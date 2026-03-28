"""Tests for webhook app routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from wechat_bot.webhook import create_webhook_app


class _FakeBot:
    def __init__(self) -> None:
        self.account_id = "acct_default"
        self.owner_user_id = "owner_1"
        self.sent: list[tuple[str, str, str]] = []
        self.stopped = False

    def use_account(self, account_id: str) -> None:
        self.account_id = account_id

    def resolve_recipient(self, to: str | None = None) -> str:
        explicit = (to or "").strip()
        if explicit:
            return explicit
        if self.owner_user_id:
            return self.owner_user_id
        raise RuntimeError("No recipient available")

    async def send_text(self, to: str | None = None, text: str | None = None) -> None:
        assert text is not None
        resolved = self.resolve_recipient(to)
        self.sent.append((self.account_id, resolved, text))

    async def stop(self) -> None:
        self.stopped = True


def test_healthz_and_shutdown():
    bot = _FakeBot()
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": 200}

    assert bot.stopped is True


def test_send_get_success_with_account_switch():
    bot = _FakeBot()
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.get(
            "/send",
            params={
                "to": "u_target",
                "text": "hello",
                "account_id": "acct_2",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": 200}
    assert bot.sent == [("acct_2", "u_target", "hello")]


def test_send_post_success():
    bot = _FakeBot()
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.post(
            "/send",
            json={
                "to": "u_target",
                "text": "hello post",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": 200}
    assert bot.sent == [("acct_default", "u_target", "hello post")]


def test_send_post_owner_default_when_to_missing():
    bot = _FakeBot()
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.post(
            "/send",
            json={
                "text": "hello owner",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": 200}
    assert bot.sent == [("acct_default", "owner_1", "hello owner")]


def test_send_requires_api_key_when_configured():
    bot = _FakeBot()
    app = create_webhook_app(bot, api_key="secret")

    with TestClient(app) as client:
        bad = client.get(
            "/send",
            params={
                "to": "u_target",
                "text": "hello",
            },
        )
        assert bad.status_code == 401
        assert bad.json() == {"status": 401, "detail": "Invalid webhook key"}

        ok = client.get(
            "/send",
            params={
                "to": "u_target",
                "text": "hello",
                "key": "secret",
            },
        )
        assert ok.status_code == 200

        ok_header = client.post(
            "/send",
            json={"to": "u_target", "text": "hello2"},
            headers={"X-Webhook-Key": "secret"},
        )
        assert ok_header.status_code == 200


def test_get_route_can_be_disabled():
    bot = _FakeBot()
    app = create_webhook_app(bot, allow_get=False)

    with TestClient(app) as client:
        resp = client.get(
            "/send",
            params={
                "to": "u_target",
                "text": "hello",
            },
        )

    assert resp.status_code == 405
    assert resp.json() == {"status": 405, "detail": "Method Not Allowed"}


def test_send_returns_400_when_recipient_unavailable():
    bot = _FakeBot()
    bot.owner_user_id = ""
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.post(
            "/send",
            json={
                "text": "hello",
            },
        )

    assert resp.status_code == 400
    assert resp.json() == {"status": 400, "detail": "No recipient available"}


def test_send_returns_422_for_invalid_payload():
    bot = _FakeBot()
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.post("/send", json={})

    assert resp.status_code == 422
    assert resp.json() == {"status": 422, "detail": "Invalid request parameters"}


def test_send_returns_502_when_send_fails():
    bot = _FakeBot()

    async def _raise_send_text(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        raise RuntimeError("upstream unavailable")

    bot.send_text = _raise_send_text  # type: ignore[assignment]
    app = create_webhook_app(bot)

    with TestClient(app) as client:
        resp = client.post(
            "/send",
            json={
                "to": "u_target",
                "text": "hello",
            },
        )

    assert resp.status_code == 502
    assert resp.json() == {"status": 502, "detail": "Failed to send message"}
