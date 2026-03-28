"""Tests for the handler and filter system."""

from __future__ import annotations

from wechat_bot.handlers import Filter
from wechat_bot.models import (
    ImageItem,
    MessageItem,
    TextItem,
    VoiceItem,
    WeixinMessage,
)
from wechat_bot.types import MessageItemType


def _text_msg(text: str, from_user: str = "u1") -> WeixinMessage:
    return WeixinMessage(
        from_user_id=from_user,
        item_list=[
            MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text)),
        ],
    )


def _image_msg(from_user: str = "u1") -> WeixinMessage:
    return WeixinMessage(
        from_user_id=from_user,
        item_list=[
            MessageItem(type=MessageItemType.IMAGE, image_item=ImageItem()),
        ],
    )


def _voice_msg(text: str | None = None) -> WeixinMessage:
    return WeixinMessage(
        from_user_id="u1",
        item_list=[
            MessageItem(
                type=MessageItemType.VOICE,
                voice_item=VoiceItem(text=text),
            ),
        ],
    )


class TestFilterBasic:
    def test_all_matches_everything(self):
        assert Filter.all()(_text_msg("hi"))
        assert Filter.all()(_image_msg())

    def test_text_filter(self):
        assert Filter.text()(_text_msg("hello"))
        assert not Filter.text()(_image_msg())

    def test_image_filter(self):
        assert Filter.image()(_image_msg())
        assert not Filter.image()(_text_msg("hi"))

    def test_voice_filter(self):
        assert Filter.voice()(_voice_msg())
        assert not Filter.voice()(_text_msg("hi"))


class TestFilterText:
    def test_startswith(self):
        f = Filter.text_startswith("/cmd")
        assert f(_text_msg("/cmd do_thing"))
        assert not f(_text_msg("hello /cmd"))
        assert not f(_image_msg())

    def test_regex(self):
        f = Filter.text_regex(r"^\d{3}$")
        assert f(_text_msg("123"))
        assert not f(_text_msg("12"))
        assert not f(_text_msg("abc"))


class TestFilterCombination:
    def test_and(self):
        f = Filter.text() & Filter.text_startswith("/")
        assert f(_text_msg("/help"))
        assert not f(_text_msg("no slash"))
        assert not f(_image_msg())

    def test_or(self):
        f = Filter.image() | Filter.voice()
        assert f(_image_msg())
        assert f(_voice_msg())
        assert not f(_text_msg("hi"))

    def test_invert(self):
        f = ~Filter.text()
        assert f(_image_msg())
        assert not f(_text_msg("hi"))

    def test_complex_combination(self):
        f = Filter.text_startswith("/admin") & Filter.from_user("admin@im.wechat")
        assert f(_text_msg("/admin reload", from_user="admin@im.wechat"))
        assert not f(_text_msg("/admin reload", from_user="other@im.wechat"))
        assert not f(_text_msg("hello", from_user="admin@im.wechat"))


class TestFilterFromUser:
    def test_from_user(self):
        f = Filter.from_user("admin@im.wechat")
        assert f(_text_msg("hi", from_user="admin@im.wechat"))
        assert not f(_text_msg("hi", from_user="other@im.wechat"))
