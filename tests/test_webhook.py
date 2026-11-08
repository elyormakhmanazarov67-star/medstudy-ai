"""Webhook must reject unauthorized posts and only respond to private messages."""
from fastapi.testclient import TestClient
from app import main
from app import telegram_gateway as gateway


def test_webhook_requires_secret(monkeypatch):
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'a' * 40)
    client = TestClient(main.app)
    payload = {'update_id':123, 'message':{'chat':{'id':100,'type':'private'},'from':{'id':100},'text':'/myid'}}
    assert client.post('/telegram/webhook', json=payload).status_code == 403
    assert client.post('/telegram/webhook', headers={'X-Telegram-Bot-Api-Secret-Token':'bad'}, json=payload).status_code == 403


def test_webhook_id_and_minapp_entry(monkeypatch):
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'a' * 40)
    monkeypatch.setenv('BOT_TOKEN', '12345:abc')
    monkeypatch.setenv('WEB_APP_URL', 'https://medstudy.example.org')
    monkeypatch.setenv('ALLOWED_USER_IDS', '100')
    calls=[]
    async def fake_call(method,payload):
        calls.append((method,payload))
        return {'ok':True}
    monkeypatch.setattr(gateway,'api_call',fake_call)
    client = TestClient(main.app)
    headers={'X-Telegram-Bot-Api-Secret-Token':'a'*40}
    body={'update_id':11,'message':{'chat':{'id':100,'type':'private'},'from':{'id':100},'text':'/myid'}}
    assert client.post('/telegram/webhook', headers=headers,json=body).status_code==200
    assert '100' in calls[-1][1]['text']
    body['message']['text']='/start'
    assert client.post('/telegram/webhook', headers=headers,json=body).status_code==200
    assert calls[-1][1]['reply_markup']['inline_keyboard'][0][0]['web_app']['url']=='https://medstudy.example.org'
    body['message']['from']['id']=200
    body['message']['chat']['id']=200
    assert client.post('/telegram/webhook', headers=headers,json=body).status_code==200
    assert 'reply_markup' not in calls[-1][1]


def test_webhook_ignores_group_chat(monkeypatch):
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET', 'b'*40)
    async def fail_if_called(method, payload):
        raise AssertionError('No message should be sent')
    monkeypatch.setattr(gateway,'api_call',fail_if_called)
    client=TestClient(main.app)
    payload={'update_id':222,'message':{'chat':{'id':-10,'type':'group'},'from':{'id':9},'text':'/start'}}
    assert client.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'b'*40},json=payload).status_code==200


def test_public_url_validation(monkeypatch):
    monkeypatch.setenv('WEB_APP_URL','http://localhost:8000')
    monkeypatch.delenv('RAILWAY_PUBLIC_DOMAIN',raising=False)
    assert gateway.public_url()==''
    monkeypatch.setenv('WEB_APP_URL','')
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN','medstudy.up.railway.app')
    assert gateway.public_url()=='https://medstudy.up.railway.app'


def test_webhook_public_free_start_and_privacy(monkeypatch):
    monkeypatch.setenv('PUBLIC_FREE_ENABLED', '1')
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET','s'*40)
    monkeypatch.setenv('WEB_APP_URL','https://medstudy.example.org')
    monkeypatch.setenv('ALLOWED_USER_IDS','100')
    calls=[]
    async def capture(method,payload):
        calls.append((method,payload))
        return {'ok':True}
    monkeypatch.setattr(gateway,'api_call',capture)
    client=TestClient(main.app)
    headers={'X-Telegram-Bot-Api-Secret-Token':'s'*40}
    body={'update_id':992,'message':{'chat':{'id':234,'type':'private'},
          'from':{'id':234},'text':'/start'}}
    r=client.post('/telegram/webhook',headers=headers,json=body)
    assert r.status_code==200
    assert 'reply_markup' in calls[-1][1]
    assert 'bepul' in calls[-1][1]['text']
    assert '/myid' not in calls[-1][1]['text']
    body['message']['text']='/privacy'
    assert client.post('/telegram/webhook',headers=headers,json=body).status_code==200
    assert 'test natijalari' in calls[-1][1]['text']
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','0')
    body['message']['text']='/start'
    assert client.post('/telegram/webhook',headers=headers,json=body).status_code==200
    assert 'reply_markup' not in calls[-1][1]


def test_approval_webhook_request_admin_callback_and_revocation(monkeypatch,tmp_path):
    from app.store import Store
    monkeypatch.setenv('ACCESS_APPROVAL_ENABLED','1')
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    monkeypatch.setenv('BOT_TOKEN','12345:abc')
    monkeypatch.setenv('TELEGRAM_WEBHOOK_SECRET','x'*40)
    monkeypatch.setenv('WEB_APP_URL','https://medstudy.example.org')
    monkeypatch.setenv('ALLOWED_USER_IDS','100')
    store=Store(str(tmp_path/'access.sqlite'))
    monkeypatch.setattr(main.app.state,'store',store)
    calls=[]
    async def capture(method,payload):
        calls.append((method,payload))
        return {'ok':True}
    monkeypatch.setattr(gateway,'api_call',capture)
    client=TestClient(main.app)
    headers={'X-Telegram-Bot-Api-Secret-Token':'x'*40}
    start={'update_id':5501,'message':{'chat':{'id':200,'type':'private'},
        'from':{'id':200},'text':'/start'}}
    assert client.post('/telegram/webhook',headers=headers,json=start).status_code==200
    assert store.access_status(200)=='pending'
    admin_notifications=[p for m,p in calls if m=='sendMessage' and p.get('chat_id')==100]
    assert len(admin_notifications)==1
    assert admin_notifications[0]['reply_markup']['inline_keyboard'][0][0]['callback_data']=='access:approve:200'
    newcomer_msgs=[p for m,p in calls if m=='sendMessage' and p.get('chat_id')==200]
    assert 'reply_markup' not in newcomer_msgs[-1]
    # Duplicate /start does not send duplicate notifications.
    assert client.post('/telegram/webhook',headers=headers,json=start).status_code==200
    assert len([p for m,p in calls if m=='sendMessage' and p.get('chat_id')==100])==1
    # Forged callback with correct webhook secret but non-admin identity cannot approve.
    callback={'update_id':5502,'callback_query':{'id':'c1','from':{'id':200},
        'data':'access:approve:200'}}
    assert client.post('/telegram/webhook',headers=headers,json=callback).status_code==200
    assert store.access_status(200)=='pending'
    callback['callback_query']['from']['id']=100
    assert client.post('/telegram/webhook',headers=headers,json=callback).status_code==200
    assert store.access_status(200)=='approved'
    assert client.post('/telegram/webhook',headers=headers,json=start).status_code==200
    allowed=[p for m,p in calls if m=='sendMessage' and p.get('chat_id')==200]
    assert 'reply_markup' in allowed[-1]
    revoke={'update_id':5503,'message':{'chat':{'id':100,'type':'private'},
         'from':{'id':100},'text':'/revoke 200'}}
    assert client.post('/telegram/webhook',headers=headers,json=revoke).status_code==200
    assert store.access_status(200)=='revoked'
    assert client.post('/telegram/webhook',headers=headers,json=start).status_code==200
    denied=[p for m,p in calls if m=='sendMessage' and p.get('chat_id')==200]
    assert 'reply_markup' not in denied[-1]
