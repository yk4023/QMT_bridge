# QMT HTTP Bridge Lite

一个面向 QMT 内置 Python 策略环境的最小 HTTP 桥接示例。只保留一个业务入口：`POST /api`。

## 特点

- 仅 Python 标准库，兼容 Python 3.6 语法。
- HTTP 工作线程只入队，QMT API 由 `qmt_http_pump` 回到模型线程执行。
- 默认仅监听 `127.0.0.1:18765`。
- 启动时随机生成 Token 并打印到 QMT 控制台，不包含任何固定私钥或账户信息。
- 默认关闭交易；设置环境变量 `QMT_HTTP_TRADE=1` 才允许 `order` / `cancel`。
- 支持 `account`、`positions`、`orders`、`fills`、`quotes`、`history`、`order`、`cancel`。

## 使用

1. 把 `qmt_http_bridge_lite.py` 复制到 QMT 策略编辑器运行。
2. 查看 QMT 控制台输出的 Token。
3. 浏览器打开仓库根目录 `web/test.html`，地址填 `http://127.0.0.1:18765`，Token 填控制台值。
4. 首次查询账户类接口时在 JSON 中传 `account_id`。

### 示例

```json
{
  "op": "positions",
  "data": {
    "account_id": "YOUR_ACCOUNT_ID",
    "account_type": "STOCK"
  }
}
```

### 行情示例

```json
{
  "op": "quotes",
  "data": {
    "symbols": ["600000.SH", "000001.SZ"]
  }
}
```

## 交易安全

交易能力默认关闭。即使打开，也建议仅在模拟账户验证完成后再接入真实账户。程序化交易是否需要报备、是否允许接口交易以及接口权限范围，请以你的证券公司、交易所和监管要求为准。
