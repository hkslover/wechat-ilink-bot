# Examples

完整示例代码位于仓库的 `examples/` 目录：

- [`examples/login_bot.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/login_bot.py)
- [`examples/echo_bot.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/echo_bot.py)
- [`examples/command_bot.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/command_bot.py)
- [`examples/media_bot.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/media_bot.py)
- [`examples/proactive_send.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/proactive_send.py)
- [`examples/account_switch.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/account_switch.py)
- [`examples/webhook_server.py`](https://github.com/hkslover/wechat-ilink-bot/blob/main/examples/webhook_server.py)

## 建议顺序

1. `login_bot.py`
2. `echo_bot.py`
3. `command_bot.py`
4. `proactive_send.py`（包含文本/图片/视频/文件主动发送）
5. `media_bot.py`（接收媒体并下载）
6. `webhook_server.py`
