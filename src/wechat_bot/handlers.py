"""Handler and filter system for incoming messages."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from .models import WeixinMessage
from .types import MessageItemType

if TYPE_CHECKING:
    from .context import MessageContext

__all__ = ["Filter", "MessageHandler", "HandlerCallback"]

HandlerCallback = Callable[["MessageContext"], Awaitable[Any]]


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class Filter:
    """Composable message filter.

    Filters can be combined with ``&`` (AND) and ``|`` (OR)::

        Filter.text() & Filter.text_startswith("/")
        Filter.image() | Filter.video()
    """

    def __init__(self, func: Callable[[WeixinMessage], bool], name: str = "") -> None:
        self._func = func
        self._name = name or repr(func)

    def __call__(self, msg: WeixinMessage) -> bool:
        return self._func(msg)

    def __and__(self, other: Filter) -> Filter:
        return Filter(
            lambda m: self._func(m) and other._func(m),
            name=f"({self._name} & {other._name})",
        )

    def __or__(self, other: Filter) -> Filter:
        return Filter(
            lambda m: self._func(m) or other._func(m),
            name=f"({self._name} | {other._name})",
        )

    def __invert__(self) -> Filter:
        return Filter(lambda m: not self._func(m), name=f"~{self._name}")

    def __repr__(self) -> str:
        return f"Filter({self._name})"

    # ------------------------------------------------------------------
    # Built-in filters
    # ------------------------------------------------------------------

    @staticmethod
    def all() -> Filter:
        """Match every message."""
        return Filter(lambda _: True, name="all")

    @staticmethod
    def text() -> Filter:
        """Match messages that contain at least one TEXT item."""
        return Filter(_has_item_type(MessageItemType.TEXT), name="text")

    @staticmethod
    def image() -> Filter:
        """Match messages that contain at least one IMAGE item."""
        return Filter(_has_item_type(MessageItemType.IMAGE), name="image")

    @staticmethod
    def voice() -> Filter:
        """Match messages that contain at least one VOICE item."""
        return Filter(_has_item_type(MessageItemType.VOICE), name="voice")

    @staticmethod
    def file() -> Filter:
        """Match messages that contain at least one FILE item."""
        return Filter(_has_item_type(MessageItemType.FILE), name="file")

    @staticmethod
    def video() -> Filter:
        """Match messages that contain at least one VIDEO item."""
        return Filter(_has_item_type(MessageItemType.VIDEO), name="video")

    @staticmethod
    def text_startswith(prefix: str) -> Filter:
        """Match messages whose text body starts with *prefix*."""

        def _check(msg: WeixinMessage) -> bool:
            body = _extract_text(msg)
            return body.startswith(prefix) if body else False

        return Filter(_check, name=f"text_startswith({prefix!r})")

    @staticmethod
    def text_regex(pattern: str) -> Filter:
        """Match messages whose text body matches the regex *pattern*."""
        compiled = re.compile(pattern)

        def _check(msg: WeixinMessage) -> bool:
            body = _extract_text(msg)
            return bool(compiled.search(body)) if body else False

        return Filter(_check, name=f"text_regex({pattern!r})")

    @staticmethod
    def from_user(user_id: str) -> Filter:
        """Match messages from a specific user."""
        return Filter(
            lambda m: (m.from_user_id or "") == user_id,
            name=f"from_user({user_id!r})",
        )

    @staticmethod
    def custom(func: Callable[[WeixinMessage], bool], name: str = "custom") -> Filter:
        """Create a filter from an arbitrary callable."""
        return Filter(func, name=name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_item_type(item_type: int) -> Callable[[WeixinMessage], bool]:
    def _check(msg: WeixinMessage) -> bool:
        if not msg.item_list:
            return False
        return any(item.type == item_type for item in msg.item_list)

    return _check


def _extract_text(msg: WeixinMessage) -> str:
    """Extract the first text body from a message's item_list."""
    if not msg.item_list:
        return ""
    for item in msg.item_list:
        if item.type == MessageItemType.TEXT and item.text_item and item.text_item.text:
            return item.text_item.text
        if item.type == MessageItemType.VOICE and item.voice_item and item.voice_item.text:
            return item.voice_item.text
    return ""


# ---------------------------------------------------------------------------
# MessageHandler
# ---------------------------------------------------------------------------


class MessageHandler:
    """Pairs a callback with an optional filter and priority.

    Handlers with lower priority numbers run first. Only the first
    matching handler (by priority order) is invoked for a given message.
    """

    def __init__(
        self,
        callback: HandlerCallback,
        filters: Filter | None = None,
        priority: int = 0,
    ) -> None:
        self.callback = callback
        self.filters = filters or Filter.all()
        self.priority = priority

    def check(self, msg: WeixinMessage) -> bool:
        """Return ``True`` if this handler should process *msg*."""
        return self.filters(msg)

    def __repr__(self) -> str:
        return (
            f"MessageHandler(callback={self.callback.__name__}, "
            f"filters={self.filters}, priority={self.priority})"
        )
