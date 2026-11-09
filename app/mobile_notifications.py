"""Send mobile approval alerts without changing the production Telegram webhook.

Notifications include only anonymous application IDs, never email/password.
A channel or private chat is configured through dedicated environment variables.
"""
from __future__ import annotations
import logging
import os
import re
import httpx

logger = logging.getLogger(__name__)
ADMIN_PANEL_URL = "https://medstudy-ai-mobile-staging-staging.up.railway.app/mobile-admin"


def notification_status() -> dict:
    token = os.getenv("MOBILE_NOTIFY_BOT_TOKEN", "").strip()
    chat = os.getenv("MOBILE_NOTIFY_CHAT_ID", "").strip()
    # Telegram group/channel IDs (-100...) or public @channel names.
    chat_valid = bool(re.fullmatch(r"-?[0-9]{4,24}|@[A-Za-z][A-Za-z0-9_]{4,31}", chat))
    return {
        "bot_configured": bool(token),
        "chat_configured": chat_valid,
        "ready": bool(token) and chat_valid,
    }


async def send_pending_notice(account_ids: list[int]) -> bool:
    """True only when Telegram explicitly accepts the message."""
    state = notification_status()
    if not state["ready"]:
        logger.warning(
            "Mobile Telegram alerts disabled: bot_configured=%s chat_configured=%s",
            state["bot_configured"], state["chat_configured"],
        )
        return False
    ids = [str(x) for x in account_ids if isinstance(x, int) and x > 0][:30]
    if not ids:
        return False
    token = os.getenv("MOBILE_NOTIFY_BOT_TOKEN", "").strip()
    chat = os.getenv("MOBILE_NOTIFY_CHAT_ID", "").strip()
    label = ", ".join("#" + i for i in ids)
    payload = {
        "chat_id": chat,
        "text": "📩 MedStudy AI 2.0: mobil ilovaga ruxsat so‘rovi "
                + label + "\nTasdiqlash / Rad etish uchun admin sahifasiga kiring.",
        "reply_markup": {"inline_keyboard": [[
            {"text": "🔐 Arizalarni ko‘rish", "url": ADMIN_PANEL_URL}
        ]]},
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                "https://api.telegram.org/bot" + token + "/sendMessage", json=payload
            )
            # Never log the URL, bot token, Telegram response body or user data.
            if response.status_code != 200:
                logger.warning("Mobile Telegram alert rejected, HTTP %s", response.status_code)
                return False
            if not response.json().get("ok"):
                logger.warning("Mobile Telegram alert rejected by Telegram")
                return False
            return True
    except (httpx.HTTPError, ValueError):
        logger.warning("Mobile Telegram alert failed: network or invalid response")
        return False
