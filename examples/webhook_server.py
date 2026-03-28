"""Run webhook server for URL-triggered message sending.

Quick start:

    WECHAT_WEBHOOK_API_KEY=your-secret python examples/webhook_server.py
"""

from __future__ import annotations

import logging
import os

from wechat_bot import run_webhook_server

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    host = os.getenv("WECHAT_WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("WECHAT_WEBHOOK_PORT", "8787"))
    account_id = os.getenv("WECHAT_ACCOUNT_ID", "").strip() or None
    state_dir = os.getenv("WECHAT_STATE_DIR", "").strip() or None
    api_key = os.getenv("WECHAT_WEBHOOK_API_KEY", "").strip() or None
    allow_get = not _env_bool("WECHAT_WEBHOOK_DISABLE_GET", default=False)
    use_current_user = not _env_bool("WECHAT_WEBHOOK_DISABLE_CURRENT_USER", default=False)
    log_level = os.getenv("WECHAT_WEBHOOK_LOG_LEVEL", "info").strip().lower() or "info"

    print(f"Webhook running at http://{host}:{port}")
    print("Health check: GET /healthz")
    if allow_get:
        if api_key:
            print(
                f'GET send (owner-default): curl "http://{host}:{port}/send?text=hello&key={api_key}"'
            )
            print(
                f'GET send (explicit to): curl "http://{host}:{port}/send?to=o9xxx@im.wechat&text=hello&key={api_key}"'
            )
        else:
            print(f'GET send (owner-default): curl "http://{host}:{port}/send?text=hello"')
            print(
                f'GET send (explicit to): curl "http://{host}:{port}/send?to=o9xxx@im.wechat&text=hello"'
            )
    print("POST send:")
    print(
        f'  curl -X POST "http://{host}:{port}/send" '
        '-H "Content-Type: application/json" '
        + (f'-H "X-Webhook-Key: {api_key}" ' if api_key else "")
        + """-d '{"text":"hello from webhook"}'"""
    )

    run_webhook_server(
        host=host,
        port=port,
        account_id=account_id,
        state_dir=state_dir,
        api_key=api_key,
        allow_get=allow_get,
        log_level=log_level,
        use_current_user=use_current_user,
    )


if __name__ == "__main__":
    main()
