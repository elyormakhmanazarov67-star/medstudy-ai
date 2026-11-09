"""Admin may approve a user ID without a prior request, retaining strict access control."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from fastapi.testclient import TestClient

from app import main, telegram_gateway as gateway
from app.store import Store

TOKEN='111111:test-secret-token'

def signed(uid):
    data={'user':json.dumps({'id':uid,'first_name':'Test'},separators=(',',':')),
          'auth_date':str(int(time.time()))}
    digest=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest()
    message='\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
    data['hash']=hmac.new(digest,message.encode(),hashlib.sha256).hexdigest()
    return {'X-Telegram-Init-Data':urlencode(data)}

def test_manual_approval_works_without_request_and_survives_public_free_off(monkeypatch,tmp_path):
    store=Store(str(tmp_path/'users.sqlite'))
    monkeypatch.setattr(main,'STORE',store)
    monkeypatch.setattr(main.app.state,'store',store)
    monkeypatch.setattr(main,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(main,'ALLOWED_IDS',{100})
    monkeypatch.setenv('ALLOWED_USER_IDS','100')
    monkeypatch.setenv('ACCESS_APPROVAL_ENABLED','1')
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','0')
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET','z'*40)
    monkeypatch.setenv('WEB_APP_URL','https://medstudy.example.org')
    calls=[]
    async def capture(method,payload):
        calls.append((method,payload))
        return {'ok':True}
    monkeypatch.setattr(gateway,'api_call',capture)
    client=TestClient(main.app)
    secret={'X-Telegram-Bot-Api-Secret-Token':'z'*40}
    payload={'update_id':1,'message':{'chat':{'type':'private','id':100},
        'from':{'id':100},'text':'/approve 200'}}
    assert client.get('/api/me',headers=signed(200)).status_code==403
    assert client.post('/telegram/webhook',json=payload,headers=secret).status_code==200
    assert store.access_status(200)=='approved'
    assert client.get('/api/me',headers=signed(200)).status_code==200
    assert client.post('/api/consent',headers=signed(200)).status_code==200
    assert client.get('/api/catalog',headers=signed(200)).status_code==200
    assert client.get('/api/me',headers=signed(300)).status_code==403
    payload['message']['text']='/revoke 200'
    assert client.post('/telegram/webhook',json=payload,headers=secret).status_code==200
    assert store.access_status(200)=='revoked'
    assert client.get('/api/me',headers=signed(200)).status_code==403
    payload['message']['text']='/approve 200'
    assert client.post('/telegram/webhook',json=payload,headers=secret).status_code==200
    assert store.access_status(200)=='approved'
    assert client.get('/api/me',headers=signed(200)).status_code==200
    payload['message']['from']['id']=300
    payload['message']['chat']['id']=300
    payload['message']['text']='/revoke 200'
    assert client.post('/telegram/webhook',json=payload,headers=secret).status_code==200
    assert store.access_status(200)=='approved'
    assert any(method=='sendMessage' and p.get('chat_id')==100 for method,p in calls)
