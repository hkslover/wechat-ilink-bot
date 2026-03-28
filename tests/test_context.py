"""Smoke tests for MessageContext helper behavior."""

from __future__ import annotations

import pytest

from wechat_bot.context import MessageContext
from wechat_bot.models import (
    CDNMedia,
    GetConfigResponse,
    ImageItem,
    MessageItem,
    TextItem,
    WeixinMessage,
)
from wechat_bot.storage import Storage
from wechat_bot.types import MessageItemType, TypingStatus


class _FakeClient:
    def __init__(self, *, typing_ticket: str | None = "ticket_1") -> None:
        self.typing_ticket = typing_ticket
        self.sent_messages: list[WeixinMessage] = []
        self.get_config_calls: list[tuple[str, str | None]] = []
        self.send_typing_calls: list[tuple[str, str, int]] = []

    async def send_message(self, msg: WeixinMessage) -> None:
        self.sent_messages.append(msg)

    async def get_config(self, user_id: str, context_token: str | None = None) -> GetConfigResponse:
        self.get_config_calls.append((user_id, context_token))
        return GetConfigResponse(ret=0, typing_ticket=self.typing_ticket)

    async def send_typing(
        self,
        user_id: str,
        typing_ticket: str,
        status: int = TypingStatus.TYPING,
    ) -> None:
        self.send_typing_calls.append((user_id, typing_ticket, status))


def _build_context(tmp_path, client: _FakeClient) -> MessageContext:
    storage = Storage(state_dir=str(tmp_path))
    storage.set_context_token("acct_1", "u_1", "ctx_abc")
    message = WeixinMessage(
        from_user_id="u_1",
        item_list=[
            MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text="hello")),
        ],
    )
    return MessageContext(
        message,
        client=client,
        storage=storage,
        account_id="acct_1",
        cdn_base_url="https://cdn.example/c2c",
    )


@pytest.mark.asyncio
async def test_reply_uses_stored_context_token(tmp_path):
    client = _FakeClient()
    ctx = _build_context(tmp_path, client)

    await ctx.reply("world")

    assert len(client.sent_messages) == 1
    sent = client.sent_messages[0]
    assert sent.context_token == "ctx_abc"
    assert sent.to_user_id == "u_1"


@pytest.mark.asyncio
async def test_send_typing_uses_typing_ticket(tmp_path):
    client = _FakeClient(typing_ticket="typing_123")
    ctx = _build_context(tmp_path, client)

    await ctx.send_typing()

    assert client.get_config_calls == [("u_1", "ctx_abc")]
    assert client.send_typing_calls == [("u_1", "typing_123", TypingStatus.TYPING)]


@pytest.mark.asyncio
async def test_send_typing_skips_when_ticket_missing(tmp_path):
    client = _FakeClient(typing_ticket=None)
    ctx = _build_context(tmp_path, client)

    await ctx.send_typing()

    assert client.get_config_calls == [("u_1", "ctx_abc")]
    assert client.send_typing_calls == []


@pytest.mark.asyncio
async def test_download_media_calls_downloader(monkeypatch, tmp_path):
    called: dict[str, object] = {}

    async def _fake_download_media_to_file(
        media: CDNMedia,
        cdn_base_url: str,
        save_dir: str,
        *,
        filename: str,
        aeskey_hex_override: str | None = None,
    ) -> str:
        called["media"] = media
        called["cdn_base_url"] = cdn_base_url
        called["save_dir"] = save_dir
        called["filename"] = filename
        called["aeskey_hex_override"] = aeskey_hex_override
        return f"{save_dir}/{filename}"

    monkeypatch.setattr(
        "wechat_bot.media.download.download_media_to_file",
        _fake_download_media_to_file,
    )

    storage = Storage(state_dir=str(tmp_path))
    message = WeixinMessage(
        from_user_id="u_1",
        item_list=[
            MessageItem(
                type=MessageItemType.IMAGE,
                image_item=ImageItem(
                    media=CDNMedia(encrypt_query_param="enc"),
                    aeskey="00112233445566778899aabbccddeeff",
                ),
            )
        ],
    )
    ctx = MessageContext(
        message,
        client=_FakeClient(),
        storage=storage,
        account_id="acct_1",
        cdn_base_url="https://cdn.example/c2c",
    )

    saved = await ctx.download_media("/tmp/downloads")

    assert saved is not None
    assert called["cdn_base_url"] == "https://cdn.example/c2c"
    assert called["save_dir"] == "/tmp/downloads"
    assert called["aeskey_hex_override"] == "00112233445566778899aabbccddeeff"
