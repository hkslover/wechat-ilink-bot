"""Tests for the low-level HTTP client (with mocked httpx)."""

import httpx
import pytest

from wechat_bot.client import (
    WeChatClient,
    _base_info,
    _build_client_version,
    _random_wechat_uin,
)
from wechat_bot.models import GetUpdatesResponse


class TestClientHelpers:
    def test_random_wechat_uin_is_base64(self):
        import base64

        uin = _random_wechat_uin()
        decoded = base64.b64decode(uin)
        assert decoded.isdigit()

    def test_build_client_version(self):
        assert _build_client_version("1.0.11") == (1 << 16) | (0 << 8) | 11
        assert _build_client_version("0.1.0") == (0 << 16) | (1 << 8) | 0
        assert _build_client_version("2.3.4") == (2 << 16) | (3 << 8) | 4

    def test_base_info(self):
        info = _base_info()
        assert "channel_version" in info


class TestWeChatClientInit:
    def test_default_values(self):
        client = WeChatClient()
        assert "ilinkai.weixin.qq.com" in client.base_url
        assert client.token == ""

    def test_custom_values(self):
        client = WeChatClient(
            base_url="https://custom.host",
            token="tok123",
            cdn_base_url="https://cdn.custom",
        )
        assert client.base_url == "https://custom.host/"
        assert client.token == "tok123"
        assert client.cdn_base_url == "https://cdn.custom"

    def test_headers_include_auth_when_token_set(self):
        client = WeChatClient(token="my_secret_token")
        headers = client._post_headers()
        assert headers["Authorization"] == "Bearer my_secret_token"
        assert headers["AuthorizationType"] == "ilink_bot_token"
        assert "iLink-App-Id" in headers

    def test_headers_omit_auth_when_no_token(self):
        client = WeChatClient(token="")
        headers = client._post_headers()
        assert "Authorization" not in headers


class TestWeChatClientMocked:
    @pytest.mark.asyncio
    async def test_get_updates_timeout_returns_empty(self):
        client = WeChatClient(token="tok")
        transport = httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ReadTimeout("")))
        client._http = httpx.AsyncClient(transport=transport)

        resp = await client.get_updates(get_updates_buf="buf1", timeout_ms=1000)
        assert isinstance(resp, GetUpdatesResponse)
        assert resp.ret == 0
        assert resp.msgs == []
        assert resp.get_updates_buf == "buf1"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_updates_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "ret": 0,
                    "msgs": [
                        {
                            "from_user_id": "u1@im.wechat",
                            "item_list": [{"type": 1, "text_item": {"text": "hi"}}],
                        }
                    ],
                    "get_updates_buf": "newbuf",
                },
            )

        client = WeChatClient(token="tok")
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        resp = await client.get_updates()
        assert resp.ret == 0
        assert resp.msgs is not None
        assert len(resp.msgs) == 1
        assert resp.get_updates_buf == "newbuf"

        await client.close()

    @pytest.mark.asyncio
    async def test_send_message(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        client = WeChatClient(token="tok")
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        from wechat_bot.models import MessageItem, TextItem, WeixinMessage
        from wechat_bot.types import MessageItemType, MessageState, MessageType

        msg = WeixinMessage(
            to_user_id="target",
            message_type=MessageType.BOT,
            message_state=MessageState.FINISH,
            item_list=[
                MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text="hello"))
            ],
        )
        await client.send_message(msg)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_config_uses_cache(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(200, json={"ret": 0, "typing_ticket": "ticket_1"})

        client = WeChatClient(token="tok", config_cache_ttl_s=60.0)
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        resp1 = await client.get_config("user1", context_token="ctx1")
        resp2 = await client.get_config("user1", context_token="ctx1")
        assert resp1.typing_ticket == "ticket_1"
        assert resp2.typing_ticket == "ticket_1"
        assert calls["count"] == 1

        await client.close()

    @pytest.mark.asyncio
    async def test_get_config_cache_distinguishes_context_token(self):
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(200, json={"ret": 0, "typing_ticket": f"ticket_{calls['count']}"})

        client = WeChatClient(token="tok", config_cache_ttl_s=60.0)
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        resp1 = await client.get_config("user1", context_token="ctx_a")
        resp2 = await client.get_config("user1", context_token="ctx_b")
        assert resp1.typing_ticket == "ticket_1"
        assert resp2.typing_ticket == "ticket_2"
        assert calls["count"] == 2

        await client.close()
