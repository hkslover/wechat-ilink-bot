"""Smoke tests for QR auth flow without real network requests."""

from __future__ import annotations

import pytest

from wechat_bot.auth import login_with_qr
from wechat_bot.errors import AuthError
from wechat_bot.types import QRLoginStatus


class _DummyAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


def _dummy_async_client_factory(*args, **kwargs):
    del args, kwargs
    return _DummyAsyncClient()


@pytest.mark.asyncio
async def test_login_with_qr_confirmed(monkeypatch):
    async def _fake_fetch_qrcode(_http, _bot_type: str):
        return "qr_key_1", "https://example.com/qr"

    async def _fake_poll_status(_http, _base_url: str, _qrcode_key: str):
        return {
            "status": QRLoginStatus.CONFIRMED,
            "bot_token": "token_abc",
            "ilink_bot_id": "acct_123",
            "baseurl": "https://api.example",
            "ilink_user_id": "user_456",
        }

    monkeypatch.setattr("wechat_bot.auth._fetch_qrcode", _fake_fetch_qrcode)
    monkeypatch.setattr("wechat_bot.auth._poll_status", _fake_poll_status)
    monkeypatch.setattr("wechat_bot.auth.httpx.AsyncClient", _dummy_async_client_factory)

    result = await login_with_qr(print_qr=False, timeout_s=5)
    assert result.token == "token_abc"
    assert result.account_id == "acct_123"
    assert result.base_url == "https://api.example"
    assert result.user_id == "user_456"


@pytest.mark.asyncio
async def test_login_with_qr_timeout(monkeypatch):
    async def _fake_fetch_qrcode(_http, _bot_type: str):
        return "qr_key_1", "https://example.com/qr"

    monkeypatch.setattr("wechat_bot.auth._fetch_qrcode", _fake_fetch_qrcode)
    monkeypatch.setattr("wechat_bot.auth.httpx.AsyncClient", _dummy_async_client_factory)

    with pytest.raises(AuthError, match="timed out"):
        await login_with_qr(print_qr=False, timeout_s=0)
