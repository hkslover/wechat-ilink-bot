"""wechat_bot — Python SDK for the WeChat iLink Bot API."""

from ._version import __version__
from .bot import Bot
from .client import WeChatClient
from .context import MessageContext
from .errors import APIError, AuthError, MediaError, SessionExpiredError, WeChatBotError
from .handlers import Filter, MessageHandler
from .models import (
    CDNMedia,
    FileItem,
    GetConfigResponse,
    GetUpdatesResponse,
    GetUploadUrlRequest,
    GetUploadUrlResponse,
    ImageItem,
    LoginResult,
    MessageItem,
    RefMessage,
    SendMessageRequest,
    TextItem,
    VideoItem,
    VoiceItem,
    WeixinMessage,
)
from .storage import Storage
from .types import (
    DEFAULT_BASE_URL,
    DEFAULT_CDN_BASE_URL,
    MessageItemType,
    MessageState,
    MessageType,
    TypingStatus,
    UploadMediaType,
)
from .webhook import create_webhook_app, run_webhook_server

__all__ = [
    "__version__",
    # Core
    "Bot",
    "WeChatClient",
    "MessageContext",
    "Storage",
    "create_webhook_app",
    "run_webhook_server",
    # Handlers
    "Filter",
    "MessageHandler",
    # Models
    "CDNMedia",
    "FileItem",
    "GetConfigResponse",
    "GetUpdatesResponse",
    "GetUploadUrlRequest",
    "GetUploadUrlResponse",
    "ImageItem",
    "LoginResult",
    "MessageItem",
    "RefMessage",
    "SendMessageRequest",
    "TextItem",
    "VideoItem",
    "VoiceItem",
    "WeixinMessage",
    # Types / enums
    "DEFAULT_BASE_URL",
    "DEFAULT_CDN_BASE_URL",
    "MessageItemType",
    "MessageState",
    "MessageType",
    "TypingStatus",
    "UploadMediaType",
    # Errors
    "APIError",
    "AuthError",
    "MediaError",
    "SessionExpiredError",
    "WeChatBotError",
]
