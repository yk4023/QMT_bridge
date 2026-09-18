from __future__ import print_function
import json
import os
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

HOST = "127.0.0.1"
PORT = int(os.environ.get("QMT_HTTP_PORT", "18765"))
TOKEN = os.environ.get("QMT_HTTP_TOKEN", "") or uuid.uuid4().hex
ALLOW_TRADE = os.environ.get("QMT_HTTP_TRADE", "0").lower() in ("1", "true", "yes", "on")
QMT_HTTP = None

def j(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {str(k): j(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [j(x) for x in v]
    m = getattr(v, "item", None)
    if callable(m):
        try:
            return j(m())
        except Exception:
            pass
    m = getattr(v, "reset_index", None)
    if callable(m):
        try:
            v = m()
        except Exception:
            pass
    m = getattr(v, "to_dict", None)
    if callable(m):
        try:
            return j(m(orient="records"))
        except Exception:
            try:
                return j(m())
            except Exception:
                pass
    return str(v)

def a(o, n, d=None):
    try:
        if isinstance(o, dict):
            return o.get(n, d)
        return getattr(o, n)
    except Exception:
        return d

def rows(v):
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]

def sym(code, ex):
    code = str(code or "")
    ex = str(ex or "").upper()
    if "." in code:
        return code
    if ex in ("SH", "SSE", "XSHG"):
        return code + ".SH"
    if ex in ("SZ", "SZSE", "XSHE"):
        return code + ".SZ"
    return code

class Call(object):
    def __init__(self, req):
        self.req = req
        self.ev = threading.Event()
        self.result = None

class Bridge(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.q = queue.Queue()
        self.server = Server((HOST, PORT), Handler)
        self.server.bridge = self
        self.thread = None
        self.account_id = ""
        self.account_type = "STOCK"

    def start(self):
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print("QMT HTTP Lite: http://%s:%s token=%s trade=%s" % (HOST, PORT, TOKEN, ALLOW_TRADE))

    def stop(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass

    def submit(self, req):
        c = Call(req)
        self.q.put(c)
        if not c.ev.wait(float(req.get("timeout", 8))):
            return {"ok": False, "error": "timeout"}
        return c.result

    def pump(self):
        for _ in range(100):
            try:
                c = self.q.get_nowait()
            except queue.Empty:
                break
            try:
                c.result = {"ok": True, "data": self.exec(c.req)}
            except Exception as e:
                c.result = {"ok": False, "error": str(e)}
            c.ev.set()

    def set_account(self, p):
        account_id = str(p.get("account_id") or self.account_id or "").strip()
        account_type = str(p.get("account_type") or self.account_type or "STOCK").upper()
        if account_id:
            self.account_id = account_id
            self.account_type = account_type
            m = getattr(self.ctx, "set_account", None)
            if callable(m):
                m(account_id)
        if not self.account_id:
            raise ValueError("account_id required")

    def detail(self, typ):
        f = globals().get("get_trade_detail_data")
        if not callable(f):
            raise RuntimeError("get_trade_detail_data unavailable")
        return rows(f(self.account_id, self.account_type, typ))

    def exec(self, r):
        op = str(r.get("op") or "")
        p = dict(r.get("data") or {})
        if op == "health":
            return {"bridge": "qmt_http_lite", "trade": ALLOW_TRADE}
        if op in ("account", "positions", "orders", "fills", "order", "cancel"):
            self.set_account(p)
        if op == "account":
            x = self.detail("ACCOUNT")
            if not x:
                return None
            x = x[0]
            return {"total_asset": float(a(x, "m_dBalance", 0) or 0), "cash": float(a(x, "m_dAvailable", 0) or 0), "market_value": float(a(x, "m_dInstrumentValue", 0) or 0)}
        if op == "positions":
            return [{"symbol": sym(a(x, "m_strInstrumentID"), a(x, "m_strExchangeID")), "qty": int(a(x, "m_nVolume", 0) or 0), "available": int(a(x, "m_nCanUseVolume", 0) or 0), "cost": float(a(x, "m_dOpenPrice", 0) or 0), "last": float(a(x, "m_dLastPrice", 0) or 0)} for x in self.detail("POSITION")]
        if op == "orders":
            return [{"order_id": str(a(x, "m_strOrderSysID", "")), "symbol": sym(a(x, "m_strInstrumentID"), a(x, "m_strExchangeID")), "qty": int(a(x, "m_nVolumeTotalOriginal", 0) or 0), "filled": int(a(x, "m_nVolumeTraded", 0) or 0), "price": float(a(x, "m_dLimitPrice", 0) or 0), "status": int(a(x, "m_nOrderStatus", 255) or 255)} for x in self.detail("ORDER")]
        if op == "fills":
            return [{"trade_id": str(a(x, "m_strTradeID", "")), "order_id": str(a(x, "m_strOrderSysID", "")), "symbol": sym(a(x, "m_strInstrumentID"), a(x, "m_strExchangeID")), "qty": abs(int(a(x, "m_nVolume", 0) or 0)), "price": float(a(x, "m_dPrice", 0) or 0)} for x in self.detail("DEAL")]
        if op == "quotes":
            codes = list(p.get("symbols") or [])
            return j(self.ctx.get_full_tick(codes) or {})
        if op == "history":
            return j(self.ctx.get_market_data_ex(fields=list(p.get("fields") or []), stock_code=list(p.get("symbols") or []), period=p.get("period", "1d"), start_time=p.get("start_time", ""), end_time=p.get("end_time", ""), count=int(p.get("count", -1)), dividend_type=p.get("dividend_type", "none"), fill_data=True, subscribe=False) or {})
        if op == "order":
            if not ALLOW_TRADE:
                raise PermissionError("trade disabled")
            side = str(p.get("side") or "").upper()
            if side not in ("BUY", "SELL"):
                raise ValueError("side must be BUY or SELL")
            qty = int(p.get("qty") or 0)
            price = float(p.get("price") or 0)
            if qty <= 0 or price <= 0:
                raise ValueError("qty and price must be positive")
            f = globals().get("passorder")
            if not callable(f):
                raise RuntimeError("passorder unavailable")
            cid = str(p.get("client_order_id") or ("QHTTP-" + uuid.uuid4().hex[:16]))
            f(23 if side == "BUY" else 24, 1101, self.account_id, p.get("symbol"), 11, price, qty, str(p.get("strategy", "QMT_HTTP_LITE")), 1, cid, self.ctx)
            return {"client_order_id": cid, "state": "SIGNAL_SENT"}
        if op == "cancel":
            if not ALLOW_TRADE:
                raise PermissionError("trade disabled")
            oid = p.get("order_id")
            can = globals().get("can_cancel_order")
            cancel = globals().get("cancel")
            if not callable(can) or not callable(cancel):
                raise RuntimeError("cancel api unavailable")
            if not can(oid, self.account_id, self.account_type):
                return {"order_id": oid, "sent": False}
            return {"order_id": oid, "sent": bool(cancel(oid, self.account_id, self.account_type, self.ctx))}
        raise ValueError("unsupported op")

class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-QMT-Token")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] != "/health":
            self.write({"ok": False, "error": "not found"}, 404)
            return
        if self.headers.get("X-QMT-Token", "") != TOKEN:
            self.write({"ok": False, "error": "unauthorized"}, 403)
            return
        self.write({"ok": True, "data": {"bridge": "qmt_http_lite", "trade": ALLOW_TRADE}})

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api":
            self.write({"ok": False, "error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 2097152:
                raise ValueError("invalid body size")
            r = json.loads(self.rfile.read(n).decode("utf-8"))
            token = self.headers.get("X-QMT-Token") or r.get("token") or ""
            if token != TOKEN:
                self.write({"ok": False, "error": "unauthorized"}, 403)
                return
            self.write(self.server.bridge.submit(r))
        except Exception as e:
            self.write({"ok": False, "error": str(e)}, 400)

    def write(self, obj, status=200):
        b = json.dumps(j(obj), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        try:
            self.wfile.write(b)
            self.wfile.flush()
        except Exception:
            pass

    def log_message(self, *_):
        return

def init(ContextInfo):
    global QMT_HTTP
    if QMT_HTTP is not None:
        return
    QMT_HTTP = Bridge(ContextInfo)
    QMT_HTTP.start()
    ContextInfo.run_time("qmt_http_pump", "500nMilliSecond", "2000-01-01 00:00:00", "SH")

def qmt_http_pump(ContextInfo):
    if QMT_HTTP is not None:
        QMT_HTTP.ctx = ContextInfo
        QMT_HTTP.pump()

def handlebar(ContextInfo):
    pass

def stop(ContextInfo):
    global QMT_HTTP
    if QMT_HTTP is not None:
        QMT_HTTP.stop()
        QMT_HTTP = None
