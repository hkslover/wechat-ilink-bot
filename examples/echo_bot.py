"""Minimal echo bot.

By default this loads the latest account from current_user.json.
Set WECHAT_ACCOUNT_ID to force a specific local account.
"""

import logging
import os

from wechat_bot import Bot, Filter

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

bot = Bot()
account_id = os.getenv("WECHAT_ACCOUNT_ID", "").strip()
if account_id:
    bot.use_account(account_id)
    print(f"Using account: {account_id}")


@bot.on_message(Filter.text())
async def echo(ctx):
    await ctx.reply(f"Echo: {ctx.text}")


if __name__ == "__main__":
    bot.run()
