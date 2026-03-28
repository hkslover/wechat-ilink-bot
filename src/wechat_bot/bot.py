"""Bot — the primary user-facing class for building a WeChat bot."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import uuid
from collections.abc import Callable
from typing import Any

from ._logging import logger
from .auth import login_with_qr
from .client import WeChatClient
from .context import MessageContext
from .errors import SessionExpiredError
from .handlers import Filter, HandlerCallback, MessageHandler
from .models import (
    LoginResult,
    MessageItem,
    TextItem,
    WeixinMessage,
)
from .polling import Poller
from .storage import Storage
from .types import (
    DEFAULT_BASE_URL,
    DEFAULT_CDN_BASE_URL,
    SESSION_EXPIRED_ERRCODE,
    MessageItemType,
    MessageState,
    MessageType,
    UploadMediaType,
)

__all__ = ["Bot"]


def _generate_client_id() -> str:
    return f"wechat-bot-{uuid.uuid4().hex[:12]}"


class Bot:
    """High-level bot interface.

    Usage::

        bot = Bot(token="your_token")

        @bot.on_message(Filter.text())
        async def echo(ctx):
            await ctx.reply(ctx.text)

        bot.run()

    Args:
        token: Bot token from QR login. If ``None`` you must call
            :meth:`login` before :meth:`run`.
        base_url: iLink API base URL.
        cdn_base_url: CDN base URL for media operations.
        account_id: Bot account ID. Auto-detected from storage if omitted.
        state_dir: Directory for persistent state files.
        user_id: Current bot user ID (usually auto-populated by login state).
        use_current_user: If ``True`` and no explicit token/account is given,
            auto-load the latest account from ``current_user.json``.
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        cdn_base_url: str = DEFAULT_CDN_BASE_URL,
        account_id: str | None = None,
        state_dir: str | None = None,
        user_id: str | None = None,
        use_current_user: bool = True,
    ) -> None:
        self._token = token or ""
        self._base_url = base_url
        self._cdn_base_url = cdn_base_url
        self._storage = Storage(state_dir)
        self._account_id = account_id or "default"
        self._handlers: list[MessageHandler] = []
        self._client: WeChatClient | None = None
        self._poller: Poller | None = None
        self._user_id = user_id or ""

        # Auto-load latest logged-in account when user creates Bot() without
        # explicit token/account_id.
        if use_current_user and not self._token and account_id is None:
            current = self._storage.load_current_user()
            if current.get("account_id"):
                self._account_id = current["account_id"]
            if current.get("base_url"):
                self._base_url = current["base_url"]
            if current.get("user_id"):
                self._user_id = current["user_id"]

        if self._token:
            self._client = self._make_client()

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    def _make_client(self) -> WeChatClient:
        return WeChatClient(
            base_url=self._base_url,
            token=self._token,
            cdn_base_url=self._cdn_base_url,
        )

    def _ensure_client(self) -> WeChatClient:
        if self._client is None:
            if not self._token:
                creds = self._storage.load_credentials(self._account_id)
                self._token = creds.get("token", "")
                if creds.get("base_url"):
                    self._base_url = creds["base_url"]
                if creds.get("user_id"):
                    self._user_id = creds["user_id"]
            if not self._token:
                raise RuntimeError(
                    "No token available. Call bot.login() or pass token= to Bot()."
                )
            self._client = self._make_client()
        return self._client

    @property
    def account_id(self) -> str:
        """Current active bot account ID."""
        return self._account_id

    @property
    def owner_user_id(self) -> str | None:
        """Owner user ID inferred from login/session state, if available."""
        return self._load_owner_user_id()

    def list_accounts(self) -> list[str]:
        """List local account IDs that have stored credentials."""
        return self._storage.list_account_ids()

    def use_account(self, account_id: str) -> None:
        """Switch to a locally stored account.

        Raises:
            RuntimeError: If the account has no stored credentials or
                polling is currently running.
        """
        if self._poller and self._poller.running:
            raise RuntimeError(
                "Cannot switch account while polling is running. Call bot.stop() first."
            )

        creds = self._storage.load_credentials(account_id)
        token = creds.get("token", "")
        if not token:
            raise RuntimeError(
                f"No credentials found for account '{account_id}'. Run bot.login() first."
            )

        self._account_id = account_id
        self._token = token
        if creds.get("base_url"):
            self._base_url = creds["base_url"]
        if creds.get("user_id"):
            self._user_id = creds["user_id"]
        self._client = self._make_client()

    def _load_owner_user_id(self) -> str | None:
        current = self._user_id.strip()
        if current:
            return current

        creds = self._storage.load_credentials(self._account_id)
        cred_user = creds.get("user_id", "").strip()
        if cred_user:
            self._user_id = cred_user
            return cred_user

        latest = self._storage.load_current_user()
        latest_account = latest.get("account_id", "").strip()
        latest_user = latest.get("user_id", "").strip()
        if latest_user and latest_account == self._account_id:
            self._user_id = latest_user
            return latest_user
        return None

    def resolve_recipient(self, to: str | None = None) -> str:
        """Resolve final recipient user ID.

        Resolution order:
        1. Explicit ``to`` (if provided)
        2. Owner user ID inferred from persisted login state
        """
        explicit = (to or "").strip()
        if explicit:
            return explicit

        owner = self._load_owner_user_id()
        if owner:
            return owner

        raise RuntimeError(
            "No recipient available. Pass `to=...` explicitly, or re-login via bot.login() "
            "to persist owner user_id."
        )

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def on_message(
        self,
        filters: Filter | None = None,
        priority: int = 0,
    ) -> Callable[[HandlerCallback], HandlerCallback]:
        """Decorator to register a message handler.

        Args:
            filters: Optional :class:`Filter` to restrict which messages
                trigger this handler.
            priority: Lower values run first. Default ``0``.

        Notes:
            Only the first matching handler (by ascending priority) is invoked
            for each inbound message.
        """

        def decorator(func: HandlerCallback) -> HandlerCallback:
            handler = MessageHandler(func, filters=filters, priority=priority)
            self.add_handler(handler)
            return func

        return decorator

    def add_handler(self, handler: MessageHandler) -> None:
        """Register a :class:`MessageHandler` manually.

        Handlers are sorted by priority and dispatch stops at first match.
        """
        self._handlers.append(handler)
        self._handlers.sort(key=lambda h: h.priority)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, **kwargs: Any) -> LoginResult:
        """Perform QR code login.

        All keyword arguments are forwarded to :func:`login_with_qr`.
        After a successful login the token and account ID are persisted
        so subsequent ``Bot()`` instances can auto-load them.
        """
        result = await login_with_qr(base_url=self._base_url, **kwargs)
        self._token = result.token
        self._account_id = result.account_id
        if result.base_url:
            self._base_url = result.base_url
        self._client = self._make_client()

        self._storage.save_credentials(
            result.account_id,
            result.token,
            base_url=result.base_url,
            user_id=result.user_id,
        )
        self._storage.save_current_user(
            result.account_id,
            base_url=result.base_url,
            user_id=result.user_id,
        )
        stale_accounts = [
            account_id
            for account_id in self._storage.list_account_ids_by_user_id(result.user_id)
            if account_id != result.account_id
        ]
        if stale_accounts:
            logger.warning(
                "User %s is bound to multiple local accounts: %s. "
                "Latest login account '%s' is now current.",
                result.user_id,
                ", ".join(stale_accounts),
                result.account_id,
            )
        return result

    # ------------------------------------------------------------------
    # Proactive sending
    # ------------------------------------------------------------------

    async def send_text(
        self,
        to: str | None = None,
        text: str | None = None,
    ) -> None:
        """Send a text message.

        Args:
            to: Optional target user ID. If omitted, owner user ID is used.
            text: Message text.
        """
        if text is None:
            raise TypeError(
                "send_text() missing required argument: 'text'. "
                "Use send_text(text='...') for owner-default mode."
            )

        recipient = self.resolve_recipient(to)
        client = self._ensure_client()
        ctx_token = self._storage.get_context_token(self._account_id, recipient)
        msg = WeixinMessage(
            from_user_id="",
            to_user_id=recipient,
            client_id=_generate_client_id(),
            message_type=MessageType.BOT,
            message_state=MessageState.FINISH,
            item_list=[MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text))],
            context_token=ctx_token,
        )
        await client.send_message(msg)

    async def send_image(
        self,
        to: str | None = None,
        file_path: str | None = None,
        caption: str = "",
    ) -> None:
        """Upload and send an image."""
        if not file_path:
            raise TypeError("send_image() missing required argument: 'file_path'")
        await self._send_media(
            self.resolve_recipient(to),
            file_path,
            caption,
            UploadMediaType.IMAGE,
        )

    async def send_video(
        self,
        to: str | None = None,
        file_path: str | None = None,
        caption: str = "",
    ) -> None:
        """Upload and send a video."""
        if not file_path:
            raise TypeError("send_video() missing required argument: 'file_path'")
        await self._send_media(
            self.resolve_recipient(to),
            file_path,
            caption,
            UploadMediaType.VIDEO,
        )

    async def send_file(
        self,
        to: str | None = None,
        file_path: str | None = None,
        caption: str = "",
    ) -> None:
        """Upload and send a file attachment."""
        if not file_path:
            raise TypeError("send_file() missing required argument: 'file_path'")
        await self._send_media(
            self.resolve_recipient(to),
            file_path,
            caption,
            UploadMediaType.FILE,
        )

    async def _send_media(
        self,
        to: str,
        file_path: str,
        caption: str,
        media_type: UploadMediaType,
    ) -> None:
        from .context import _build_media_item
        from .media.upload import upload_media

        client = self._ensure_client()
        uploaded = await upload_media(
            client,
            file_path=file_path,
            to_user_id=to,
            media_type=media_type,
            cdn_base_url=self._cdn_base_url,
        )
        ctx_token = self._storage.get_context_token(self._account_id, to)

        items: list[MessageItem] = []
        if caption:
            items.append(
                MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=caption))
            )
        items.append(_build_media_item(uploaded, media_type, file_path))

        for item in items:
            msg = WeixinMessage(
                from_user_id="",
                to_user_id=to,
                client_id=_generate_client_id(),
                message_type=MessageType.BOT,
                message_state=MessageState.FINISH,
                item_list=[item],
                context_token=ctx_token,
            )
            await client.send_message(msg)

    # ------------------------------------------------------------------
    # Polling / run
    # ------------------------------------------------------------------

    async def _dispatch(self, msg: WeixinMessage) -> None:
        """Route an inbound message to registered handlers."""
        from_user = msg.from_user_id or ""

        if msg.context_token:
            self._storage.set_context_token(self._account_id, from_user, msg.context_token)

        client = self._ensure_client()
        ctx = MessageContext(
            msg,
            client=client,
            storage=self._storage,
            account_id=self._account_id,
            cdn_base_url=self._cdn_base_url,
        )

        for handler in self._handlers:
            if handler.check(msg):
                try:
                    await handler.callback(ctx)
                except Exception:
                    logger.exception(
                        "Handler %s raised an exception", handler.callback.__name__
                    )
                return

        logger.debug("No handler matched message from %s", from_user)

    async def start(self) -> None:
        """Start the long-poll loop in the background.

        Use :meth:`stop` to shut it down gracefully.
        """
        client = self._ensure_client()
        self._storage.restore_context_tokens(self._account_id)

        self._poller = Poller(
            client=client,
            storage=self._storage,
            account_id=self._account_id,
            on_message=self._dispatch,
            on_session_expired=self._handle_session_expired,
        )
        await self._poller.start()

    async def stop(self) -> None:
        """Stop the polling loop and close the HTTP client."""
        if self._poller:
            await self._poller.stop()
            self._poller = None
        if self._client:
            await self._client.close()
            self._client = None

    async def run_async(self) -> None:
        """Async convenience method: start polling and run until interrupted.

        Handles ``SIGINT`` / ``SIGTERM`` for graceful shutdown.
        Use this in existing asyncio applications.
        """
        await self.start()
        stop_event = asyncio.Event()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError, RuntimeError):
                loop.add_signal_handler(sig, stop_event.set)

        logger.info("Bot running - press Ctrl+C to stop")
        wait_tasks: list[asyncio.Task[object]] = [asyncio.create_task(stop_event.wait())]
        poller_wait_task: asyncio.Task[object] | None = None
        if self._poller:
            poller_wait_task = asyncio.create_task(self._poller.wait_stopped())
            wait_tasks.append(poller_wait_task)

        try:
            done, pending = await asyncio.wait(
                wait_tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in pending:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            if (
                poller_wait_task is not None
                and poller_wait_task in done
                and self._poller
                and self._poller.stopped_due_to_session_expired
            ):
                raise SessionExpiredError(
                    "Polling stopped because session expired (errcode=-14). "
                    "Please run bot.login() and restart the bot.",
                    errcode=SESSION_EXPIRED_ERRCODE,
                )
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Shutting down...")
            await self.stop()

    async def _handle_session_expired(self) -> bool:
        """Try to recover by reloading stored credentials for the current account."""
        creds = self._storage.load_credentials(self._account_id)
        new_token = creds.get("token", "")
        if not new_token or new_token == self._token:
            return False

        self._token = new_token
        if creds.get("base_url"):
            self._base_url = creds["base_url"]
        if creds.get("user_id"):
            self._user_id = creds["user_id"]

        client = self._ensure_client()
        client.token = self._token
        client.base_url = self._base_url.rstrip("/") + "/"
        logger.info("Loaded refreshed token from storage for account %s", self._account_id)
        return True

    def run(self) -> None:
        """Blocking convenience method: start polling and run until interrupted.

        Handles ``SIGINT`` / ``SIGTERM`` for graceful shutdown.
        """
        has_running_loop = True
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            has_running_loop = False

        if has_running_loop:
            raise RuntimeError(
                "Bot.run() cannot be called from a running event loop. "
                "Use `await bot.run_async()` in async code."
            )

        asyncio.run(self.run_async())
