"""Command-style bot showing handler priority and first-match semantics."""

from __future__ import annotations

import asyncio
import logging

from wechat_bot import Bot, Filter

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

bot = Bot()


@bot.on_message(Filter.text_startswith("/help"), priority=-10)
async def help_command(ctx):
    await ctx.reply(
        "Commands:\n"
        "/help - show help\n"
        "/ping - typing indicator + pong\n"
        "anything else - fallback echo"
    )


@bot.on_message(Filter.text_startswith("/ping"), priority=-9)
async def ping_command(ctx):
    await ctx.send_typing()
    await asyncio.sleep(0.2)
    await ctx.reply("pong")


@bot.on_message(Filter.text(), priority=0)
async def fallback(ctx):
    await ctx.reply(f"fallback: {ctx.text}")


if __name__ == "__main__":
    bot.run()
