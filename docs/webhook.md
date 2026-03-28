# Webhook

> 当前 Webhook `/send` 接口用于发送文本消息。  
> 图片/视频/文件发送请使用 `Bot.send_image` / `Bot.send_video` / `Bot.send_file`。

## 启动服务

```bash
wechat-bot webhook --api-key your-secret
```

默认监听：`127.0.0.1:8787`

你也可以指定参数：

```bash
wechat-bot webhook \
  --host 0.0.0.0 \
  --port 8787 \
  --account-id acct_1 \
  --api-key your-secret
```

## 调用接口

### GET `/send`

owner-default：

```bash
curl "http://127.0.0.1:8787/send?text=hello&key=your-secret"
```

显式 `to`：

```bash
curl "http://127.0.0.1:8787/send?to=o9xxx@im.wechat&text=hello&key=your-secret"
```

### POST `/send`

owner-default：

```bash
curl -X POST "http://127.0.0.1:8787/send" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Key: your-secret" \
  -d '{"text":"hello from webhook"}'
```

显式 `to`：

```bash
curl -X POST "http://127.0.0.1:8787/send" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Key: your-secret" \
  -d '{"to":"o9xxx@im.wechat","text":"hello"}'
```

## 响应格式

- 成功：`{"status": 200}`
- 失败：`{"status": <4xx/5xx>, "detail": "..."}`
