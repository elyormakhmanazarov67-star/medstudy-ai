"""Staging-only mobile administrator console with secure browser sessions."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import mobile_auth

router = APIRouter()
SESSION_COOKIE = "medstudy_mobile_admin_session"
SESSION_AGE = 30 * 24 * 60 * 60
COOKIE_PATH = "/api/mobile/admin-console"


def _admin_secret() -> str:
    if os.getenv("MOBILE_ADMIN_PANEL_ENABLED", "0") != "1":
        raise HTTPException(404, "Not found")
    expected = os.getenv("MOBILE_ADMIN_KEY", "")
    if len(expected) < 32:
        raise HTTPException(503, "Administrator key is not configured")
    return expected


def _cookie_signature(value: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        ("medstudy-admin-session-v1|" + value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _issue_session(secret: str) -> str:
    expires = int(time.time()) + SESSION_AGE
    nonce = secrets.token_urlsafe(24)
    payload = "v1." + str(expires) + "." + nonce
    return payload + "." + _cookie_signature(payload, secret)


def _valid_session(cookie: str | None, secret: str) -> bool:
    if not cookie or len(cookie) > 256:
        return False
    try:
        version, expiry, nonce, signature = cookie.split(".")
        expires = int(expiry)
    except (ValueError, TypeError):
        return False
    if version != "v1" or not nonce or not (32 <= len(nonce) <= 64):
        return False
    if not (int(time.time()) < expires <= int(time.time()) + SESSION_AGE):
        return False
    expected = _cookie_signature("v1." + expiry + "." + nonce, secret)
    return hmac.compare_digest(signature, expected)


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    # Browser sends Origin on cross-site/scripted POST requests.
    return bool(host and origin == "https://" + host)


def verify_admin_key(
    key: str | None = None,
    request: Request | None = None,
    *,
    mutation: bool = False,
):
    secret = _admin_secret()
    # Legacy API clients may continue to use the header directly.
    if key is not None and hmac.compare_digest(key.encode(), secret.encode()):
        return
    if request is not None and _valid_session(request.cookies.get(SESSION_COOKIE), secret):
        if mutation and not _same_origin(request):
            raise HTTPException(403, "Origin verification failed")
        return
    raise HTTPException(403, "Administrator authorization failed")


class SessionLogin(BaseModel):
    remember: bool = True


@router.post("/api/mobile/admin-console/session")
def create_admin_session(
    body: SessionLogin,
    x_mobile_admin_key: str | None = Header(default=None),
):
    secret = _admin_secret()
    if not x_mobile_admin_key or not hmac.compare_digest(
        x_mobile_admin_key.encode("utf-8"), secret.encode("utf-8")
    ):
        raise HTTPException(403, "Administrator authorization failed")
    response = JSONResponse({"authenticated": True}, headers={"Cache-Control": "no-store"})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=_issue_session(secret),
        max_age=SESSION_AGE if body.remember else None,
        path=COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return response


@router.get("/api/mobile/admin-console/session")
def check_admin_session(request: Request):
    # Session check must not allow accidental header authentication.
    verify_admin_key(request=request)
    return JSONResponse({"authenticated": True}, headers={"Cache-Control": "no-store"})


@router.post("/api/mobile/admin-console/logout")
def admin_logout(request: Request):
    verify_admin_key(request=request, mutation=True)
    response = JSONResponse({"logged_out": True}, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        SESSION_COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite="strict"
    )
    return response


@router.get("/mobile-register", include_in_schema=False)
def public_registration_page():
    """Public form can only create a pending application, never grant access."""
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
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "mobile-admin.html",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


@router.get("/api/mobile/admin-console/pending")
def admin_pending(request: Request, x_mobile_admin_key: str | None = Header(default=None)):
    verify_admin_key(x_mobile_admin_key, request)
    return {"items": mobile_auth.pending_accounts()}


class ReviewBody(BaseModel):
    account_id: int = Field(gt=0)
    decision: str = Field(pattern="^(approved|rejected|revoked)$")


@router.post("/api/mobile/admin-console/review")
def admin_review(
    body: ReviewBody, request: Request, x_mobile_admin_key: str | None = Header(default=None)
):
    verify_admin_key(x_mobile_admin_key, request, mutation=True)
    return mobile_auth.set_account_status(body.account_id, body.decision)


@router.get("/api/mobile/admin-console/telegram-status")
def telegram_status(request: Request, x_mobile_admin_key: str | None = Header(default=None)):
    """Authenticated diagnostics; never return secrets or chat identifiers."""
    verify_admin_key(x_mobile_admin_key, request)
    from .mobile_notifications import notification_status
    return {**notification_status(), "pending_count": len(mobile_auth.pending_accounts())}


@router.post("/api/mobile/admin-console/resend-pending")
async def resend_pending(
    request: Request, x_mobile_admin_key: str | None = Header(default=None)
):
    """Allow admin to notify about applications submitted before bot configuration."""
    verify_admin_key(x_mobile_admin_key, request, mutation=True)
    from .mobile_notifications import notification_status, send_pending_notice
    if not notification_status()["ready"]:
        raise HTTPException(409, "Telegram bot yoki chat ID sozlanmagan")
    pending = mobile_auth.pending_accounts()
    if not pending:
        return {"sent": False, "pending_count": 0}
    success = await send_pending_notice([item["id"] for item in pending])
    if not success:
        raise HTTPException(
            502,
            "Telegram xabarni qabul qilmadi. Xabar yuboruvchi botga shaxsiy akkauntingizdan /start yuboring.",
        )
    return {"sent": True, "pending_count": len(pending)}
