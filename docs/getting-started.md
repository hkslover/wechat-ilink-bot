# 快速开始

## 1) 扫码登录

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot(use_current_user=False)
    result = await bot.login()
    print("Login successful.")
    print(f"account_id = {result.account_id}")
    print(f"user_id    = {result.user_id}")
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## 2) 最小 Echo Bot

```python
from wechat_bot import Bot, Filter

bot = Bot()


@bot.on_message(Filter.text())
async def echo(ctx):
    await ctx.reply(f"Echo: {ctx.text}")


if __name__ == "__main__":
    bot.run()
```

## 3) 主动发送文本

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot()

    # owner-default（不传 to）
    await bot.send_text(text="Hello from wechat-ilink-bot!")

    # 显式目标（需要时）
    # await bot.send_text(to="o9xxx@im.wechat", text="Hello")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

> `to` 不传时会走 owner-default；传了 `to` 则显式目标优先。

## 4) 主动发送图片 / 视频 / 文件

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot()

    # owner-default 发送
    await bot.send_image(file_path="/path/to/image.png", caption="image")
    await bot.send_video(file_path="/path/to/video.mp4", caption="video")
    await bot.send_file(file_path="/path/to/file.pdf", caption="file")

    # 显式指定收件人
    # await bot.send_file(to="o9xxx@im.wechat", file_path="/path/to/file.pdf")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

你也可以参考完整脚本：`examples/proactive_send.py`。
