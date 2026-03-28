# FAQ

## 为什么 `send_text` 可以不传 `to`？

SDK 支持 owner-default。  
当 `to` 省略时，会尝试使用登录状态中的 owner `user_id` 作为接收者。

## 如果 owner 无法解析怎么办？

会返回明确错误，提示你显式传入 `to` 或重新登录。

## Webhook 成功和失败响应是什么？

- 成功：`{"status": 200}`
- 失败：`{"status": <4xx/5xx>, "detail": "..."}`

## 想看完整 API 怎么办？

查看左侧 API 文档，或直接访问：

- [Bot API](api/bot.md)
- [MessageContext API](api/context.md)
- [Webhook Helpers API](api/webhook.md)
