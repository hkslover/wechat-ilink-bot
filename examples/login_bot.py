"""One-time QR login helper.

Run this first to persist credentials, then run other examples.
"""

import asyncio
import logging

from wechat_bot import Bot

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    bot = Bot(use_current_user=False)

    result = await bot.login()
    print("Login successful.")
    print(f"account_id = {result.account_id}")
    if result.user_id:
        print(f"user_id    = {result.user_id}")
    print("Next step: python examples/echo_bot.py")
    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
