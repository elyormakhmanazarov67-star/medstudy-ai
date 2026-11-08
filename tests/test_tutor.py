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
    async def answer(lesson, question, mode='explain', level='standard', history=None):
        calls.append({'lesson': lesson['id'], 'question': question, 'mode': mode,
                      'level': level, 'history': history or []})
        return {'answer': 'Ergonomika ishni qulay tashkil etishdir.', 'sections': ['Ergonomika tushunchasi']}
    monkeypatch.setattr(tutor, 'generate_answer', answer)
    client = TestClient(main.app)
    return client, calls

def test_status_disabled_without_key(client, monkeypatch):
    c, calls = client
    c.post('/api/consent', headers=hdr())
    monkeypatch.delenv('OPENAI_API_KEY')
    assert c.get('/api/tutor/status', headers=hdr()).json()['enabled'] is False
    assert c.post('/api/tutor/ask', headers=hdr(), json={'lesson_id':'eng_l1','question':'What does tooth mean?'}).status_code==503
    assert not calls

def test_separate_opt_in_and_daily_limit(client):
    c,calls = client
    c.post('/api/consent', headers=hdr())
    question = {'lesson_id':'eng_l1','question':'What does tooth mean?'}
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
    assert c.post('/api/tutor/ask', json={'lesson_id':'eng_l1','question':'What does tooth mean?'}).status_code==401
    c.post('/api/consent',headers=hdr())
    c.post('/api/tutor/consent',headers=hdr())
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'xxxx','question':'What does tooth mean?'}).status_code==404
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'eng_l1','question':'Mening pochta emailim a@b.com'}).status_code==422
    assert len(calls)==0

def test_revoke_and_delete_cleans_tables(client):
    c,calls=client
    c.post('/api/consent',headers=hdr())
    c.post('/api/tutor/consent',headers=hdr())
    c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'eng_l1','question':'What does tooth mean?'})
    assert c.delete('/api/tutor/consent',headers=hdr()).status_code==200
    assert c.post('/api/tutor/ask',headers=hdr(),json={'lesson_id':'eng_l1','question':'What does tooth mean?'}).status_code==403
    assert c.delete('/api/me',headers=hdr()).status_code==200
    assert main.STORE.ai_usage(UID)==0
    assert not main.STORE.has_ai_consent(UID)

def test_lesson_grounding():
    lesson=main.CATALOG['subjects'][3]['lessons'][0]
    context, heads=tutor.select_context(lesson, 'tooth')
    assert 'lug‘at' in context.lower()
    assert len(heads) in range(1,4)
    assert len(context)<=4800
    response={'status':'completed','output':[{'type':'reasoning'},{'type':'message','content':[{'type':'output_text','text':'O‘zbekcha izoh'}]}]}
    assert tutor.extract_output(response)=='O‘zbekcha izoh'

def test_tutor_learning_modes_and_rejects_invalid_mode(client):
    c, calls = client
    c.post('/api/consent', headers=hdr())
    c.post('/api/tutor/consent', headers=hdr())
    base = {'lesson_id':'eng_l1', 'question':'What does tooth mean?'}
    assert c.post('/api/tutor/ask', headers=hdr(), json={**base, 'mode':'clinical'}).status_code == 422
    assert len(calls) == 0
    response = c.post('/api/tutor/ask', headers=hdr(), json={**base, 'mode':'recall'})
    assert response.status_code == 200
    assert calls[0]['mode'] == 'recall'

def test_teaching_styles_and_response_handling():
    assert 'savol' in tutor.response_style('recall').lower()
    assert 'misol' in tutor.response_style('example').lower()
    with pytest.raises(ValueError):
        tutor.response_style('unsafe')

def test_multiturn_oral_tutor_is_bounded_and_opt_in(client):
    c,calls=client
    c.post('/api/consent',headers=hdr())
    payload={'lesson_id':'eng_l1','question':'Menga nazariy savol bering',
             'mode':'oral','level':'basic','history':[]}
    assert c.post('/api/tutor/ask',headers=hdr(),json=payload).status_code==403
    c.post('/api/tutor/consent',headers=hdr())
    r=c.post('/api/tutor/ask',headers=hdr(),json=payload)
    assert r.status_code==200
    assert calls[0]['mode']=='oral' and calls[0]['level']=='basic'
    conversation=[{'role':'user','content':'Menga nazariy savol bering'},
                  {'role':'assistant','content':'Tish haqida qanday tushunchangiz bor?'}]
    r=c.post('/api/tutor/ask',headers=hdr(),json={**payload,'history':conversation,
        'question':'Tish qattiq to‘qimalardan tashkil topadi'})
    assert r.status_code==200 and calls[1]['history']==conversation
    assert c.post('/api/tutor/ask',headers=hdr(),json={**payload,'history':[conversation[1]]}).status_code==422
    assert c.post('/api/tutor/ask',headers=hdr(),json={**payload,'level':'expert'}).status_code==422
    assert c.post('/api/tutor/ask',headers=hdr(),json={**payload,'history':conversation*4}).status_code==422
    assert c.post('/api/tutor/ask',headers=hdr(),json={**payload,'history':[
        {'role':'user','content':'email a@b.com'},{'role':'assistant','content':'Ok'}
    ]}).status_code==422
    assert len(calls)==2

def test_oral_and_level_styles():
    assert 'savol' in tutor.response_style('oral').lower()
    assert 'boshlang‘ich' in tutor.response_level('basic').lower()
    with pytest.raises(ValueError):
        tutor.response_level('unknown')



def test_global_quota_shared_between_users(client, monkeypatch):
    c,calls=client
    second=UID+1
    monkeypatch.setattr(main, 'ALLOWED_IDS', {UID,second})
    monkeypatch.setenv('AI_GLOBAL_DAILY_LIMIT','3')
    h2=hdr(__import__('tests.test_miniapp',fromlist=['sign']).sign(uid=second))
    for headers in (hdr(),h2):
        assert c.post('/api/consent',headers=headers).status_code==200
        assert c.post('/api/tutor/consent',headers=headers).status_code==200
    payload={'lesson_id':'eng_l1','question':'Tish haqida izoh bering'}
    assert c.post('/api/tutor/ask',headers=hdr(),json=payload).status_code==200
    assert c.post('/api/tutor/ask',headers=hdr(),json=payload).status_code==200
    assert c.get('/api/tutor/status',headers=h2).json()['remaining']==1
    assert c.post('/api/tutor/ask',headers=h2,json=payload).status_code==200
    assert c.post('/api/tutor/ask',headers=h2,json=payload).status_code==429
    assert c.get('/api/tutor/status',headers=h2).json()['remaining']==0
    assert len(calls)==3
    assert main.STORE.ai_global_usage()==3


def test_untrusted_chat_not_saved_to_database(client):
    import sqlite3
    c,calls=client
    c.post('/api/consent',headers=hdr())
    c.post('/api/tutor/consent',headers=hdr())
    marker='privatetutorhistoryexample-notstored'
    p={'lesson_id':'eng_l1','question':marker,'mode':'oral',
       'history':[{'role':'user','content':'Avval savol berdim'},
                  {'role':'assistant','content':'Menga tarixdan savol bering'}]}
    assert c.post('/api/tutor/ask',headers=hdr(),json=p).status_code==200
    with main.STORE.connect() as db:
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert not any('message' in x or 'transcript' in x for x in names)
        assert marker not in str(db.iterdump())
        assert main.STORE.ai_usage(UID)==1


def test_openai_payload_grounded_stateless_and_oral_stages(monkeypatch):
    import asyncio
    import json
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
    monkeypatch.setenv('AI_ENABLED','1')
    records=[]
    def handler(request):
        body=json.loads(request.content)
        records.append(body)
        return httpx.Response(200,json={'status':'completed','output':[
            {'type':'message','content':[{'type':'output_text','text':'Mavzudagi ta’rifni tekshiring.'}]}]})
    constructor=httpx.AsyncClient
    def mocked_client(*args,**kwargs):
        kwargs['transport']=httpx.MockTransport(handler)
        return constructor(*args,**kwargs)
    monkeypatch.setattr(tutor.httpx,'AsyncClient',mocked_client)
    lesson=main.CATALOG['subjects'][4]['lessons'][1]
    first=asyncio.run(tutor.generate_answer(lesson,'Bitta savol bering',mode='oral',level='basic'))
    second=asyncio.run(tutor.generate_answer(lesson,'ATP qayerda hosil bo‘ladi?',
        mode='oral',level='advanced',history=[
        {'role':'user','content':'Bitta savol bering'},
        {'role':'assistant','content':'ATP sintezi nima?'}]))
    assert first['answer'] and second['answer']
    assert all(x['store'] is False and x['max_output_tokens']<=720 for x in records)
    assert all('DARSDAN_PARCHALAR' in x['input'] for x in records)
    assert 'birinchi savol' in records[0]['input'].lower()
    assert 'talabaning hozirgi javobini' in records[1]['input'].lower()
    assert 'ATP sintezi nima?' in records[1]['input']
    assert len(records)==2


def test_response_failures_do_not_leak_secrets(monkeypatch):
    import asyncio
    import httpx
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
    def handler(request):
        return httpx.Response(429, json={'error':{'message':'secret private-key must not appear'}})
    original=httpx.AsyncClient
    monkeypatch.setattr(tutor.httpx,'AsyncClient',lambda *a,**kw:original(
        *a,transport=httpx.MockTransport(handler),**kw))
    lesson=main.CATALOG['subjects'][3]['lessons'][0]
    with pytest.raises(tutor.TutorUnavailable) as err:
        asyncio.run(tutor.generate_answer(lesson,'What is a tooth?'))
    assert 'private-key' not in str(err.value)
    assert 'balansi' in str(err.value).lower()
