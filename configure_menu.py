"""Set Telegram bot's Mini App menu button; HTTPS server must already be deployed."""
from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlparse
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
token=os.getenv('BOT_TOKEN','').strip()
url=os.getenv('WEB_APP_URL','').strip()
if not token or token == 'PASTE_YOUR_SECRET_TOKEN_HERE':
    raise SystemExit('BOT_TOKEN ni .env faylida kiriting. Tokenni chatga yubormang.')
p=urlparse(url)
if p.scheme!='https' or not p.netloc or p.username or p.password:
    raise SystemExit('WEB_APP_URL haqiqiy PUBLIC HTTPS manzil bo‘lishi shart.')
with httpx.Client(timeout=20) as client:
    resp=client.post(f'https://api.telegram.org/bot{token}/setChatMenuButton',json={
        'menu_button': {'type':'web_app','text':'MedStudy AI','web_app':{'url':url}}
    })
    data=resp.json()
if not data.get('ok'):
    raise SystemExit('Telegram xatosi: '+str(data.get('description','Noma’lum xato')))
print('✅ Telegram menyusiga MedStudy AI Mini App qo‘shildi.')
print('BotFather orqali bot bilan chatni oching va menyu tugmasini bosing.')
