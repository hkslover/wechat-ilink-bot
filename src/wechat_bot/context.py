"""MessageContext — rich wrapper around an inbound WeixinMessage."""

from __future__ import annotations

import base64
import os
import uuid
from mimetypes import guess_type
from typing import TYPE_CHECKING

from .models import (
    CDNMedia,
    MessageItem,
    TextItem,
    WeixinMessage,
)
from .types import MessageItemType, MessageState, MessageType, UploadMediaType

if TYPE_CHECKING:
    from .client import WeChatClient
    from .storage import Storage

__all__ = ["MessageContext"]


def _generate_client_id() -> str:
    return f"wechat-bot-{uuid.uuid4().hex[:12]}"


def _extract_text(msg: WeixinMessage) -> str:
    for item in msg.item_list or []:
        if item.type == MessageItemType.TEXT and item.text_item and item.text_item.text:
            return item.text_item.text
        if item.type == MessageItemType.VOICE and item.voice_item and item.voice_item.text:
            return item.voice_item.text
    return ""


def _guess_media_type(file_path: str) -> UploadMediaType:
    mime, _ = guess_type(file_path)
    if mime:
        if mime.startswith("image/"):
            return UploadMediaType.IMAGE
        if mime.startswith("video/"):
            return UploadMediaType.VIDEO
    return UploadMediaType.FILE


class MessageContext:
    """Convenience wrapper provided to every handler callback.

    Attributes:
        message: The raw :class:`WeixinMessage`.
        from_user: Sender user ID.
        text: Extracted text body (from TEXT or voice-to-text items).
        items: Shortcut for ``message.item_list``.
        account_id: Bot account ID processing this message.
    """

    def __init__(
        self,
        message: WeixinMessage,
        *,
        client: WeChatClient,
        storage: Storage,
        account_id: str,
        cdn_base_url: str,
    ) -> None:
        self.message = message
        self.from_user: str = message.from_user_id or ""
        self.text: str = _extract_text(message)
        self.items: list[MessageItem] = message.item_list or []
        self.account_id = account_id

        self._client = client
        self._storage = storage
        self._cdn_base_url = cdn_base_url

    @property
    def context_token(self) -> str | None:
        """The context_token for this conversation, looked up from storage."""
        return self._storage.get_context_token(self.account_id, self.from_user)

    # ------------------------------------------------------------------
    # Send helpers
    # ------------------------------------------------------------------

    def _build_outbound_msg(self, item_list: list[MessageItem]) -> WeixinMessage:
        return WeixinMessage(
            from_user_id="",
            to_user_id=self.from_user,
            client_id=_generate_client_id(),
            message_type=MessageType.BOT,
            message_state=MessageState.FINISH,
            item_list=item_list if item_list else None,
            context_token=self.context_token or None,
        )

    async def reply(self, text: str) -> None:
        """Reply with a text message."""
        item = MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text))
        msg = self._build_outbound_msg([item])
        await self._client.send_message(msg)

    async def reply_image(self, file_path: str, caption: str = "") -> None:
        """Reply with an image (optionally with a text caption)."""
        await self._reply_media(file_path, caption, UploadMediaType.IMAGE)

    async def reply_video(self, file_path: str, caption: str = "") -> None:
        """Reply with a video."""
        await self._reply_media(file_path, caption, UploadMediaType.VIDEO)

    async def reply_file(self, file_path: str, caption: str = "") -> None:
        """Reply with a file attachment."""
        await self._reply_media(file_path, caption, UploadMediaType.FILE)

    async def _reply_media(
        self,
        file_path: str,
        caption: str,
        media_type: UploadMediaType,
    ) -> None:
        from .media.upload import upload_media

        uploaded = await upload_media(
            self._client,
            file_path=file_path,
            to_user_id=self.from_user,
            media_type=media_type,
            cdn_base_url=self._cdn_base_url,
        )

        items: list[MessageItem] = []
        if caption:
            items.append(MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=caption)))

        media_item = _build_media_item(uploaded, media_type, file_path)
        items.append(media_item)

        for item in items:
            msg = self._build_outbound_msg([item])
            await self._client.send_message(msg)

    async def send_typing(self) -> None:
        """Send a typing indicator to the conversation partner.

        The underlying ``get_config`` lookup is short-lived cached by client,
        so repeated calls in one conversation avoid redundant network fetches.
        """
        config = await self._client.get_config(self.from_user, self.context_token)
        if config.typing_ticket:
            await self._client.send_typing(self.from_user, config.typing_ticket)

    # ------------------------------------------------------------------
    # Media download
    # ------------------------------------------------------------------

    async def download_media(self, save_dir: str) -> str | None:
        """Download the first media item to *save_dir*. Returns saved path or ``None``."""
        from .media.download import download_media_to_file

        for item in self.items:
            media, aeskey_hex, filename = _resolve_media_from_item(item)
            if media is None:
                continue
            return await download_media_to_file(
                media,
                self._cdn_base_url,
                save_dir,
                filename=filename,
                aeskey_hex_override=aeskey_hex,
            )
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_media_item(
    uploaded: object,  # UploadedMedia
    media_type: UploadMediaType,
    file_path: str,
) -> MessageItem:
    from .media.upload import UploadedMedia

    assert isinstance(uploaded, UploadedMedia)
    cdn_media = CDNMedia(
        encrypt_query_param=uploaded.download_encrypted_query_param,
        aes_key=base64.b64encode(uploaded.aeskey_hex.encode("ascii")).decode(),
        encrypt_type=1,
    )

    if media_type == UploadMediaType.IMAGE:
        from .models import ImageItem

        return MessageItem(
            type=MessageItemType.IMAGE,
            image_item=ImageItem(media=cdn_media, mid_size=uploaded.file_size_ciphertext),
        )
    if media_type == UploadMediaType.VIDEO:
        from .models import VideoItem

        return MessageItem(
            type=MessageItemType.VIDEO,
            video_item=VideoItem(media=cdn_media, video_size=uploaded.file_size_ciphertext),
        )
    # FILE (and VOICE falls through to FILE)
    from .models import FileItem

    return MessageItem(
        type=MessageItemType.FILE,
        file_item=FileItem(
            media=cdn_media,
            file_name=os.path.basename(file_path),
            len=str(uploaded.file_size),
        ),
    )


def _resolve_media_from_item(
    item: MessageItem,
) -> tuple[CDNMedia | None, str | None, str]:
    """Extract CDNMedia, optional hex aes key override, and a filename."""
    if item.type == MessageItemType.IMAGE and item.image_item:
        media = item.image_item.media
        aeskey_hex = item.image_item.aeskey  # hex override for images
        return media, aeskey_hex, f"image_{uuid.uuid4().hex[:8]}.jpg"
    if item.type == MessageItemType.VOICE and item.voice_item:
        return item.voice_item.media, None, f"voice_{uuid.uuid4().hex[:8]}.silk"
    if item.type == MessageItemType.FILE and item.file_item:
        fname = item.file_item.file_name or f"file_{uuid.uuid4().hex[:8]}.bin"
        return item.file_item.media, None, fname
    if item.type == MessageItemType.VIDEO and item.video_item:
        return item.video_item.media, None, f"video_{uuid.uuid4().hex[:8]}.mp4"
    return None, None, ""
