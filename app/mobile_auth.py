"""Isolated mobile account pilot; does not alter Telegram authorization."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mobile", tags=["mobile"])
EMAIL_RE = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,24}$")
SESSION_SECONDS = 60 * 60 * 24 * 14
# Isolate mobile credentials from legacy Telegram user IDs and progress rows.
DB_PATH = os.getenv("MOBILE_AUTH_DB_PATH", os.getenv("DATABASE_PATH", "data/medstudy.db"))
_DB_READY = False


def connect():
    path = Path(DB_PATH).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=15)
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    global _DB_READY
    if _DB_READY:
        return
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS mobile_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mobile_sessions (
            token_hash TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES mobile_accounts(id) ON DELETE CASCADE,
            expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mobile_sessions_user ON mobile_sessions(account_id);
        CREATE TABLE IF NOT EXISTS mobile_auth_limits (
            key_hash TEXT NOT NULL,
            window INTEGER NOT NULL,
            attempts INTEGER NOT NULL,
            PRIMARY KEY(key_hash, window)
        );
        """)
    _DB_READY = True


def digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password, salt):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)


def now_text():
    return datetime.now(timezone.utc).isoformat()


def rate_limit(db, key, max_attempts=8):
    # A database-backed cap shared by all server workers; no raw IP/email logged.
    window = int(time.time()) // 900
    key_hash = digest(key)
    db.execute("DELETE FROM mobile_auth_limits WHERE window < ?", (window - 1,))
    db.execute("INSERT INTO mobile_auth_limits VALUES (?, ?, 1) ON CONFLICT(key_hash,window) DO UPDATE SET attempts=attempts+1", (key_hash, window))
    used = db.execute("SELECT attempts FROM mobile_auth_limits WHERE key_hash=? AND window=?", (key_hash, window)).fetchone()[0]
    db.commit()  # Persist limits even if caller later rejects credentials.
    if used > max_attempts:
        raise HTTPException(429, "Juda ko'p urinish. Keyinroq qayta urinib ko'ring.")


class Register(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    display_name: str = Field(min_length=2, max_length=70)
    password: str = Field(min_length=12, max_length=128)


class Login(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(email):
    value = email.strip().lower()
    if not EMAIL_RE.fullmatch(value):
        raise HTTPException(422, "Email formati noto'g'ri")
    return value


@router.post("/register", status_code=202)
def register(body: Register, request: Request):
    init_db()
    email = normalize_email(body.email)
    name = body.display_name.strip()
    if len(name) < 2 or len(body.password.encode("utf-8")) > 256:
        raise HTTPException(422, "Ism yoki parol noto'g'ri")
    with connect() as db:
        rate_limit(db, "reg:" + (request.client.host if request.client else "unknown"), 5)
        exists = db.execute("SELECT id FROM mobile_accounts WHERE email=?", (email,)).fetchone()
        if not exists:
            salt = secrets.token_bytes(16)
            db.execute("INSERT INTO mobile_accounts(email,display_name,salt,password_hash,created_at) VALUES (?,?,?,?,?)",
                       (email, name, salt, hash_password(body.password, salt), now_text()))
    # Do not reveal whether email is registered.
    return {"message": "Ariza qabul qilindi. Administrator tasdig'ini kuting."}


@router.post("/login")
def login(body: Login, request: Request):
    init_db()
    email = normalize_email(body.email)
    with connect() as db:
        ip = request.client.host if request.client else "unknown"
        rate_limit(db, "login-ip:" + ip, 30)
        rate_limit(db, "login-account:" + email, 8)
        row = db.execute("SELECT id,salt,password_hash,approved FROM mobile_accounts WHERE email=?", (email,)).fetchone()
        # Equalize password check for non-existent users.
        fake_salt = b"medstudy-pilot00"
        computed = hash_password(body.password, row[1] if row else fake_salt)
        if not row or not hmac.compare_digest(computed, row[2]):
            raise HTTPException(401, "Email yoki parol noto'g'ri")
        if not row[3]:
            raise HTTPException(403, "Administrator tasdig'i kutilmoqda")
        token = secrets.token_urlsafe(32)
        expiry = int(time.time()) + SESSION_SECONDS
        db.execute("DELETE FROM mobile_sessions WHERE expires_at < ?", (int(time.time()),))
        db.execute("INSERT INTO mobile_sessions VALUES (?,?,?)", (digest(token), row[0], expiry))
    return {"access_token": token, "token_type": "bearer", "expires_in": SESSION_SECONDS}


def current_account(authorization: str | None):
    init_db()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Kirish talab qilinadi")
    token = authorization[7:]
    if not 30 <= len(token) <= 100:
        raise HTTPException(401, "Sessiya yaroqsiz")
    with connect() as db:
        row = db.execute("""SELECT a.id,a.email,a.display_name,a.approved FROM mobile_sessions s
            JOIN mobile_accounts a ON a.id=s.account_id
            WHERE s.token_hash=? AND s.expires_at>?""", (digest(token), int(time.time()))).fetchone()
    if not row or not row[3]:
        raise HTTPException(401, "Sessiya tugagan yoki ruxsat bekor qilingan")
    return {"id": row[0], "email": row[1], "display_name": row[2]}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    return current_account(authorization)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    current_account(authorization)
    with connect() as db:
        db.execute("DELETE FROM mobile_sessions WHERE token_hash=?", (digest(authorization[7:]),))
    return {"logged_out": True}


def pending_accounts(limit=30):
    init_db()
    with connect() as db:
        return [{"id": row[0], "email": row[1], "display_name": row[2]} for row in
                db.execute("SELECT id,email,display_name FROM mobile_accounts WHERE approved=0 ORDER BY id LIMIT ?", (limit,))]


def approve_account(account_id, approved):
    init_db()
    with connect() as db:
        count = db.execute("UPDATE mobile_accounts SET approved=? WHERE id=?", (int(approved), account_id)).rowcount
        if not count:
            raise HTTPException(404, "Account topilmadi")
        if not approved:
            db.execute("DELETE FROM mobile_sessions WHERE account_id=?", (account_id,))
    return {"account_id": account_id, "approved": approved}
