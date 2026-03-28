"""Long-poll loop for receiving inbound messages."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from ._logging import logger
from .models import WeixinMessage
from .types import SESSION_EXPIRED_ERRCODE

if TYPE_CHECKING:
    from .client import WeChatClient
    from .storage import Storage

__all__ = ["Poller"]

_DEFAULT_LONG_POLL_TIMEOUT_MS = 35_000
_MAX_CONSECUTIVE_FAILURES = 3
_BACKOFF_DELAY_S = 30.0
_RETRY_DELAY_S = 2.0
_SESSION_RECOVERY_DELAY_S = 2.0

MessageCallback = Callable[[WeixinMessage], Awaitable[None]]
SessionExpiredCallback = Callable[[], "bool | Awaitable[bool]"]


class Poller:
    """Manages the getUpdates long-poll loop with retry and back-off.

    Args:
        client: The low-level :class:`WeChatClient`.
        storage: Persistent storage for sync cursor.
        account_id: Bot account ID.
        on_message: Async callback invoked for every inbound message.
    """

    def __init__(
        self,
        client: WeChatClient,
        storage: Storage,
        account_id: str,
        on_message: MessageCallback,
        on_session_expired: SessionExpiredCallback | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self._account_id = account_id
        self._on_message = on_message
        self._on_session_expired = on_session_expired
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._stopped_due_to_session_expired = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the polling loop in the background."""
        if self._task and not self._task.done():
            logger.warning("Poller already running")
            return
        self._stop_event.clear()
        self._stopped_due_to_session_expired = False
        self._task = asyncio.create_task(self._loop())
        logger.info("Poller started for account %s", self._account_id)

    async def stop(self) -> None:
        """Signal the loop to stop and wait for it to finish."""
        self._stop_event.set()
        if self._task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Poller stopped for account %s", self._account_id)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def stopped_due_to_session_expired(self) -> bool:
        return self._stopped_due_to_session_expired

    async def wait_stopped(self) -> None:
        """Wait until polling exits."""
        if self._task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        get_updates_buf = self._storage.load_sync_buf(self._account_id)
        if get_updates_buf:
            logger.debug("Resuming from previous sync buf (%d bytes)", len(get_updates_buf))

        next_timeout_ms = _DEFAULT_LONG_POLL_TIMEOUT_MS
        consecutive_failures = 0

        while not self._stop_event.is_set():
            try:
                resp = await self._client.get_updates(
                    get_updates_buf=get_updates_buf,
                    timeout_ms=next_timeout_ms,
                )

                if resp.longpolling_timeout_ms and resp.longpolling_timeout_ms > 0:
                    next_timeout_ms = resp.longpolling_timeout_ms

                is_error = (resp.ret is not None and resp.ret != 0) or (
                    resp.errcode is not None and resp.errcode != 0
                )

                if is_error:
                    is_session_expired = (
                        resp.errcode == SESSION_EXPIRED_ERRCODE
                        or resp.ret == SESSION_EXPIRED_ERRCODE
                    )

                    if is_session_expired:
                        recovered = await self._try_recover_session()
                        if recovered:
                            logger.info("Session recovered, resume polling")
                            consecutive_failures = 0
                            await self._interruptible_sleep(_SESSION_RECOVERY_DELAY_S)
                            continue
                        logger.error(
                            "Session expired (ret=%s, errcode=%s); stopping poller. "
                            "Please re-login via bot.login().",
                            resp.ret,
                            resp.errcode,
                        )
                        self._stopped_due_to_session_expired = True
                        self._stop_event.set()
                        break

                    consecutive_failures += 1
                    logger.error(
                        "getUpdates error: ret=%s errcode=%s errmsg=%s (%d/%d)",
                        resp.ret,
                        resp.errcode,
                        resp.errmsg,
                        consecutive_failures,
                        _MAX_CONSECUTIVE_FAILURES,
                    )
                    if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                        consecutive_failures = 0
                        await self._interruptible_sleep(_BACKOFF_DELAY_S)
                    else:
                        await self._interruptible_sleep(_RETRY_DELAY_S)
                    continue

                # Success
                consecutive_failures = 0

                if resp.get_updates_buf:
                    self._storage.save_sync_buf(self._account_id, resp.get_updates_buf)
                    get_updates_buf = resp.get_updates_buf

                for msg in resp.msgs or []:
                    if self._stop_event.is_set():
                        break
                    try:
                        await self._on_message(msg)
                    except Exception:
                        logger.exception(
                            "Error in message handler for msg from %s",
                            msg.from_user_id,
                        )

            except asyncio.CancelledError:
                break
            except Exception:
                if self._stop_event.is_set():
                    break
                consecutive_failures += 1
                logger.exception(
                    "getUpdates exception (%d/%d)",
                    consecutive_failures,
                    _MAX_CONSECUTIVE_FAILURES,
                )
                if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    consecutive_failures = 0
                    await self._interruptible_sleep(_BACKOFF_DELAY_S)
                else:
                    await self._interruptible_sleep(_RETRY_DELAY_S)

        logger.debug("Poll loop exited")

    async def _try_recover_session(self) -> bool:
        if self._on_session_expired is None:
            return False
        try:
            result = self._on_session_expired()
            if inspect.isawaitable(result):
                return bool(await result)
            return bool(result)
        except Exception:
            logger.exception("Session recovery callback failed")
            return False

    async def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by the stop event."""
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
