"""Tests for Bot runtime helpers."""

import pytest

from wechat_bot.bot import Bot
from wechat_bot.errors import SessionExpiredError
from wechat_bot.models import LoginResult
from wechat_bot.storage import Storage


@pytest.mark.asyncio
async def test_run_raises_helpful_error_inside_running_loop():
    bot = Bot()

    with pytest.raises(RuntimeError, match=r"run_async"):
        bot.run()

    await bot.stop()


def test_bot_auto_loads_current_user(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_credentials(
        "acct_latest",
        "token_latest",
        base_url="https://latest.host",
        user_id="u_latest",
    )
    storage.save_current_user(
        "acct_latest",
        base_url="https://latest.host",
        user_id="u_latest",
    )

    bot = Bot(state_dir=str(tmp_path))
    assert bot._account_id == "acct_latest"
    assert bot._token == ""
    assert bot._base_url == "https://latest.host"
    bot._ensure_client()
    assert bot._token == "token_latest"


def test_bot_explicit_account_id_does_not_use_current_user(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_current_user(
        "acct_latest",
        "token_latest",
        base_url="https://latest.host",
    )

    bot = Bot(account_id="manual_acct", state_dir=str(tmp_path))
    assert bot._account_id == "manual_acct"
    assert bot._token == ""


@pytest.mark.asyncio
async def test_login_updates_current_user(monkeypatch, tmp_path):
    async def _fake_login_with_qr(*, base_url: str, **_: object) -> LoginResult:
        return LoginResult(
            token="tok_after_login",
            account_id="acct_after_login",
            base_url=base_url,
            user_id="u_after_login",
        )

    monkeypatch.setattr("wechat_bot.bot.login_with_qr", _fake_login_with_qr)

    bot = Bot(state_dir=str(tmp_path))
    result = await bot.login()

    assert result.account_id == "acct_after_login"

    storage = Storage(state_dir=str(tmp_path))
    current = storage.load_current_user()
    assert current["account_id"] == "acct_after_login"
    assert current["user_id"] == "u_after_login"

    await bot.stop()


@pytest.mark.asyncio
async def test_login_warns_on_duplicate_user_accounts(monkeypatch, tmp_path, caplog):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_credentials("acct_old", "tok_old", user_id="u_same")

    async def _fake_login_with_qr(*, base_url: str, **_: object) -> LoginResult:
        return LoginResult(
            token="tok_after_login",
            account_id="acct_new",
            base_url=base_url,
            user_id="u_same",
        )

    monkeypatch.setattr("wechat_bot.bot.login_with_qr", _fake_login_with_qr)
    bot = Bot(state_dir=str(tmp_path), use_current_user=False)

    with caplog.at_level("WARNING"):
        await bot.login()

    assert "bound to multiple local accounts" in caplog.text
    assert "acct_old" in caplog.text
    await bot.stop()


def test_use_account_switches_credentials(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_credentials("alpha", "token_a", base_url="https://a.host")
    storage.save_credentials("beta", "token_b", base_url="https://b.host", user_id="u_b")

    bot = Bot(state_dir=str(tmp_path), use_current_user=False)
    bot.use_account("beta")

    assert bot.account_id == "beta"
    assert bot._token == "token_b"
    assert bot._base_url == "https://b.host"
    assert bot._user_id == "u_b"
    assert bot.list_accounts() == ["alpha", "beta"]


def test_use_account_requires_existing_credentials(tmp_path):
    bot = Bot(state_dir=str(tmp_path), use_current_user=False)
    with pytest.raises(RuntimeError, match="No credentials found"):
        bot.use_account("missing")


@pytest.mark.asyncio
async def test_run_async_raises_when_poller_stops_due_to_session_expired(monkeypatch, tmp_path):
    class _ExpiredPoller:
        stopped_due_to_session_expired = True
        running = False

        async def wait_stopped(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    async def _fake_start(self: Bot) -> None:
        self._poller = _ExpiredPoller()  # type: ignore[assignment]

    monkeypatch.setattr(Bot, "start", _fake_start)
    bot = Bot(state_dir=str(tmp_path), use_current_user=False)

    with pytest.raises(SessionExpiredError, match="session expired"):
        await bot.run_async()


def test_resolve_recipient_prefers_explicit(tmp_path):
    bot = Bot(state_dir=str(tmp_path), user_id="owner_1", use_current_user=False)
    assert bot.resolve_recipient("u_target") == "u_target"


def test_resolve_recipient_uses_owner_user_id(tmp_path):
    bot = Bot(state_dir=str(tmp_path), user_id="owner_1", use_current_user=False)
    assert bot.resolve_recipient() == "owner_1"
    assert bot.owner_user_id == "owner_1"


def test_resolve_recipient_uses_credentials_user_id(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_credentials("acct_1", "tok", user_id="owner_from_creds")

    bot = Bot(state_dir=str(tmp_path), account_id="acct_1", use_current_user=False)
    assert bot.resolve_recipient() == "owner_from_creds"


def test_resolve_recipient_uses_current_user_when_account_matches(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_current_user("acct_1", user_id="owner_from_current")

    bot = Bot(state_dir=str(tmp_path), account_id="acct_1", use_current_user=False)
    assert bot.resolve_recipient() == "owner_from_current"


def test_resolve_recipient_ignores_current_user_when_account_mismatch(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_current_user("acct_latest", user_id="owner_latest")

    bot = Bot(state_dir=str(tmp_path), account_id="acct_1", use_current_user=False)
    with pytest.raises(RuntimeError, match="No recipient available"):
        bot.resolve_recipient()


def test_resolve_recipient_raises_when_owner_missing(tmp_path):
    bot = Bot(state_dir=str(tmp_path), use_current_user=False)
    with pytest.raises(RuntimeError, match="No recipient available"):
        bot.resolve_recipient()


@pytest.mark.asyncio
async def test_send_text_owner_default(monkeypatch, tmp_path):
    sent_to: list[str] = []
    sent_text: list[str] = []

    class _FakeClient:
        async def send_message(self, msg):  # type: ignore[no-untyped-def]
            sent_to.append(msg.to_user_id or "")
            text_item = msg.item_list[0].text_item if msg.item_list else None
            sent_text.append(text_item.text if text_item else "")

    bot = Bot(state_dir=str(tmp_path), user_id="owner_1", use_current_user=False)
    bot._token = "tok"
    bot._client = _FakeClient()  # type: ignore[assignment]

    await bot.send_text(text="hello")

    assert sent_to == ["owner_1"]
    assert sent_text == ["hello"]


def test_resolve_recipient_updates_after_use_account(tmp_path):
    storage = Storage(state_dir=str(tmp_path))
    storage.save_credentials("acct_1", "tok_1", user_id="owner_1")
    storage.save_credentials("acct_2", "tok_2", user_id="owner_2")

    bot = Bot(state_dir=str(tmp_path), account_id="acct_1", use_current_user=False)
    assert bot.resolve_recipient() == "owner_1"
    bot.use_account("acct_2")
    assert bot.resolve_recipient() == "owner_2"


@pytest.mark.asyncio
async def test_send_text_explicit_recipient_overrides_owner(tmp_path):
    sent_to: list[str] = []

    class _FakeClient:
        async def send_message(self, msg):  # type: ignore[no-untyped-def]
            sent_to.append(msg.to_user_id or "")

    bot = Bot(state_dir=str(tmp_path), user_id="owner_1", use_current_user=False)
    bot._token = "tok"
    bot._client = _FakeClient()  # type: ignore[assignment]

    await bot.send_text(to="u_target", text="hello")
    assert sent_to == ["u_target"]


@pytest.mark.asyncio
async def test_send_text_requires_text_argument(tmp_path):
    bot = Bot(state_dir=str(tmp_path), user_id="owner_1", use_current_user=False)
    with pytest.raises(TypeError, match="missing required argument: 'text'"):
        await bot.send_text(to="u_target")
