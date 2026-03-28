"""Tests for Poller error handling and session recovery."""

from __future__ import annotations

import asyncio

import pytest

from wechat_bot.models import GetUpdatesResponse
from wechat_bot.polling import Poller
from wechat_bot.storage import Storage
from wechat_bot.types import SESSION_EXPIRED_ERRCODE


class _FakeClient:
    def __init__(self, responses: list[GetUpdatesResponse]) -> None:
        self._responses = responses
        self.calls = 0

    async def get_updates(
        self,
        get_updates_buf: str = "",
        timeout_ms: int | None = None,
    ) -> GetUpdatesResponse:
        del get_updates_buf, timeout_ms
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[index]


@pytest.mark.asyncio
async def test_poller_stops_on_session_expired_without_recovery(tmp_path):
    client = _FakeClient(
        [GetUpdatesResponse(ret=SESSION_EXPIRED_ERRCODE, errcode=SESSION_EXPIRED_ERRCODE)]
    )
    storage = Storage(state_dir=str(tmp_path))

    async def _on_message(_msg: object) -> None:
        return None

    poller = Poller(client=client, storage=storage, account_id="acct", on_message=_on_message)
    await asyncio.wait_for(poller._loop(), timeout=1.0)

    assert poller.stopped_due_to_session_expired
    assert client.calls == 1


@pytest.mark.asyncio
async def test_poller_uses_recovery_callback_and_keeps_running(tmp_path):
    client = _FakeClient(
        [
            GetUpdatesResponse(ret=SESSION_EXPIRED_ERRCODE, errcode=SESSION_EXPIRED_ERRCODE),
            GetUpdatesResponse(ret=0, msgs=[]),
        ]
    )
    storage = Storage(state_dir=str(tmp_path))
    recovered: list[bool] = []

    async def _on_message(_msg: object) -> None:
        return None

    async def _on_session_expired() -> bool:
        recovered.append(True)
        return True

    poller = Poller(
        client=client,
        storage=storage,
        account_id="acct",
        on_message=_on_message,
        on_session_expired=_on_session_expired,
    )

    async def _stop_after_recovery_sleep(_seconds: float) -> None:
        poller._stop_event.set()

    poller._interruptible_sleep = _stop_after_recovery_sleep  # type: ignore[method-assign]
    await asyncio.wait_for(poller._loop(), timeout=1.0)

    assert recovered == [True]
    assert not poller.stopped_due_to_session_expired
    assert client.calls >= 1
