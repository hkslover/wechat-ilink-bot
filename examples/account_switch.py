"""Use a specific local account to send one proactive text message."""

from __future__ import annotations

import asyncio
import logging
import os

from wechat_bot import Bot

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main() -> None:
    bot = Bot(use_current_user=False)
    accounts = bot.list_accounts()
    if not accounts:
        raise RuntimeError("No local accounts found. Run python examples/login_bot.py first.")

    account_id = os.getenv("WECHAT_ACCOUNT_ID", "").strip()
    if not account_id:
        raise RuntimeError(f"Please set WECHAT_ACCOUNT_ID. Available: {', '.join(accounts)}")

    bot.use_account(account_id)
    target_user = os.getenv("WECHAT_TARGET_USER", "").strip()

    if target_user:
        await bot.send_text(to=target_user, text=f"hello from account {account_id}")
    else:
        await bot.send_text(text=f"hello from account {account_id}")
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
