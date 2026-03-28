"""Download inbound media and acknowledge saved paths."""

import logging
from pathlib import Path

from wechat_bot import Bot, Filter

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

MEDIA_ROOT = Path(__file__).resolve().parent / "downloads"

bot = Bot()


@bot.on_message(Filter.text_startswith("/help"))
async def help_command(ctx):
    await ctx.reply(
        "Commands:\n"
        "/help - show this message\n"
        "send image/video/file - bot downloads then replies with local path\n"
        "send text - bot echoes your text"
    )


@bot.on_message(Filter.image())
async def on_image(ctx):
    path = await ctx.download_media(str(MEDIA_ROOT / "images"))
    await ctx.reply(f"图片已保存到: {path}" if path else "图片下载失败")


@bot.on_message(Filter.video())
async def on_video(ctx):
    path = await ctx.download_media(str(MEDIA_ROOT / "videos"))
    await ctx.reply(f"视频已保存到: {path}" if path else "视频下载失败")


@bot.on_message(Filter.file())
async def on_file(ctx):
    path = await ctx.download_media(str(MEDIA_ROOT / "files"))
    await ctx.reply(f"文件已保存到: {path}" if path else "文件下载失败")


@bot.on_message(Filter.text())
async def echo(ctx):
    await ctx.reply(f"Echo: {ctx.text}")


if __name__ == "__main__":
    bot.run()
