"""QR-code login flow for the WeChat iLink Bot API."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx

from ._logging import logger
from .errors import AuthError
from .models import LoginResult
from .types import DEFAULT_BASE_URL, DEFAULT_BOT_TYPE, QRLoginStatus

__all__ = ["login_with_qr"]

_FIXED_BASE_URL = "https://ilinkai.weixin.qq.com/"
_GET_QRCODE_TIMEOUT_S = 5.0
_QR_POLL_TIMEOUT_S = 35.0
_MAX_QR_REFRESH = 3


async def _api_get(
    http: httpx.AsyncClient,
    base_url: str,
    endpoint: str,
    timeout: float,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/" + endpoint
    resp = await http.get(url, timeout=timeout)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    return data


async def _fetch_qrcode(
    http: httpx.AsyncClient,
    bot_type: str,
) -> tuple[str, str]:
    """Fetch a new QR code. Returns (qrcode_key, qrcode_url)."""
    data = await _api_get(
        http,
        _FIXED_BASE_URL,
        f"ilink/bot/get_bot_qrcode?bot_type={bot_type}",
        _GET_QRCODE_TIMEOUT_S,
    )
    qrcode_key: str = data.get("qrcode", "")
    qrcode_url: str = data.get("qrcode_img_content", "")
    if not qrcode_key:
        raise AuthError("Server returned empty qrcode key")
    return qrcode_key, qrcode_url


async def _poll_status(
    http: httpx.AsyncClient,
    base_url: str,
    qrcode_key: str,
) -> dict[str, Any]:
    """Long-poll for QR scan status."""
    try:
        data = await _api_get(
            http,
            base_url,
            f"ilink/bot/get_qrcode_status?qrcode={qrcode_key}",
            _QR_POLL_TIMEOUT_S,
        )
        return data
    except (httpx.ReadTimeout, httpx.ConnectTimeout):
        return {"status": QRLoginStatus.WAIT}
    except httpx.HTTPError as exc:
        logger.warning("QR poll network error, treating as wait: %s", exc)
        return {"status": QRLoginStatus.WAIT}


def _try_print_qr_terminal(url: str) -> None:
    """Attempt to render the QR code in the terminal via the qrcode library."""
    try:
        import qrcode  # type: ignore[import-untyped]

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        pass


async def login_with_qr(
    base_url: str = DEFAULT_BASE_URL,
    bot_type: str = DEFAULT_BOT_TYPE,
    on_qr_url: Callable[[str], None] | None = None,
    timeout_s: int = 480,
    print_qr: bool = True,
) -> LoginResult:
    """Perform QR-code login and return a :class:`LoginResult`.

    Args:
        base_url: API base URL (used for the account, not for QR endpoints).
        bot_type: iLink bot type string.
        on_qr_url: Optional callback invoked with the QR code URL so the
            caller can display it however they like.
        timeout_s: Maximum seconds to wait for the user to scan.
        print_qr: If ``True``, attempt to print the QR code in the terminal.

    Raises:
        AuthError: If login fails or times out.
    """
    try:
        http_ctx = httpx.AsyncClient()
    except ImportError:
        http_ctx = httpx.AsyncClient(proxy=None)
    async with http_ctx as http:
        qrcode_key, qrcode_url = await _fetch_qrcode(http, bot_type)
        logger.info("QR code obtained: %s", qrcode_url)

        if print_qr:
            _try_print_qr_terminal(qrcode_url)
            print(f"\n扫描二维码登录，或在浏览器打开:\n{qrcode_url}\n")

        if on_qr_url:
            on_qr_url(qrcode_url)

        current_poll_base = _FIXED_BASE_URL
        deadline = asyncio.get_event_loop().time() + timeout_s
        refresh_count = 0
        scanned_printed = False

        while asyncio.get_event_loop().time() < deadline:
            status_data = await _poll_status(http, current_poll_base, qrcode_key)
            status = status_data.get("status", QRLoginStatus.WAIT)

            if status == QRLoginStatus.WAIT:
                pass

            elif status == QRLoginStatus.SCANNED:
                if not scanned_printed:
                    logger.info("QR scanned, waiting for confirmation...")
                    print("已扫码，请在微信中确认...")
                    scanned_printed = True

            elif status == QRLoginStatus.CONFIRMED:
                bot_token = status_data.get("bot_token", "")
                account_id = status_data.get("ilink_bot_id", "")
                result_base_url = status_data.get("baseurl") or base_url
                user_id = status_data.get("ilink_user_id")

                if not account_id:
                    raise AuthError("Login confirmed but server did not return ilink_bot_id")

                logger.info("Login confirmed: account_id=%s", account_id)
                return LoginResult(
                    token=bot_token,
                    account_id=account_id,
                    base_url=result_base_url,
                    user_id=user_id,
                )

            elif status == QRLoginStatus.EXPIRED:
                refresh_count += 1
                if refresh_count >= _MAX_QR_REFRESH:
                    raise AuthError("QR code expired too many times")

                logger.info("QR expired, refreshing (%d/%d)...", refresh_count, _MAX_QR_REFRESH)
                qrcode_key, qrcode_url = await _fetch_qrcode(http, bot_type)
                scanned_printed = False

                if print_qr:
                    _try_print_qr_terminal(qrcode_url)
                    print(f"\n新二维码已生成，请重新扫描:\n{qrcode_url}\n")
                if on_qr_url:
                    on_qr_url(qrcode_url)

            elif status == QRLoginStatus.SCANNED_REDIRECT:
                redirect_host = status_data.get("redirect_host", "")
                if redirect_host:
                    current_poll_base = f"https://{redirect_host}/"
                    logger.info("Redirecting poll to %s", current_poll_base)

            await asyncio.sleep(1.0)

        raise AuthError(f"Login timed out after {timeout_s}s")
