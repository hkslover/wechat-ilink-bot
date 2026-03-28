"""Tests for Pydantic protocol models."""

from wechat_bot.models import (
    GetUpdatesResponse,
    MessageItem,
    SendMessageRequest,
    TextItem,
    WeixinMessage,
)
from wechat_bot.types import MessageItemType, MessageState, MessageType


class TestWeixinMessage:
    def test_roundtrip_text_message(self):
        msg = WeixinMessage(
            from_user_id="user123@im.wechat",
            to_user_id="bot456@im.bot",
            message_type=MessageType.USER,
            message_state=MessageState.FINISH,
            item_list=[
                MessageItem(
                    type=MessageItemType.TEXT,
                    text_item=TextItem(text="Hello Bot"),
                )
            ],
            context_token="tok_abc",
        )

        data = msg.model_dump(exclude_none=True)
        restored = WeixinMessage.model_validate(data)

        assert restored.from_user_id == "user123@im.wechat"
        assert restored.context_token == "tok_abc"
        assert restored.item_list is not None
        assert len(restored.item_list) == 1
        assert restored.item_list[0].text_item is not None
        assert restored.item_list[0].text_item.text == "Hello Bot"

    def test_from_json_dict(self):
        raw = {
            "from_user_id": "abc@im.wechat",
            "item_list": [{"type": 1, "text_item": {"text": "hi"}}],
            "context_token": "ctx_1",
        }
        msg = WeixinMessage.model_validate(raw)
        assert msg.from_user_id == "abc@im.wechat"
        assert msg.item_list is not None
        assert msg.item_list[0].type == MessageItemType.TEXT

    def test_extra_fields_are_preserved(self):
        raw = {"from_user_id": "u1", "unknown_field": 42}
        msg = WeixinMessage.model_validate(raw)
        assert msg.from_user_id == "u1"


class TestGetUpdatesResponse:
    def test_empty_response(self):
        resp = GetUpdatesResponse(ret=0, msgs=[])
        assert resp.ret == 0
        assert resp.msgs == []

    def test_parse_with_messages(self):
        raw = {
            "ret": 0,
            "msgs": [
                {
                    "from_user_id": "u1",
                    "item_list": [{"type": 1, "text_item": {"text": "ping"}}],
                }
            ],
            "get_updates_buf": "buf123",
        }
        resp = GetUpdatesResponse.model_validate(raw)
        assert resp.msgs is not None
        assert len(resp.msgs) == 1
        assert resp.get_updates_buf == "buf123"


class TestSendMessageRequest:
    def test_serialize(self):
        req = SendMessageRequest(
            msg=WeixinMessage(
                to_user_id="target",
                item_list=[
                    MessageItem(
                        type=MessageItemType.TEXT,
                        text_item=TextItem(text="reply"),
                    )
                ],
            )
        )
        data = req.model_dump(exclude_none=True)
        assert "msg" in data
        assert data["msg"]["to_user_id"] == "target"
