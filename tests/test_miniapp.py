import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from app.auth import verify_init_data, AuthError
from app.core import load_catalog, grade
from app.store import Store
from app import main

TOKEN='111111:test-secret-token'
UID=224466

def sign(uid=UID, now=None, token=TOKEN):
    data={'user':json.dumps({'id':uid,'first_name':'Demo'}, separators=(',',':')),
          'auth_date':str(int(time.time() if now is None else now))}
    secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
    check='\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
    data['hash']=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    return urlencode(data)

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'BOT_TOKEN',TOKEN)
    monkeypatch.setattr(main,'ALLOWED_IDS',{UID})
    monkeypatch.setattr(main,'DEV_PREVIEW',False)
    monkeypatch.setattr(main,'STORE',Store(str(tmp_path/'db.sqlite')))
    return TestClient(main.app)

def hdr(raw=None):return {'X-Telegram-Init-Data': raw or sign()}

def test_catalog_and_grading():
    c=load_catalog()
    assert len(c['subjects'])==5
    assert sum(len(s['lessons']) for s in c['subjects'])==66
    assert len(c['subjects'][0]['lessons'])==31
    assert len(c['subjects'][1]['lessons'])==12
    assert len(c['subjects'][0]['lessons'][0]['questions'])==1
    assert c['subjects'][0]['lessons'][0]['sections']
    assert grade([],[])==(0,[])


def test_signature_and_expiry():
    assert verify_init_data(sign(),TOKEN)==UID
    with pytest.raises(AuthError):verify_init_data(sign().replace('first_name','last_name'),TOKEN)
    with pytest.raises(AuthError):verify_init_data(sign(now=int(time.time())-4000),TOKEN)
    with pytest.raises(AuthError):verify_init_data(sign()+'&user=evil',TOKEN)

def test_unauthorized_access(client):
    assert client.get('/api/catalog').status_code==401
    assert client.get('/api/catalog',headers=hdr(sign(uid=44))).status_code==403
    assert client.get('/api/catalog',headers=hdr()).status_code==403

def test_consent_catalog_quiz_and_delete(client):
    assert client.get('/api/me',headers=hdr()).json()['consented'] is False
    assert client.post('/api/consent',headers=hdr()).status_code==200
    c=client.get('/api/catalog',headers=hdr())
    assert c.status_code==200 and len(c.json()['subjects'])==5
    empty=client.get('/api/lessons/ergonomika',headers=hdr()).json()
    assert len(empty['questions'])==1
    assert len(empty['teacher_materials'])>=1
    assert len(empty['supplementary'])>=1
    body={'lesson_id':'ergonomika','question_ids':['old'],'answers':[0]}
    assert client.post('/api/attempts',json=body,headers=hdr()).status_code==400
    lesson=client.get('/api/lessons/eng_l1',headers=hdr()).json()
    assert len(lesson['questions'])==2
    assert 'answer' not in lesson['questions'][0]
    qs=main.CATALOG['subjects'][3]['lessons'][0]['questions']
    body={'lesson_id':'eng_l1','question_ids':[q['id'] for q in qs],
          'answers':[q['answer'] for q in qs]}
    done=client.post('/api/attempts',json=body,headers=hdr())
    assert done.status_code==200 and done.json()['score']==2
    assert client.get('/api/progress',headers=hdr()).json()['attempts_count']==1
    assert client.delete('/api/me',headers=hdr()).status_code==200
    assert client.get('/api/catalog',headers=hdr()).status_code==403


def test_cannot_submit_arbitrary_or_incomplete_question_set(client):
    client.post('/api/consent',headers=hdr())
    res=client.post('/api/attempts',json={'lesson_id':'eng_l1','question_ids':['wrong'],'answers':[0]},headers=hdr())
    assert res.status_code==400
    res=client.post('/api/attempts',json={'lesson_id':'eng_l1','question_ids':['wrong'],'answers':[9]},headers=hdr())
    assert res.status_code==400


def test_wrong_review(client):
    client.post('/api/consent',headers=hdr())
    qs=main.CATALOG['subjects'][3]['lessons'][0]['questions']
    answers=[(qs[0]['answer']+1)%4, qs[1]['answer']]
    full={'lesson_id':'eng_l1','question_ids':[q['id'] for q in qs],'answers':answers}
    done=client.post('/api/attempts',json=full,headers=hdr())
    assert done.status_code==200 and done.json()['score']==1
    review=client.get('/api/review/eng_l1',headers=hdr()).json()
    assert len(review['questions'])==1
    retry={'lesson_id':'eng_l1','question_ids':[qs[0]['id']], 'answers':[qs[0]['answer']]}
    result=client.post('/api/attempts',json=retry,headers=hdr())
    assert result.status_code==200 and result.json()['score']==1
    assert client.get('/api/progress',headers=hdr()).json()['latest'][0]['total']==2


def test_independent_required_and_supplementary_quizzes(client):
    client.post('/api/consent',headers=hdr())
    lid='bio_l1'
    source=main.CATALOG['subjects'][4]['lessons'][0]
    required=source['questions']
    extra=source['supplement_questions']
    assert required and extra
    assert set(q['id'] for q in required).isdisjoint(set(q['id'] for q in extra))
    data={'lesson_id':lid,'question_ids':[q['id'] for q in extra],
          'answers':[q['answer'] for q in extra],'category':'supplementary'}
    assert client.post('/api/attempts',json=data,headers=hdr()).json()['mode']=='supplementary'
    assert client.get('/api/progress',headers=hdr()).json()['latest']==[]
    req={'lesson_id':lid,'question_ids':[q['id'] for q in required],
         'answers':[q['answer'] for q in required],'category':'required'}
    done=client.post('/api/attempts',json=req,headers=hdr())
    assert done.status_code==200 and done.json()['mode']=='full'
    assert client.get('/api/progress',headers=hdr()).json()['latest'][0]['total']==len(required)
    bad=client.post('/api/attempts',json={**data,'category':'required'},headers=hdr())
    assert bad.status_code==400
    bad=client.post('/api/attempts',json={**req,'category':'supplementary'},headers=hdr())
    assert bad.status_code==400
    extra_result=client.get('/api/lessons/'+lid,headers=hdr()).json()
    assert extra_result['supplement_sections']
    assert extra_result['supplement_question_count']==len(extra)
    assert 'answer' not in extra_result['supplement_questions'][0]
