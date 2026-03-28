# wechat-ilink-bot

轻量、实用的 Python SDK，用于接入 WeChat iLink Bot API。

支持扫码登录、长轮询收消息、文本/图片/视频/文件发送，以及一键 webhook 发送。

## 安装

```bash
pip install wechat-ilink-bot
```

可选依赖：

```bash
# 终端二维码打印
pip install "wechat-ilink-bot[qrcode]"

# webhook
pip install "wechat-ilink-bot[webhook]"
```

## 快速开始

1. 首次登录（扫码）：

```bash
python examples/login_bot.py
```

2. 启动最小 Echo Bot：

```bash
python examples/echo_bot.py
```

3. 主动发送消息：

```bash
python examples/proactive_send.py
```

## Webhook 一键启动

```bash
wechat-bot webhook --api-key your-secret
```

发送示例：

```bash
# GET
curl "http://127.0.0.1:8787/send?text=hello&key=your-secret"

# POST
curl -X POST "http://127.0.0.1:8787/send" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Key: your-secret" \
  -d '{"text":"hello from webhook"}'
```

## 示例目录

- `examples/login_bot.py`：扫码登录
- `examples/echo_bot.py`：最小回声机器人
- `examples/command_bot.py`：命令式 handler
- `examples/media_bot.py`：媒体下载
- `examples/proactive_send.py`：主动发送
- `examples/account_switch.py`：账号切换发送
- `examples/webhook_server.py`：本地 webhook 服务

## 文档

文档已迁移到 `docs/`（`MkDocs + Read the Docs` 结构）。

本地预览：

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

## 参与贡献

- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## License

MIT
