"""Tests for CLI argument handling."""

from __future__ import annotations

from wechat_bot import cli


def test_cli_webhook_defaults(monkeypatch):
    called: dict[str, object] = {}

    def _fake_run_webhook_server(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(cli, "run_webhook_server", _fake_run_webhook_server)

    rc = cli.main(["webhook"])
    assert rc == 0
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8787
    assert called["allow_get"] is True
    assert called["use_current_user"] is True


def test_cli_webhook_custom_options(monkeypatch):
    called: dict[str, object] = {}

    def _fake_run_webhook_server(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(cli, "run_webhook_server", _fake_run_webhook_server)

    rc = cli.main(
        [
            "webhook",
            "--host",
            "0.0.0.0",
            "--port",
            "9999",
            "--account-id",
            "acct_2",
            "--state-dir",
            "/tmp/state",
            "--api-key",
            "abc",
            "--disable-get",
            "--disable-current-user",
            "--log-level",
            "debug",
        ]
    )

    assert rc == 0
    assert called == {
        "host": "0.0.0.0",
        "port": 9999,
        "account_id": "acct_2",
        "state_dir": "/tmp/state",
        "api_key": "abc",
        "allow_get": False,
        "log_level": "debug",
        "use_current_user": False,
    }


def test_cli_webhook_returns_nonzero_on_error(monkeypatch):
    def _fake_run_webhook_server(**kwargs):
        del kwargs
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "run_webhook_server", _fake_run_webhook_server)

    rc = cli.main(["webhook"])
    assert rc == 1
