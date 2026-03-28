"""Command-line entrypoints for wechat_bot."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .webhook import run_webhook_server

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wechat-bot", description="wechat-ilink-bot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    webhook = subparsers.add_parser("webhook", help="Run HTTP webhook server")
    webhook.add_argument("--host", default="127.0.0.1", help="Bind host")
    webhook.add_argument("--port", type=int, default=8787, help="Bind port")
    webhook.add_argument("--account-id", default=None, help="Use a specific local account ID")
    webhook.add_argument(
        "--state-dir",
        default=None,
        help="State directory (default ~/.wechat_bot)",
    )
    webhook.add_argument("--api-key", default=None, help="Optional API key for /send")
    webhook.add_argument("--disable-get", action="store_true", help="Disable GET /send")
    webhook.add_argument(
        "--disable-current-user",
        action="store_true",
        help="Disable auto-loading current_user account",
    )
    webhook.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Uvicorn log level",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "webhook":
        try:
            run_webhook_server(
                host=args.host,
                port=args.port,
                account_id=args.account_id,
                state_dir=args.state_dir,
                api_key=args.api_key,
                allow_get=not args.disable_get,
                log_level=args.log_level,
                use_current_user=not args.disable_current_user,
            )
            return 0
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
