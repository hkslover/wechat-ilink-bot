"""Exception hierarchy for wechat_bot."""

from __future__ import annotations

__all__ = [
    "WeChatBotError",
    "AuthError",
    "APIError",
    "MediaError",
    "SessionExpiredError",
]


class WeChatBotError(Exception):
    """Base exception for all wechat_bot errors."""


class AuthError(WeChatBotError):
    """Raised when QR login or authentication fails."""


class APIError(WeChatBotError):
    """Raised when the iLink API returns an error response."""

    def __init__(self, message: str, *, ret: int | None = None, errcode: int | None = None):
        self.ret = ret
        self.errcode = errcode
        super().__init__(message)


class SessionExpiredError(APIError):
    """Raised when the server returns errcode -14 (session timeout)."""


class MediaError(WeChatBotError):
    """Raised when media upload or download fails."""
