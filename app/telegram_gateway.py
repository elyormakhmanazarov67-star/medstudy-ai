"""Telegram webhook gateway for public Free / allowlisted pilot Mini App.

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


def approval_enabled() -> bool:
    return os.getenv('ACCESS_APPROVAL_ENABLED', '0') == '1'


def admin_ids() -> set[int]:
    raw=(os.getenv('ADMIN_USER_IDS','').strip() or os.getenv('ALLOWED_USER_IDS',''))
    try:
        return {int(s.strip()) for s in raw.replace(';',',').split(',') if s.strip()}
    except ValueError:
        return set()


def public_free_enabled() -> bool:
    return os.getenv('PUBLIC_FREE_ENABLED', '0') == '1'


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
        try:
            response = await client.post(f'https://api.telegram.org/bot{token}/{method}', json=payload)
        except httpx.RequestError:
            # Never emit URLs containing the Telegram token into Railway logs.
            raise RuntimeError(f'Telegram {method}: connection failed') from None
        if response.status_code >= 400:
            raise RuntimeError(f'Telegram {method}: HTTP {response.status_code}')
        try:
            result = response.json()
        except ValueError:
            raise RuntimeError(f'Telegram {method}: invalid response') from None
        if not result.get('ok'):
            raise RuntimeError(f'Telegram {method}: API rejected the request')
        return result


async def configure_telegram() -> bool:
    """Opt-in cutover. No webhook set unless AUTO_SET_WEBHOOK=1."""
    if os.getenv('AUTO_SET_WEBHOOK', '0') != '1':
        logger.info('Telegram auto configuration is OFF; Mini App HTTP service only.')
        return False
    if not telegram_setup_ready():
        secret = webhook_secret()
        logger.warning(
            'Cannot configure Telegram: token_present=%s, public_url_valid=%s, webhook_secret_valid=%s',
            bool(bot_token()), bool(public_url()), bool(re.fullmatch(r'[A-Za-z0-9_-]{16,256}', secret)),
        )
        return False
    base = public_url()
    try:
        await api_call('setWebhook', {
            'url': base + '/telegram/webhook',
            'secret_token': webhook_secret(),
            'allowed_updates': ['message', 'callback_query'],
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
                {'command': 'status', 'description': 'Mini App ruxsatim'},
                {'command': 'requests', 'description': 'Admin: kutilayotgan so‘rovlar'},
                {'command': 'approve', 'description': 'Admin: Telegram ID ga ruxsat'},
                {'command': 'reject', 'description': 'Admin: arizani rad etish'},
                {'command': 'revoke', 'description': 'Admin: ruxsatni bekor qilish'},
            ]
        })
        logger.warning('Telegram webhook and Mini App menu successfully registered on %s', base)
        return True
    except (httpx.HTTPError, RuntimeError) as exc:
        logger.warning('Telegram setup failed (%s); Mini App HTTP server is still available.', exc.__class__.__name__ if isinstance(exc, httpx.HTTPError) else str(exc))
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
    store=request.app.state.store
    def is_admin(uid: int) -> bool:
        return uid in admin_ids()
    # Inlined approval buttons are available only to Telegram administrators.
    callback=update.get('callback_query')
    if isinstance(callback,dict):
        from_user=callback.get('from') or {}
        admin_uid=from_user.get('id')
        data=str(callback.get('data') or '')
        match=re.fullmatch(r'access:(approve|reject|revoke):([1-9]\d{0,15})',data)
        if approval_enabled() and isinstance(admin_uid,int) and is_admin(admin_uid) and match:
            action,target=match.group(1),int(match.group(2))
            decision={'approve':'approved','reject':'rejected','revoke':'revoked'}[action]
            try:
                store.review_access(target,decision,admin_uid)
                reply=('✅ Tasdiqlandi' if decision=='approved' else
                       '❌ Rad etildi' if decision=='rejected' else '⛔ Ruxsat bekor qilindi')
                try:
                    await api_call('sendMessage',{'chat_id':target,'text':
                       ('✅ MedStudy AI Mini App uchun ruxsat berildi. /start yuborib ilovani oching.' if decision=='approved'
                        else 'MedStudy AI Mini App ruxsati: '+reply)})
                except (httpx.HTTPError,RuntimeError):
                    logger.warning('Could not send approval notification')
            except ValueError as exc:
                reply=str(exc)
        else:
            reply='Bu amal faqat administratorga ruxsat etilgan'
        try:
            if isinstance(callback.get('id'),str):
                await api_call('answerCallbackQuery',{'callback_query_id':callback['id'],'text':reply[:180]})
        except (httpx.HTTPError,RuntimeError):
            logger.warning('Could not answer callback')
        return {'ok':True}
    message = update.get('message')
    if not isinstance(message, dict):
        return {'ok': True}
    chat = message.get('chat') or {}
    user = message.get('from') or {}
    if chat.get('type') != 'private' or not isinstance(user.get('id'), int):
        return {'ok': True}
    uid = user['id']
    chat_id = chat.get('id')
    if chat_id != uid:
        return {'ok':True}
    text = str(message.get('text') or '').strip()
    cmd = (text.split(maxsplit=1)[0].split('@')[0] if text.startswith('/') else '').lower()
    target_text=text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1))>1 else ''
    is_owner=is_admin(uid)
    approval=approval_enabled()
    markup=None
    if cmd == '/myid':
        body = f'Sizning Telegram ID: {uid}. Uni ochiq joyda ulashmang.'
    elif approval and is_owner and cmd in {'/approve','/reject','/revoke'}:
        if not re.fullmatch(r'[1-9]\d{0,15}',target_text):
            body='Format: /approve 123456789 yoki /reject 123456789 yoki /revoke 123456789'
        else:
            decision={'/approve':'approved','/reject':'rejected','/revoke':'revoked'}[cmd]
            target=int(target_text)
            try:
                store.review_access(target,decision,uid)
                body=f'✅ {target}: {decision}'
                try:
                    await api_call('sendMessage',{'chat_id':target,'text':
                        'MedStudy AI ruxsat holati: '+decision+
                        ('. /start yuborib ilovani oching.' if decision=='approved' else '.')})
                except (httpx.HTTPError,RuntimeError):
                    logger.warning('Could not send approval status')
            except ValueError as exc:
                body=str(exc)
    elif approval and is_owner and cmd=='/help':
        body=('MedStudy AI — administrator buyruqlari:\n'
              '/requests — kutilayotgan arizalar\n'
              '/approve ID — Telegram ID orqali ruxsat berish\n'
              '/reject ID — arizani rad etish\n'
              '/revoke ID — ruxsatni bekor qilish\n'
              '/myid — mening Telegram ID raqamim')
    elif approval and is_owner and cmd=='/requests':
        pending=store.pending_access()
        body=('Kutilayotgan so‘rovlar:\n'+'\n'.join(str(x) for x in pending)
              +'\n\n/approve ID, /reject ID yoki /revoke ID') if pending else 'Kutilayotgan so‘rovlar yo‘q.'
    elif approval and cmd=='/status':
        status='approved' if is_owner else store.access_status(uid)
        body={'approved':'✅ Mini App ochiq.', 'pending':'⏳ Administrator javobi kutilmoqda.',
              'rejected':'❌ So‘rov rad etilgan.', 'revoked':'⛔ Ruxsat bekor qilingan.',
              'not_requested':'/start orqali qabul so‘rovini yuboring.'}[status]
    elif approval and not is_owner and cmd in {'/start','/help',''}:
        status,created=store.request_access(uid)
        if created:
            for admin_uid in sorted(admin_ids())[:5]:
                keyboard={'inline_keyboard':[
                    [{'text':'✅ Tasdiqlash','callback_data':f'access:approve:{uid}'},
                     {'text':'❌ Rad etish','callback_data':f'access:reject:{uid}'}]
                ]}
                try:
                    await api_call('sendMessage',{'chat_id':admin_uid,
                        'text':f'📩 MedStudy AI Mini App kirish so‘rovi.\nTelegram ID: {uid}\n'
                               f'/approve {uid} yoki /reject {uid}',
                        'reply_markup':keyboard})
                except (httpx.HTTPError,RuntimeError):
                    logger.warning('Cannot notify administrator; request remains in database')
        if status=='approved':
            body=('✅ Ruxsat tasdiqlangan. MedStudy AI Mini App’ni ochishingiz mumkin.')
            markup={'inline_keyboard': [[{'text':'📱 MedStudy AI ni ochish',
                       'web_app':{'url':public_url()}}]]} if public_url() else None
        elif status=='pending':
            body=('⏳ So‘rovingiz administratorga yuborildi. '
                  'Ruxsat berilgach bu yerga xabar keladi. /status orqali tekshiring.')
        elif status=='rejected':
            body='❌ So‘rovingiz rad etilgan. Administratorga murojaat qiling.'
        else:
            body='⛔ Mini App ruxsatingiz bekor qilingan. Administratorga murojaat qiling.'
    elif not public_free_enabled() and uid not in allowed_users():
        body='MedStudy AI hozir yopiq sinovda. /myid orqali ID ni ko‘ring va administratorga shaxsiy tartibda murojaat qiling.'
    elif cmd in {'/start','/help',''}:
        body=('🎓 MedStudy AI — tibbiyot talabalari uchun o‘quv yordamchisi.\n\n'
              '📚 6 fan, 81 mavzu va 631 ta test savoli.\n'
              '🆓 Darslar va testlar bepul. Pro hali faol emas.\n'
              '⚠️ Materiallar mustaqil o‘quv loyihasiga tegishli.\n\n'
              'Quyidagi tugma orqali Mini App’ni oching.')
        markup={'inline_keyboard': [[{'text':'📱 MedStudy AI ni ochish',
                 'web_app':{'url':public_url()}}]]} if public_url() else None
    elif cmd == '/privacy':
        body=('Telegram ID, rozilik va test natijalari saqlanadi. '
              'Kirish so‘rovining holati, vaqti va uni ko‘rib chiqqan admin IDsi ham qayd etiladi. '
              'Ma’lumotlarni Mini App ichidan o‘chirishingiz mumkin. '
              'Bu rasmiy universitet xizmati emas.')
    else:
        body='Mini App uchun /start yoki /status buyrug‘ini yuboring.'
    payload = {'chat_id': chat_id, 'text': body}
    if markup:
        payload['reply_markup'] = markup
    try:
        await api_call('sendMessage', payload)
    except (httpx.HTTPError, RuntimeError):
        logger.exception('Telegram sendMessage failed')
        raise HTTPException(502, 'Telegram send failed')
    return {'ok': True}
