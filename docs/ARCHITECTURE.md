# Architecture

## 1. 线程模型

QMT 的策略 API 与策略运行上下文存在耦合，因此本项目不在 HTTP worker 中直接访问 QMT API。

```text
Thread A/B/C: HTTP workers
       |
       | PendingCall
       v
trade_queue / query_queue
       |
       | every 500ms
       v
QMT model thread: qmt_bridge_pump
       |
       v
Service -> QmtAdapter -> QMT API
```

交易队列优先于查询队列，避免大量行情请求让撤单/下单长期排队。

## 2. 分层

- HTTP：只关心 JSON、鉴权、CORS、限流、状态码。
- Dispatcher：只关心跨线程请求交接。
- Service：业务语义、缓存、幂等、交易风控。
- Adapter：QMT 字段、方向、状态码、行情/交易 API 兼容。
- Runtime：生命周期和依赖装配。

## 3. 一致性

`passorder` 返回的只是信号已发送，不等价于交易所已受理或成交。因此 `submit_limit` 返回 `SIGNAL_SENT` 和 `needs_reconciliation=true`，最终状态应通过订单/成交查询或事件回调核对。

## 4. 缓存

账户/持仓 2 秒、订单/成交 3 秒、历史行情 10 秒的短 TTL 缓存主要用于多个外部策略同时轮询时削峰。交易操作不缓存。

## 5. 失败模式

- HTTP 超时不意味着委托一定没有进入 QMT；真实系统应使用 `client_order_id` + 订单查询核对。
- QMT 定时泵停止会导致所有排队请求超时。
- 客户端断开只终止网络响应，不应让 QMT 模型线程崩溃。
