# API Reference

默认地址：`http://127.0.0.1:18765`

## Lite

唯一业务入口：

```http
POST /api
X-QMT-Token: <token>
Content-Type: application/json
```

```json
{
  "op": "positions",
  "data": {
    "account_id": "YOUR_ACCOUNT_ID",
    "account_type": "STOCK"
  },
  "timeout": 8
}
```

支持 `health`、`account`、`positions`、`orders`、`fills`、`quotes`、`history`、`order`、`cancel`。

## Full

```http
POST /api/v1/<operation>
X-QMT-Token: <token>
Content-Type: application/json
```

请求：

```json
{
  "protocol_version": "1.0",
  "request_id": "client-generated-id",
  "operation": "quotes",
  "payload": {
    "symbols": ["600000.SH", "000001.SZ"]
  },
  "timeout_ms": 8000
}
```

响应：

```json
{
  "protocol_version": "1.0",
  "request_id": "client-generated-id",
  "ok": true,
  "data": {},
  "error_type": "",
  "error": "",
  "server_time": 0
}
```

### `health`

服务状态。另有 `GET /health`。

### `runtime`

返回运行时计数、启动时间和脱敏后的公开配置。

### `account`

Payload：`account_id`、`account_type`。

### `positions`

返回持仓数量、可用数量、冻结数量、成本、最新价、市值。

### `orders`

返回账户订单，可选 `strategy_name`。

### `fills`

返回成交记录，可选 `strategy_name`。

### `quotes`

```json
{"symbols":["600000.SH","000001.SZ"]}
```

### `history`

```json
{
  "symbols": ["600000.SH"],
  "fields": ["open", "high", "low", "close", "volume"],
  "period": "1d",
  "start_time": "",
  "end_time": "",
  "count": 100,
  "dividend_type": "front",
  "subscribe": false
}
```

### `subscribe` / `unsubscribe`

订阅 QMT 行情回调，并通过 `events` 读取缓冲事件。

### `events`

```json
{"limit":200}
```

读取并移除事件缓冲中的前 N 条事件。

### `audit`

返回最近请求审计信息，不记录 Token。

### `submit_limit`

默认关闭。除普通鉴权外建议携带：

```http
X-Idempotency-Key: a-client-unique-key
```

Payload：

```json
{
  "account_id": "YOUR_ACCOUNT_ID",
  "account_type": "STOCK",
  "symbol": "600000.SH",
  "side": "BUY",
  "qty": 100,
  "limit_price": 10.50,
  "strategy_name": "MY_STRATEGY",
  "client_order_id": "optional-client-id"
}
```

### `cancel`

```json
{
  "account_id": "YOUR_ACCOUNT_ID",
  "account_type": "STOCK",
  "broker_order_id": "ORDER_ID"
}
```
