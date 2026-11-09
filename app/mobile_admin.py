"""Staging-only administrator review interface with an explicit server-side secret."""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import mobile_auth

router = APIRouter()


def verify_admin_key(key: str | None):
    if os.getenv("MOBILE_ADMIN_PANEL_ENABLED", "0") != "1":
        raise HTTPException(404, "Not found")
    expected = os.getenv("MOBILE_ADMIN_KEY", "")
    if len(expected) < 32:
        raise HTTPException(503, "Administrator key is not configured")
    if not key or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(403, "Administrator authorization failed")


@router.get("/mobile-register", include_in_schema=False)
def public_registration_page():
    """Public form can only create a pending application, never grant access."""
    from pathlib import Path
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "mobile-register.html",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


@router.get("/mobile-admin", include_in_schema=False)
def admin_page():
    if os.getenv("MOBILE_ADMIN_PANEL_ENABLED", "0") != "1":
        raise HTTPException(404, "Not found")
    from pathlib import Path
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "mobile-admin.html",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                 "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'"},
    )


@router.get("/api/mobile/admin-console/pending")
def admin_pending(x_mobile_admin_key: str | None = Header(default=None)):
    verify_admin_key(x_mobile_admin_key)
    return {"items": mobile_auth.pending_accounts()}


class ReviewBody(BaseModel):
    account_id: int = Field(gt=0)
    decision: str = Field(pattern="^(approved|rejected|revoked)$")


@router.post("/api/mobile/admin-console/review")
def admin_review(body: ReviewBody, x_mobile_admin_key: str | None = Header(default=None)):
    verify_admin_key(x_mobile_admin_key)
    result = mobile_auth.set_account_status(body.account_id, body.decision)
    return result


@router.get("/api/mobile/admin-console/telegram-status")
def telegram_status(x_mobile_admin_key: str | None = Header(default=None)):
    """Authenticated diagnostics; never return secrets or chat identifiers."""
    verify_admin_key(x_mobile_admin_key)
    from .mobile_notifications import notification_status
    return {**notification_status(), "pending_count": len(mobile_auth.pending_accounts())}


@router.post("/api/mobile/admin-console/resend-pending")
async def resend_pending(x_mobile_admin_key: str | None = Header(default=None)):
    """Allow admin to notify about applications submitted before bot configuration."""
    verify_admin_key(x_mobile_admin_key)
    from .mobile_notifications import notification_status, send_pending_notice
    if not notification_status()["ready"]:
        raise HTTPException(409, "Telegram bot yoki kanal ID sozlanmagan")
    pending = mobile_auth.pending_accounts()
    if not pending:
        return {"sent": False, "pending_count": 0}
    success = await send_pending_notice([item["id"] for item in pending])
    if not success:
        raise HTTPException(502, "Telegram xabarni qabul qilmadi. Botni kanalga administrator qiling.")
    return {"sent": True, "pending_count": len(pending)}
