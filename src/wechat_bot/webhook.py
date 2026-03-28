"""Webhook server helpers for one-click HTTP message sending."""

from __future__ import annotations

from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from ._logging import logger
from ._version import __version__
from .bot import Bot

__all__ = ["WebhookSendRequest", "create_webhook_app", "run_webhook_server"]


class WebhookSendRequest(BaseModel):
    """Payload for POST /send."""

    to: str | None = Field(default=None, min_length=1, description="Target user ID")
    text: str = Field(min_length=1, description="Text message content")
    account_id: str | None = Field(default=None, description="Optional local account ID")
    key: str | None = Field(default=None, description="Optional webhook key")


def _require_fastapi() -> tuple[type[object], object, type[Exception], object]:
    try:
        from fastapi import FastAPI, Header, HTTPException, Query
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Webhook requires optional dependencies. Install with: "
            "python -m pip install 'wechat-ilink-bot[webhook]' "
            "(or python -m pip install fastapi uvicorn)."
        ) from exc
    return FastAPI, Header, HTTPException, Query


def _check_api_key(
    required_key: str | None,
    *,
    query_or_body_key: str | None,
    header_key: str | None,
) -> bool:
    if not required_key:
        return True
    provided = (header_key or "").strip() or (query_or_body_key or "").strip()
    return bool(provided and provided == required_key)


def create_webhook_app(
    bot: Bot,
    *,
    api_key: str | None = None,
    allow_get: bool = True,
) -> object:
    """Create a FastAPI app exposing `/healthz` and `/send`."""

    FastAPI, Header, HTTPException, Query = _require_fastapi()
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @asynccontextmanager
    async def lifespan(_app: object):
        yield
        await bot.stop()

    app = FastAPI(
        title="wechat-ilink-bot webhook",
        version=__version__,
        lifespan=lifespan,
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "detail": detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"status": 422, "detail": "Invalid request parameters"},
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(
        _request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"status": 500, "detail": "Internal server error"},
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, int]:
        return {"status": 200}

    async def _send(
        *,
        to: str | None,
        text: str,
        account_id: str | None,
        provided_key: str | None,
        header_key: str | None,
    ) -> dict[str, int]:
        if not _check_api_key(
            api_key,
            query_or_body_key=provided_key,
            header_key=header_key,
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook key")

        if account_id and account_id != bot.account_id:
            try:
                bot.use_account(account_id)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            resolved_to = bot.resolve_recipient(to)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            await bot.send_text(to=resolved_to, text=text)
        except Exception as exc:
            logger.exception("Webhook send failed for account_id=%s", bot.account_id)
            raise HTTPException(status_code=502, detail="Failed to send message") from exc

        return {"status": 200}

    if allow_get:

        @app.get("/send")
        async def send_get(
            to: str | None = Query(default=None, min_length=1),
            text: str = Query(..., min_length=1),
            account_id: str | None = Query(default=None),
            key: str | None = Query(default=None),
            x_webhook_key: str | None = Header(default=None, alias="X-Webhook-Key"),
        ) -> dict[str, int]:
            return await _send(
                to=to,
                text=text,
                account_id=account_id,
                provided_key=key,
                header_key=x_webhook_key,
            )

    @app.post("/send")
    async def send_post(
        payload: WebhookSendRequest,
        x_webhook_key: str | None = Header(default=None, alias="X-Webhook-Key"),
    ) -> dict[str, int]:
        return await _send(
            to=payload.to,
            text=payload.text,
            account_id=payload.account_id,
            provided_key=payload.key,
            header_key=x_webhook_key,
        )

    return app


def run_webhook_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    account_id: str | None = None,
    state_dir: str | None = None,
    api_key: str | None = None,
    allow_get: bool = True,
    log_level: str = "info",
    use_current_user: bool = True,
) -> None:
    """Run webhook server and expose HTTP endpoints for sending text messages."""

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Webhook server requires uvicorn. Install with: "
            "python -m pip install 'wechat-ilink-bot[webhook]' "
            "(or python -m pip install uvicorn)."
        ) from exc

    bot = Bot(state_dir=state_dir, use_current_user=use_current_user)
    if account_id:
        bot.use_account(account_id)

    app = create_webhook_app(
        bot,
        api_key=api_key,
        allow_get=allow_get,
    )
    uvicorn.run(app, host=host, port=port, log_level=log_level)
