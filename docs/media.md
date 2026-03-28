# 媒体发送

`wechat-ilink-bot` 支持主动发送：

- 图片：`send_image`
- 视频：`send_video`
- 文件：`send_file`

## 基础示例

```python
import asyncio

from wechat_bot import Bot


async def main() -> None:
    bot = Bot()

    await bot.send_image(file_path="/path/to/image.png", caption="image")
    await bot.send_video(file_path="/path/to/video.mp4", caption="video")
    await bot.send_file(file_path="/path/to/file.pdf", caption="file")

    await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## 显式收件人

```python
await bot.send_image(to="o9xxx@im.wechat", file_path="/path/to/image.png")
await bot.send_video(to="o9xxx@im.wechat", file_path="/path/to/video.mp4")
await bot.send_file(to="o9xxx@im.wechat", file_path="/path/to/file.pdf")
```

## 说明

- `to` 省略时：走 owner-default 收件人。
- `to` 显式传入时：显式目标优先。
- `caption` 可选，会在媒体消息前发送一条文本说明。
