"""Small Telegram webhook gateway for the closed pilot Mini App.

No update bodies or tokens are logged. A single HTTPS service can host both
Telegram's Mini App and the Telegram Bot API webhook.
"""
from __future__ import annotations

import hmac
import logging
import os
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter()


def public_url() -> str:
    configured = os.getenv('WEB_APP_URL', '').strip().rstrip('/')
    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', '').strip()
    candidate = configured or (f'https://{railway_domain}' if railway_domain else '')
    parsed = urlparse(candidate)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ''
    return candidate


def bot_token() -> str:
    return os.getenv('BOT_TOKEN', '').strip()


def webhook_secret() -> str:
    return os.getenv('TELEGRAM_WEBHOOK_SECRET', '').strip()


def allowed_users() -> set[int]:
    raw = os.getenv('ALLOWED_USER_IDS', '').replace(';', ',')
    return {int(v.strip()) for v in raw.split(',') if v.strip()}


def telegram_setup_ready() -> bool:
    secret = webhook_secret()
    return bool(bot_token() and public_url() and re.fullmatch(r'[A-Za-z0-9_-]{16,256}', secret))


async def api_call(method: str, payload: dict) -> dict:
    token = bot_token()
    if not token:
        raise RuntimeError('BOT_TOKEN is unset')
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f'https://api.telegram.org/bot{token}/{method}', json=payload)
        response.raise_for_status()
        result = response.json()
        if not result.get('ok'):
            raise RuntimeError(f'Telegram {method} returned an error')
        return result


async def configure_telegram() -> bool:
    """Opt-in cutover. No webhook set unless AUTO_SET_WEBHOOK=1."""
    if os.getenv('AUTO_SET_WEBHOOK', '0') != '1':
        logger.info('Telegram auto configuration is OFF; Mini App HTTP service only.')
        return False
    if not telegram_setup_ready():
        logger.warning('Cannot configure Telegram: BOT_TOKEN, WEB_APP_URL, or TELEGRAM_WEBHOOK_SECRET not ready.')
        return False
    base = public_url()
    try:
        await api_call('setWebhook', {
            'url': base + '/telegram/webhook',
            'secret_token': webhook_secret(),
            'allowed_updates': ['message'],
            'max_connections': 10,
        })
        await api_call('setChatMenuButton', {
            'menu_button': {
                'type': 'web_app',
                'text': 'MedStudy AI',
                'web_app': {'url': base},
            }
        })
        await api_call('setMyCommands', {
            'commands': [
                {'command': 'start', 'description': 'MedStudy AI ni ochish'},
                {'command': 'myid', 'description': 'Telegram ID raqamim'},
                {'command': 'help', 'description': 'Yordam'},
                {'command': 'privacy', 'description': 'Maxfiylik haqida'},
            ]
        })
        logger.info('Telegram webhook + Mini App menu configured.')
        return True
    except (httpx.HTTPError, RuntimeError):
        logger.exception('Telegram configuration failed. Mini App web server remains available.')
        return False


@router.post('/telegram/webhook', include_in_schema=False)
async def receive_telegram_update(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    secret = webhook_secret()
    if not secret or not x_telegram_bot_api_secret_token or not hmac.compare_digest(secret, x_telegram_bot_api_secret_token):
        raise HTTPException(403, 'Forbidden')
    if int(request.headers.get('content-length') or 0) > 65536:
        raise HTTPException(413, 'Payload too large')
    try:
        update = await request.json()
    except ValueError:
        raise HTTPException(400, 'Invalid JSON')
    if not isinstance(update, dict):
        raise HTTPException(400, 'Invalid update')
    message = update.get('message')
    if not isinstance(message, dict):
        return {'ok': True}
    chat = message.get('chat') or {}
    user = message.get('from') or {}
    if chat.get('type') != 'private' or not isinstance(user.get('id'), int):
        return {'ok': True}
    uid = user['id']
    chat_id = chat.get('id')
    text = str(message.get('text') or '').strip()
    cmd = (text.split(maxsplit=1)[0].split('@')[0] if text.startswith('/') else '').lower()
    if cmd == '/myid':
        body = f'Sizning Telegram ID: {uid}. Uni ochiq joyda ulashmang.'
        markup = None
    elif uid not in allowed_users():
        body = 'MedStudy AI hozir yopiq sinovda. /myid orqali ID ni ko‘ring va administratorga shaxsiy tartibda murojaat qiling.'
        markup = None
    elif cmd in {'/start', '/help', ''}:
        body = ('🎓 MedStudy AI — yopiq sinov versiyasi.\n\n'
                '📚 4 ta fan, 5 ta dars, 34 ta test savoli.\n'
                '📊 Test natijalari va xatolarni qaytarish Mini App ichida.\n'
                '⚠️ O‘quv materiallari mutaxassis tasdig‘ini kutmoqda.\n\n'
                'Quyidagi tugmani bosib Mini App ni oching.')
        markup = {'inline_keyboard': [[{'text':'📱 MedStudy AI ni ochish', 'web_app':{'url': public_url()}}]]} if public_url() else None
    elif cmd == '/privacy':
        body = ('Sinovda Telegram ID, rozilik va test natijalari saqlanadi. '
                'Ma’lumotlarni Mini App ichida o‘chirishingiz mumkin. '
                'Ilova mustaqil ta’lim loyihasi, universitetning rasmiy xizmati emas.')
        markup = None
    else:
        body = 'Mini App uchun /start buyrug‘ini yuboring.'
        markup = None
    payload = {'chat_id': chat_id, 'text': body}
    if markup:
        payload['reply_markup'] = markup
    try:
        await api_call('sendMessage', payload)
    except (httpx.HTTPError, RuntimeError):
        logger.exception('Telegram sendMessage failed')
        raise HTTPException(502, 'Telegram send failed')
    return {'ok': True}
