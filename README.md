# QMT HTTP Bridge

把 QMT 内置策略环境暴露成一个**仅本机可访问的 HTTP API**，让外部 Python、浏览器、研究脚本或其他策略进程通过统一协议访问账户、持仓、委托、成交和行情，并在显式开启后发送限价委托/撤单。

> 本项目是技术示例，不绕过券商权限、不提供交易账户、不保证任何券商版本兼容性，也不构成投资建议。程序化交易的报备、接口权限和使用边界应以监管、交易所和开户券商要求为准。

## 为什么做两版

| 版本 | 适合谁 | 接口 | 代码风格 | 默认交易 |
|---|---|---|---|---|
| `lite/` | 想快速复制进 QMT、理解核心思路的人 | `POST /api` | 单文件、无代码注释、最少抽象 | 关闭 |
| `full/` | 想二次开发、做长期运行服务的人 | `/api/v1/<operation>` | 模块化、完整注释、测试、限流/审计/幂等/风控 | 关闭 |

## 核心设计

QMT 策略 API 并不适合从任意 HTTP 工作线程直接并发调用。本项目采用：

```text
浏览器 / Python / 外部策略
          |
          v
     HTTP worker
          |
          v
   thread-safe queue
          |
          v
 qmt_bridge_pump (500ms)
          |
          v
      QMT API
```

也就是说，HTTP 线程负责网络收发，请求真正触碰 QMT API 时回到模型线程执行。

## 快速开始：Lite

1. 打开 `lite/qmt_http_bridge_lite.py`，复制进 QMT 策略编辑器并运行。
2. QMT 控制台会输出监听地址和一次性随机 Token。
3. 打开 `lite/test.html`。
4. 填写 Token、账户号，调用 `account` / `positions` / `quotes` 等操作。

默认不会下单。只有显式设置 `QMT_HTTP_TRADE=1` 后，`order` 和 `cancel` 才会工作。

## Full 版

完整版本位于 `full/`，入口是 `full/qmt_strategy.py`，模块包是 `full/qmt_bridge/`。

提供：

- Token 鉴权；
- 本机回环地址强制绑定；
- CORS Origin 白名单；
- 每分钟请求限流；
- 请求体大小限制；
- 读请求短 TTL 缓存；
- 交易请求优先队列；
- 限价单数量/金额上限；
- `X-Idempotency-Key` 幂等保护；
- 审计事件缓冲；
- QMT 委托/成交/持仓/错误事件缓冲；
- 单元测试。

详细接口见 `docs/API.md`，部署与威胁模型见 `docs/SECURITY.md` 和 `docs/ARCHITECTURE.md`。

## Web 测试页

`web/test.html` 无任何第三方依赖，直接双击即可使用。支持 Lite 和 Full 两种协议。

## 项目结构

```text
qmt-http-bridge-open/
├─ lite/
│  ├─ qmt_http_bridge_lite.py
│  ├─ test.html
│  └─ README.md
├─ full/
│  ├─ qmt_strategy.py
│  ├─ qmt_bridge/
│  ├─ tests/
│  ├─ test.html
│  └─ README.md
├─ web/test.html
├─ docs/
│  ├─ API.md
│  ├─ ARCHITECTURE.md
│  └─ SECURITY.md
├─ article/
│  └─ csdn_zhihu_miniqmt_to_qmt_http.md
└─ LICENSE
```

## 合规提醒

中国证监会《证券市场程序化交易管理规定（试行）》自 2024 年 10 月 8 日起施行，对程序化交易报告、交易监测、风险控制、系统接入等作出要求。开源代码本身不代表你的账户已取得程序化交易权限；实际使用前请向开户券商确认报告、权限和接口政策。

## License

MIT。实际使用 QMT/券商软件时，还应遵守相应软件许可、券商协议和监管要求。
