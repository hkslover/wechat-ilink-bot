"""Low-level async HTTP client for the WeChat iLink Bot API."""

from __future__ import annotations

import base64
import os
import struct
from time import monotonic
from typing import Any

import httpx

from ._logging import logger
from ._version import __version__
from .errors import APIError
from .models import (
    BaseInfo,
    GetConfigResponse,
    GetUpdatesResponse,
    GetUploadUrlRequest,
    GetUploadUrlResponse,
    SendMessageRequest,
    SendTypingResponse,
    WeixinMessage,
)
from .types import DEFAULT_BASE_URL, DEFAULT_CDN_BASE_URL, TypingStatus

__all__ = ["WeChatClient"]

_ILINK_APP_ID = "wx_bot_python"


def _build_client_version(version: str) -> int:
    """Encode M.N.P into a uint32 as 0x00MMNNPP."""
    parts = version.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return ((major & 0xFF) << 16) | ((minor & 0xFF) << 8) | (patch & 0xFF)


_ILINK_CLIENT_VERSION = str(_build_client_version(__version__))

DEFAULT_LONG_POLL_TIMEOUT_S = 35.0
DEFAULT_API_TIMEOUT_S = 15.0
DEFAULT_CONFIG_TIMEOUT_S = 10.0
DEFAULT_CONFIG_CACHE_TTL_S = 60.0


def _random_wechat_uin() -> str:
    """Generate the X-WECHAT-UIN header: random uint32 -> decimal string -> base64."""
    raw = os.urandom(4)
    uint32 = struct.unpack(">I", raw)[0]
    return base64.b64encode(str(uint32).encode()).decode()


def _base_info() -> dict[str, Any]:
    return {"channel_version": __version__}


class WeChatClient:
    """Async HTTP client wrapping the five iLink Bot API endpoints.

    Args:
        base_url: iLink API base URL.
        token: Bot token obtained from QR login.
        cdn_base_url: CDN base URL for media operations.
        app_id: iLink-App-Id header value.
        config_cache_ttl_s: In-memory TTL for ``get_config`` responses.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        token: str = "",
        cdn_base_url: str = DEFAULT_CDN_BASE_URL,
        app_id: str = _ILINK_APP_ID,
        config_cache_ttl_s: float = DEFAULT_CONFIG_CACHE_TTL_S,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.cdn_base_url = cdn_base_url
        self._app_id = app_id
        self._config_cache_ttl_s = max(0.0, config_cache_ttl_s)
        self._config_cache: dict[tuple[str, str], tuple[float, GetConfigResponse]] = {}
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            try:
                self._http = httpx.AsyncClient(
                    timeout=httpx.Timeout(DEFAULT_API_TIMEOUT_S, connect=10.0),
                )
            except ImportError:
                logger.warning(
                    "System SOCKS proxy detected but 'socksio' is not installed. "
                    "Falling back to direct connection. "
                    "To use the proxy, run: pip install 'httpx[socks]'"
                )
                self._http = httpx.AsyncClient(
                    timeout=httpx.Timeout(DEFAULT_API_TIMEOUT_S, connect=10.0),
                    proxy=None,
                )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def _common_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "iLink-App-Id": self._app_id,
            "iLink-App-ClientVersion": _ILINK_CLIENT_VERSION,
        }
        return headers

    def _post_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "X-WECHAT-UIN": _random_wechat_uin(),
            **self._common_headers(),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post(
        self,
        endpoint: str,
        body: dict[str, Any],
        *,
        timeout: float = DEFAULT_API_TIMEOUT_S,
        label: str = "",
    ) -> dict[str, Any]:
        http = await self._ensure_http()
        url = self.base_url + endpoint
        headers = self._post_headers()
        logger.debug("%s POST %s", label, url)
        resp = await http.post(url, json=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        logger.debug("%s response: %s", label, data)
        return data

    async def _get(
        self,
        endpoint: str,
        *,
        timeout: float = DEFAULT_API_TIMEOUT_S,
        label: str = "",
    ) -> dict[str, Any]:
        http = await self._ensure_http()
        url = self.base_url + endpoint
        headers = self._common_headers()
        logger.debug("%s GET %s", label, url)
        resp = await http.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_updates(
        self,
        get_updates_buf: str = "",
        timeout_ms: int | None = None,
    ) -> GetUpdatesResponse:
        """Long-poll for new inbound messages.

        Args:
            get_updates_buf: Sync cursor from previous response.
            timeout_ms: Server-side long-poll timeout in ms.
        """
        timeout_s = (timeout_ms / 1000.0) if timeout_ms else DEFAULT_LONG_POLL_TIMEOUT_S
        client_timeout = timeout_s + 5.0

        body = {
            "get_updates_buf": get_updates_buf,
            "base_info": _base_info(),
        }
        try:
            data = await self._post(
                "ilink/bot/getupdates",
                body,
                timeout=client_timeout,
                label="getUpdates",
            )
        except httpx.ReadTimeout:
            logger.debug("getUpdates: client-side timeout, returning empty")
            return GetUpdatesResponse(ret=0, msgs=[], get_updates_buf=get_updates_buf)

        return GetUpdatesResponse.model_validate(data)

    async def send_message(self, msg: WeixinMessage) -> None:
        """Send a single message downstream."""
        req = SendMessageRequest(msg=msg, base_info=BaseInfo(channel_version=__version__))
        await self._post(
            "ilink/bot/sendmessage",
            req.model_dump(exclude_none=True),
            label="sendMessage",
        )

    async def get_upload_url(self, req: GetUploadUrlRequest) -> GetUploadUrlResponse:
        """Get a pre-signed CDN upload URL."""
        payload = req.model_dump(exclude_none=True)
        payload["base_info"] = _base_info()
        data = await self._post("ilink/bot/getuploadurl", payload, label="getUploadUrl")
        return GetUploadUrlResponse.model_validate(data)

    async def get_config(
        self,
        user_id: str,
        context_token: str | None = None,
    ) -> GetConfigResponse:
        """Fetch bot config (includes typing_ticket) for a user.

        Responses are cached in-memory for a short TTL to reduce duplicate
        calls in frequent typing indicator scenarios.
        """
        cache_key = (user_id, context_token or "")
        now = monotonic()
        if self._config_cache_ttl_s > 0:
            cached = self._config_cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]

        body: dict[str, Any] = {
            "ilink_user_id": user_id,
            "base_info": _base_info(),
        }
        if context_token:
            body["context_token"] = context_token
        data = await self._post(
            "ilink/bot/getconfig",
            body,
            timeout=DEFAULT_CONFIG_TIMEOUT_S,
            label="getConfig",
        )
        resp = GetConfigResponse.model_validate(data)
        if self._config_cache_ttl_s > 0 and (resp.ret is None or resp.ret == 0):
            self._config_cache[cache_key] = (monotonic() + self._config_cache_ttl_s, resp)
        return resp

    async def send_typing(
        self,
        user_id: str,
        typing_ticket: str,
        status: int = TypingStatus.TYPING,
    ) -> None:
        """Send a typing indicator to a user."""
        body: dict[str, Any] = {
            "ilink_user_id": user_id,
            "typing_ticket": typing_ticket,
            "status": status,
            "base_info": _base_info(),
        }
        data = await self._post(
            "ilink/bot/sendtyping",
            body,
            timeout=DEFAULT_CONFIG_TIMEOUT_S,
            label="sendTyping",
        )
        resp = SendTypingResponse.model_validate(data)
        if resp.ret and resp.ret != 0:
            raise APIError(
                f"sendTyping failed: {resp.errmsg}",
                ret=resp.ret,
            )
