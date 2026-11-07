"""The OpenAI integration is tested with fakes; no API calls or charges."""
import pytest
from fastapi.testclient import TestClient
from app import main, tutor
from app.store import Store
from tests.test_miniapp import UID, TOKEN, hdr

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'BOT_TOKEN', TOKEN)
    monkeypatch.setattr(main, 'ALLOWED_IDS', {UID})
    monkeypatch.setattr(main, 'STORE', Store(str(tmp_path/'medstudy.db')))
    monkeypatch.setenv('BOT_TOKEN', TOKEN)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-real')
    monkeypatch.setenv('AI_ENABLED', '1')
    monkeypatch.setenv('AI_DAILY_LIMIT', '2')
    monkeypatch.setenv('AI_GLOBAL_DAILY_LIMIT', '3')
    calls = []
    async def answer(lesson, question):
        calls.append({'lesson': lesson['id'], 'question': question})
        return {'answer': 'Ergonomika ishni qulay tashkil etishdir.', 'sections': ['Ergonomika tushunchasi']}
    monkeypatch.setattr(tutor, 'generate_answer', answer)
    client = TestClient(main.app)
    return client, calls

def test_status_disabled_without_key(client, monkeypatch):
    c, calls = client
    c.post('/api/consent', headers=hdr())
    monkeypatch.delenv('OPENAI_API_KEY')
    assert c.get('/api/tutor/status', headers=hdr()).json()['enabled'] is False
    assert c.post('/api/tutor/ask', headers=hdr(), json={'lesson_id':'ergonomika','question':'Ergonomika nima?'}).status_code==503
    assert not calls

def test_separate_opt_in_and_daily_limit(client):
    c,calls = client
    c.post('/api/consent', headers=hdr())
    question = {'lesson_id':'ergonomika','question':'Ergonomika nima?'}
    assert c.post('/api/tutor/ask', headers=hdr(), json=question).status_code==403
    assert c.post('/api/tutor/consent', headers=hdr()).status_code==200
    a=c.post('/api/tutor/ask', headers=hdr(), json=question)
    assert a.status_code==200 and a.json()['remaining']==1
    assert 'Ergonomika' in a.json()['answer']
    assert c.post('/api/tutor/ask', headers=hdr(), json=question).status_code==200
    assert c.post('/api/tutor/ask', headers=hdr(), json=question).status_code==429
    assert len(calls)==2
    assert c.get('/api/tutor/status', headers=hdr()).json()['remaining']==0

def test_unauthorized_no_call_and_invalid_inputs(client):
    c,calls=client
    assert c.post('/api/tutor/ask', json={'lesson_id':'ergonomika','question':'Ergonomika nima?'}).status_code==401
    c.post('/api/consent',headers=hdr())
    c.post('/api/tutor/consent',headers=hdr())
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'xxxx','question':'Ergonomika nima?'}).status_code==404
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'ergonomika','question':'Mening pochta emailim a@b.com'}).status_code==422
    assert len(calls)==0

def test_revoke_and_delete_cleans_tables(client):
    c,calls=client
    c.post('/api/consent',headers=hdr())
    c.post('/api/tutor/consent',headers=hdr())
    c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'ergonomika','question':'Ergonomika nima?'})
    assert c.delete('/api/tutor/consent',headers=hdr()).status_code==200
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'ergonomika','question':'Ergonomika nima?'}).status_code==403
    assert c.delete('/api/me',headers=hdr()).status_code==200
    assert main.STORE.ai_usage(UID)==0
    assert not main.STORE.has_ai_consent(UID)

def test_lesson_grounding():
    lesson=main.CATALOG['subjects'][0]['lessons'][0]
    context, heads=tutor.select_context(lesson, 'Ergonomika ish joyiga ta’siri')
    assert 'Ergonomika' in context
    assert len(heads) in range(1,4)
    assert len(context)<=4800
    response={'status':'completed','output':[{'type':'reasoning'},{'type':'message','content':[{'type':'output_text','text':'O‘zbekcha izoh'}]}]}
    assert tutor.extract_output(response)=='O‘zbekcha izoh'
