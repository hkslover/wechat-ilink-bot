"""Smoke tests for examples imports and async main helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from wechat_bot.models import LoginResult

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load_example_module(module_name: str, file_name: str):
    path = EXAMPLES_DIR / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_examples_import_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr("wechat_bot.storage._DEFAULT_STATE_DIR", str(tmp_path / ".wechat_bot"))

    modules = [
        _load_example_module("ex_echo", "echo_bot.py"),
        _load_example_module("ex_login", "login_bot.py"),
        _load_example_module("ex_command", "command_bot.py"),
        _load_example_module("ex_media", "media_bot.py"),
        _load_example_module("ex_proactive", "proactive_send.py"),
        _load_example_module("ex_switch", "account_switch.py"),
    ]

    assert all(modules)


@pytest.mark.asyncio
async def test_login_example_main_smoke(monkeypatch):
    module = _load_example_module("ex_login_main", "login_bot.py")

    async def _fake_login(self):
        return LoginResult(
            token="tok",
            account_id="acct",
            base_url="https://api.example",
            user_id="user_1",
        )

    async def _fake_stop(self):
        return None

    monkeypatch.setattr(module.Bot, "login", _fake_login)
    monkeypatch.setattr(module.Bot, "stop", _fake_stop)

    await module.main()


@pytest.mark.asyncio
async def test_proactive_example_main_smoke(monkeypatch):
    module = _load_example_module("ex_proactive_main", "proactive_send.py")

    sent: list[tuple[str, str]] = []

    async def _fake_send_text(self, to: str, text: str) -> None:
        sent.append((to, text))

    async def _fake_stop(self):
        return None

    monkeypatch.setenv("WECHAT_TARGET_USER", "u_target")
    monkeypatch.delenv("WECHAT_IMAGE_PATH", raising=False)
    monkeypatch.delenv("WECHAT_FILE_PATH", raising=False)
    monkeypatch.delenv("WECHAT_VIDEO_PATH", raising=False)
    monkeypatch.setattr(module.Bot, "send_text", _fake_send_text)
    monkeypatch.setattr(module.Bot, "stop", _fake_stop)

    await module.main()

    assert sent == [("u_target", "Hello from wechat-ilink-bot!")]


@pytest.mark.asyncio
async def test_proactive_example_main_owner_default(monkeypatch):
    module = _load_example_module("ex_proactive_owner_default", "proactive_send.py")

    calls: list[tuple[str | None, str | None]] = []

    async def _fake_send_text(
        self, to: str | None = None, text: str | None = None
    ) -> None:
        calls.append((to, text))

    async def _fake_stop(self):
        return None

    monkeypatch.delenv("WECHAT_TARGET_USER", raising=False)
    monkeypatch.delenv("WECHAT_IMAGE_PATH", raising=False)
    monkeypatch.delenv("WECHAT_FILE_PATH", raising=False)
    monkeypatch.delenv("WECHAT_VIDEO_PATH", raising=False)
    monkeypatch.setattr(module.Bot, "send_text", _fake_send_text)
    monkeypatch.setattr(module.Bot, "stop", _fake_stop)

    await module.main()

    assert calls == [(None, "Hello from wechat-ilink-bot!")]


@pytest.mark.asyncio
async def test_account_switch_example_main_smoke(monkeypatch):
    module = _load_example_module("ex_switch_main", "account_switch.py")

    events: list[str] = []

    def _fake_list_accounts(self):
        return ["acct_1"]

    def _fake_use_account(self, account_id: str):
        events.append(f"use:{account_id}")

    async def _fake_send_text(self, to: str, text: str):
        events.append(f"send:{to}:{text}")

    async def _fake_stop(self):
        return None

    monkeypatch.setenv("WECHAT_ACCOUNT_ID", "acct_1")
    monkeypatch.setenv("WECHAT_TARGET_USER", "u_target")
    monkeypatch.setattr(module.Bot, "list_accounts", _fake_list_accounts)
    monkeypatch.setattr(module.Bot, "use_account", _fake_use_account)
    monkeypatch.setattr(module.Bot, "send_text", _fake_send_text)
    monkeypatch.setattr(module.Bot, "stop", _fake_stop)

    await module.main()

    assert events[0] == "use:acct_1"
    assert events[1].startswith("send:u_target:hello from account acct_1")


@pytest.mark.asyncio
async def test_account_switch_example_main_owner_default(monkeypatch):
    module = _load_example_module("ex_switch_owner_default", "account_switch.py")

    calls: list[tuple[str | None, str | None]] = []

    def _fake_list_accounts(self):
        return ["acct_1"]

    def _fake_use_account(self, account_id: str):
        assert account_id == "acct_1"

    async def _fake_send_text(
        self, to: str | None = None, text: str | None = None
    ) -> None:
        calls.append((to, text))

    async def _fake_stop(self):
        return None

    monkeypatch.setenv("WECHAT_ACCOUNT_ID", "acct_1")
    monkeypatch.delenv("WECHAT_TARGET_USER", raising=False)
    monkeypatch.setattr(module.Bot, "list_accounts", _fake_list_accounts)
    monkeypatch.setattr(module.Bot, "use_account", _fake_use_account)
    monkeypatch.setattr(module.Bot, "send_text", _fake_send_text)
    monkeypatch.setattr(module.Bot, "stop", _fake_stop)

    await module.main()

    assert calls == [(None, "hello from account acct_1")]
