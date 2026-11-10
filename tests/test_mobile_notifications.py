"""Mobile Telegram notifications must be explicit, private and testable."""
import asyncio

import httpx
from app.mobile_notifications import notification_status, send_pending_notice


def test_notification_requires_bot_and_chat(monkeypatch):
    monkeypatch.delenv("MOBILE_NOTIFY_BOT_TOKEN", raising=False)
    monkeypatch.delenv("MOBILE_NOTIFY_CHAT_ID", raising=False)
    assert notification_status()["ready"] is False
    assert notification_status()["chat_configured"] is False


def test_notification_sends_only_account_ids(monkeypatch):
    monkeypatch.setenv("MOBILE_NOTIFY_BOT_TOKEN", "example-token-for-test")
    monkeypatch.setenv("MOBILE_NOTIFY_CHAT_ID", "-1001234567890")
    sent = []
    class FakeResponse:
        status_code = 200
        def json(self):
            return {"ok": True}
    class FakeClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            sent.append((url, json))
            return FakeResponse()
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    assert notification_status()["ready"] is True
    assert asyncio.run(send_pending_notice([41])) is True
    assert len(sent) == 1
    assert sent[0][1]["chat_id"] == "-1001234567890"
    assert "#41" in sent[0][1]["text"]
    assert "email" not in sent[0][1]["text"].lower()
    assert all("callback_data" not in button for row in
               sent[0][1]["reply_markup"]["inline_keyboard"] for button in row)


def test_notification_failure_is_reported(monkeypatch):
    monkeypatch.setenv("MOBILE_NOTIFY_BOT_TOKEN", "example-token-for-test")
    monkeypatch.setenv("MOBILE_NOTIFY_CHAT_ID", "@medstudyadmin")
    class FakeResponse:
        status_code = 403
    class FakeClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, json):
            return FakeResponse()
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    assert asyncio.run(send_pending_notice([1])) is False
