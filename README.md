# wechat-ilink-bot

轻量、实用的 Python SDK，用于接入 WeChat iLink Bot API。

支持扫码登录、长轮询收消息、文本/图片/视频/文件发送，以及一键 webhook 发送。

<p>
  <a href="https://wechat-ilink-bot.readthedocs.io/en/latest/" target="_blank">
    <strong>Read the Docs: https://wechat-ilink-bot.readthedocs.io/en/latest/</strong>
  </a>
</p>

## 安装

PyPI 安装：

```bash
pip install wechat-ilink-bot
```

源码安装（开发/调试推荐）：

```bash
git clone https://github.com/hkslover/wechat-ilink-bot.git
cd wechat-ilink-bot
pip install -e .
```

可选依赖：

```bash
# 终端二维码打印
pip install "wechat-ilink-bot[qrcode]"

# webhook
pip install "wechat-ilink-bot[webhook]"
```

## 快速开始

### 1) 扫码登录并持久化账号

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot(use_current_user=False)
    result = await bot.login()
    print(f"login ok: account_id={result.account_id}, user_id={result.user_id}")
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2) 最小 Echo Bot

```python
from wechat_bot import Bot, Filter

bot = Bot()


@bot.on_message(Filter.text())
async def echo(ctx):
    await ctx.reply(f"Echo: {ctx.text}")


if __name__ == "__main__":
    bot.run()
```

### 3) 主动发送（owner-default 或显式目标）

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot()

    # owner-default（不传 to）
    await bot.send_text(text="Hello from wechat-ilink-bot!")

    # 或者显式目标
    # await bot.send_text(to="o9xxx@im.wechat", text="Hello")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Webhook 快速使用

启动：

```bash
wechat-bot webhook --api-key your-secret
```

请求示例：

```bash
# GET
curl "http://127.0.0.1:8787/send?text=hello&key=your-secret"

# POST
curl -X POST "http://127.0.0.1:8787/send" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Key: your-secret" \
  -d '{"text":"hello from webhook"}'
```

## Examples

更多完整脚本请查看：

- [examples/login_bot.py](examples/login_bot.py)
- [examples/echo_bot.py](examples/echo_bot.py)
- [examples/command_bot.py](examples/command_bot.py)
- [examples/media_bot.py](examples/media_bot.py)
- [examples/proactive_send.py](examples/proactive_send.py)
- [examples/account_switch.py](examples/account_switch.py)
- [examples/webhook_server.py](examples/webhook_server.py)

## 本地文档预览

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
