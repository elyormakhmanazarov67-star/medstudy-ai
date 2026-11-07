"""Verify Telegram WebApp.initData using the algorithm documented by Telegram."""
from __future__ import annotations
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

class AuthError(ValueError):
    pass


def verify_init_data(raw: str, bot_token: str, max_age: int = 3600, now: int | None = None) -> int:
    if not raw or not bot_token or len(raw) > 16384:
        raise AuthError("Telegram ma’lumotlari yo‘q")
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise AuthError("Takroriy maydon")
    data = dict(pairs)
    supplied_hash = data.pop("hash", "")
    if len(supplied_hash) != 64:
        raise AuthError("Imzo mavjud emas")
    try:
        int(supplied_hash, 16)
    except ValueError as exc:
        raise AuthError("Imzo noto‘g‘ri") from exc
    # Exclude hash, but include signature if Telegram includes it.
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, supplied_hash.lower()):
        raise AuthError("Telegram tasdiqlanmadi")
    try:
        auth_date = int(data["auth_date"])
        user = json.loads(data["user"])
        user_id = user["id"]
        if type(user_id) is not int or user_id <= 0:
            raise ValueError
    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise AuthError("Foydalanuvchi ma’lumoti topilmadi") from exc
    timestamp = int(time.time() if now is None else now)
    if not timestamp - max_age <= auth_date <= timestamp + 30:
        raise AuthError("Kirish muddati tugagan. Telegram ilovasini qayta oching")
    return user_id
