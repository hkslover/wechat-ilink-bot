# 快速开始

## 安装

```bash
pip install wechat-ilink-bot
```

可选：

```bash
pip install "wechat-ilink-bot[webhook]"
```

## 第一步：扫码登录

```bash
python examples/login_bot.py
```

## 第二步：运行 Echo Bot

```bash
python examples/echo_bot.py
```

## 第三步：主动发送

```bash
python examples/proactive_send.py
```

如果不传 `to`，SDK 会优先尝试 owner-default 收件人（登录账号对应用户）。
