"""Enumerations and constants for the WeChat iLink Bot protocol."""

from __future__ import annotations

from enum import IntEnum

__all__ = [
    "MessageItemType",
    "MessageType",
    "MessageState",
    "UploadMediaType",
    "TypingStatus",
    "QRLoginStatus",
    "DEFAULT_BASE_URL",
    "DEFAULT_CDN_BASE_URL",
    "DEFAULT_BOT_TYPE",
    "SESSION_EXPIRED_ERRCODE",
]

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
DEFAULT_CDN_BASE_URL = "https://novac2c.cdn.weixin.qq.com/c2c"
DEFAULT_BOT_TYPE = "3"
SESSION_EXPIRED_ERRCODE = -14


class MessageItemType(IntEnum):
    """Type of a single message item within a WeixinMessage."""

    TEXT = 1
    IMAGE = 2
    VOICE = 3
    FILE = 4
    VIDEO = 5


class MessageType(IntEnum):
    """Sender type: user or bot."""

    USER = 1
    BOT = 2


class MessageState(IntEnum):
    """Delivery state of a message."""

    NEW = 0
    GENERATING = 1
    FINISH = 2


class UploadMediaType(IntEnum):
    """Media type used in CDN upload requests."""

    IMAGE = 1
    VIDEO = 2
    FILE = 3
    VOICE = 4


class TypingStatus(IntEnum):
    """Typing indicator status."""

    TYPING = 1
    CANCEL = 2


class QRLoginStatus:
    """Status strings returned by get_qrcode_status."""

    WAIT = "wait"
    SCANNED = "scaned"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    SCANNED_REDIRECT = "scaned_but_redirect"
