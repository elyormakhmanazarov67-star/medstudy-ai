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
