"""Send proactive messages without starting polling."""

import asyncio
import logging
import os

from wechat_bot import Bot

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    target_user = os.getenv("WECHAT_TARGET_USER", "").strip()

    bot = Bot()
    account_id = os.getenv("WECHAT_ACCOUNT_ID", "").strip()
    if account_id:
        bot.use_account(account_id)

    if target_user:
        await bot.send_text(to=target_user, text="Hello from wechat-ilink-bot!")
    else:
        await bot.send_text(text="Hello from wechat-ilink-bot!")

    image_path = os.getenv("WECHAT_IMAGE_PATH", "").strip()
    if image_path:
        if target_user:
            await bot.send_image(to=target_user, file_path=image_path, caption="测试图片")
        else:
            await bot.send_image(file_path=image_path, caption="测试图片")

    file_path = os.getenv("WECHAT_FILE_PATH", "").strip()
    if file_path:
        if target_user:
            await bot.send_file(to=target_user, file_path=file_path, caption="测试文件")
        else:
            await bot.send_file(file_path=file_path, caption="测试文件")

    video_path = os.getenv("WECHAT_VIDEO_PATH", "").strip()
    if video_path:
        if target_user:
            await bot.send_video(to=target_user, file_path=video_path, caption="测试视频")
        else:
            await bot.send_video(file_path=video_path, caption="测试视频")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
