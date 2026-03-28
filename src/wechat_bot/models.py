"""Pydantic v2 models mirroring the WeChat iLink Bot JSON protocol."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = [
    "BaseInfo",
    "TextItem",
    "CDNMedia",
    "ImageItem",
    "VoiceItem",
    "FileItem",
    "VideoItem",
    "RefMessage",
    "MessageItem",
    "WeixinMessage",
    "GetUpdatesRequest",
    "GetUpdatesResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "GetUploadUrlRequest",
    "GetUploadUrlResponse",
    "SendTypingRequest",
    "SendTypingResponse",
    "GetConfigResponse",
    "LoginResult",
]


class _Proto(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class BaseInfo(_Proto):
    channel_version: str | None = None


class TextItem(_Proto):
    text: str | None = None


class CDNMedia(_Proto):
    encrypt_query_param: str | None = None
    aes_key: str | None = None
    encrypt_type: int | None = None
    full_url: str | None = None


class ImageItem(_Proto):
    media: CDNMedia | None = None
    thumb_media: CDNMedia | None = None
    aeskey: str | None = None
    url: str | None = None
    mid_size: int | None = None
    thumb_size: int | None = None
    thumb_height: int | None = None
    thumb_width: int | None = None
    hd_size: int | None = None


class VoiceItem(_Proto):
    media: CDNMedia | None = None
    encode_type: int | None = None
    bits_per_sample: int | None = None
    sample_rate: int | None = None
    playtime: int | None = None
    text: str | None = None


class FileItem(_Proto):
    media: CDNMedia | None = None
    file_name: str | None = None
    md5: str | None = None
    len: str | None = None


class VideoItem(_Proto):
    media: CDNMedia | None = None
    video_size: int | None = None
    play_length: int | None = None
    video_md5: str | None = None
    thumb_media: CDNMedia | None = None
    thumb_size: int | None = None
    thumb_height: int | None = None
    thumb_width: int | None = None


class RefMessage(_Proto):
    message_item: MessageItem | None = None
    title: str | None = None


class MessageItem(_Proto):
    type: int | None = None
    create_time_ms: int | None = None
    update_time_ms: int | None = None
    is_completed: bool | None = None
    msg_id: str | None = None
    ref_msg: RefMessage | None = None
    text_item: TextItem | None = None
    image_item: ImageItem | None = None
    voice_item: VoiceItem | None = None
    file_item: FileItem | None = None
    video_item: VideoItem | None = None


class WeixinMessage(_Proto):
    seq: int | None = None
    message_id: int | None = None
    from_user_id: str | None = None
    to_user_id: str | None = None
    client_id: str | None = None
    create_time_ms: int | None = None
    update_time_ms: int | None = None
    delete_time_ms: int | None = None
    session_id: str | None = None
    group_id: str | None = None
    message_type: int | None = None
    message_state: int | None = None
    item_list: list[MessageItem] | None = None
    context_token: str | None = None


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class GetUpdatesRequest(_Proto):
    get_updates_buf: str = ""
    base_info: BaseInfo | None = None


class GetUpdatesResponse(_Proto):
    ret: int | None = None
    errcode: int | None = None
    errmsg: str | None = None
    msgs: list[WeixinMessage] | None = None
    get_updates_buf: str | None = None
    longpolling_timeout_ms: int | None = None


class SendMessageRequest(_Proto):
    msg: WeixinMessage | None = None
    base_info: BaseInfo | None = None


class SendMessageResponse(_Proto):
    pass


class GetUploadUrlRequest(_Proto):
    filekey: str | None = None
    media_type: int | None = None
    to_user_id: str | None = None
    rawsize: int | None = None
    rawfilemd5: str | None = None
    filesize: int | None = None
    thumb_rawsize: int | None = None
    thumb_rawfilemd5: str | None = None
    thumb_filesize: int | None = None
    no_need_thumb: bool | None = None
    aeskey: str | None = None
    base_info: BaseInfo | None = None


class GetUploadUrlResponse(_Proto):
    upload_param: str | None = None
    thumb_upload_param: str | None = None
    upload_full_url: str | None = None


class SendTypingRequest(_Proto):
    ilink_user_id: str | None = None
    typing_ticket: str | None = None
    status: int | None = None
    base_info: BaseInfo | None = None


class SendTypingResponse(_Proto):
    ret: int | None = None
    errmsg: str | None = None


class GetConfigResponse(_Proto):
    ret: int | None = None
    errmsg: str | None = None
    typing_ticket: str | None = None


# ---------------------------------------------------------------------------
# SDK-level models (not part of the wire protocol)
# ---------------------------------------------------------------------------


class LoginResult(BaseModel):
    """Result of a successful QR code login."""

    token: str
    account_id: str
    base_url: str | None = None
    user_id: str | None = None
