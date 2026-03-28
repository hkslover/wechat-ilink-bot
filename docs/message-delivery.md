# 消息发送能力

`wechat-ilink-bot` 提供两类发送能力：

1. 主动发送（`Bot.send_*`）
2. 会话内回复（`MessageContext.reply_*`）

## 一、主动发送（Bot.send_*）

适合定时任务、脚本触发、外部业务调用。

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot()

    await bot.send_text(text="hello")
    await bot.send_image(file_path="/path/to/image.png", caption="image")
    await bot.send_video(file_path="/path/to/video.mp4", caption="video")
    await bot.send_file(file_path="/path/to/file.pdf", caption="file")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

- `to` 不传：owner-default
- `to` 传入：显式目标优先

## 二、会话内回复（ctx.reply_*）

适合在 handler 中直接回给当前对话发起人。

```python
from wechat_bot import Bot, Filter

bot = Bot()


@bot.on_message(Filter.text_startswith("/image"))
async def reply_image(ctx):
    await ctx.reply_image("/path/to/image.png", caption="image")


@bot.on_message(Filter.text_startswith("/video"))
async def reply_video(ctx):
    await ctx.reply_video("/path/to/video.mp4", caption="video")


@bot.on_message(Filter.text_startswith("/file"))
async def reply_file(ctx):
    await ctx.reply_file("/path/to/file.pdf", caption="file")


if __name__ == "__main__":
    bot.run()
```

常用方法：

- `ctx.reply(text)`
- `ctx.reply_image(file_path, caption="")`
- `ctx.reply_video(file_path, caption="")`
- `ctx.reply_file(file_path, caption="")`
- `ctx.send_typing()`
