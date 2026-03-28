# Webhook

## 启动

```bash
wechat-bot webhook --api-key your-secret
```

默认监听：`127.0.0.1:8787`

## 调用示例

GET：

```bash
curl "http://127.0.0.1:8787/send?text=hello&key=your-secret"
```

POST：

```bash
curl -X POST "http://127.0.0.1:8787/send" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Key: your-secret" \
  -d '{"text":"hello from webhook"}'
```

## 返回格式

- 成功：`{"status": 200}`
- 失败：`{"status": <4xx/5xx>, "detail": "..."}`
