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
    assert len(c['subjects'])==6
    assert sum(len(s['lessons']) for s in c['subjects'])==81
    assert len(c['subjects'][0]['lessons'])==31
    assert len(c['subjects'][1]['lessons'])==12
    assert len(c['subjects'][0]['lessons'][0]['questions'])==10
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
    assert c.status_code==200 and len(c.json()['subjects'])==6
    empty=client.get('/api/lessons/ergonomika',headers=hdr()).json()
    assert len(empty['questions'])==10
    assert 'teacher_materials' not in empty
    assert 'sammu_books' not in empty
    assert 'supplementary' not in empty
    body={'lesson_id':'ergonomika','question_ids':['old'],'answers':[0]}
    assert client.post('/api/attempts',json=body,headers=hdr()).status_code==400
    lesson=client.get('/api/lessons/eng_l1',headers=hdr()).json()
    assert len(lesson['questions'])==10
    assert 'answer' not in lesson['questions'][0]
    qs=main.CATALOG['subjects'][3]['lessons'][0]['questions']
    body={'lesson_id':'eng_l1','question_ids':[q['id'] for q in qs],
          'answers':[q['answer'] for q in qs]}
    done=client.post('/api/attempts',json=body,headers=hdr())
    assert done.status_code==200 and done.json()['score']==10
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
    answers=[(qs[0]['answer']+1)%4]+[q['answer'] for q in qs[1:]]
    full={'lesson_id':'eng_l1','question_ids':[q['id'] for q in qs],'answers':answers}
    done=client.post('/api/attempts',json=full,headers=hdr())
    assert done.status_code==200 and done.json()['score']==9
    review=client.get('/api/review/eng_l1',headers=hdr()).json()
    assert len(review['questions'])==1
    retry={'lesson_id':'eng_l1','question_ids':[qs[0]['id']], 'answers':[qs[0]['answer']]}
    result=client.post('/api/attempts',json=retry,headers=hdr())
    assert result.status_code==200 and result.json()['score']==1
    assert client.get('/api/progress',headers=hdr()).json()['latest'][0]['total']==10


def test_no_supplementary_data_or_quiz(client):
    client.post('/api/consent',headers=hdr())
    lesson=client.get('/api/lessons/bio_l1',headers=hdr()).json()
    assert 'supplement_sections' not in lesson
    assert 'supplement_questions' not in lesson
    assert 'sammu_books' not in lesson
    required=main.CATALOG['subjects'][4]['lessons'][0]['questions']
    response=client.post('/api/attempts',json={
        'lesson_id':'bio_l1',
        'question_ids':[q['id'] for q in required],
        'answers':[q['answer'] for q in required],
        'category':'supplementary'
    },headers=hdr())
    assert response.status_code==409


def test_latin_subject_and_poster_in_authenticated_lesson(client):
    assert client.post('/api/consent',headers=hdr()).status_code==200
    catalog=client.get('/api/catalog',headers=hdr()).json()
    latin=next(s for s in catalog['subjects'] if s['id']=='lotin_tili_tibbiy_terminologiya')
    assert len(latin['lessons'])==15
    first=client.get('/api/lessons/latin_a1',headers=hdr()).json()
    assert first['subject_id']=='lotin_tili_tibbiy_terminologiya'
    assert len(first['alphabet'])==25
    assert first['alphabet'][3]['term']=='Dens'
    assert 'teacher_materials' not in first
    assert first['questions'][0]['q']
    assert client.get('/api/lessons/latin_a1').status_code==401
    later=client.get('/api/lessons/latin_a15',headers=hdr()).json()
    assert later['sections'] and later['questions']
    assert len(later['questions'])==5


def test_public_free_telegram_auth_consent_and_isolation(client, monkeypatch):
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    outsider=UID+123
    outsider_headers=hdr(sign(uid=outsider))
    # Public means real signed Telegram users, not anonymous web visitors.
    assert client.get('/api/me').status_code==401
    assert client.get('/api/me', headers=hdr(sign(uid=outsider, now=int(time.time())-4000))).status_code==401
    assert client.get('/api/me',headers=outsider_headers).status_code==200
    assert client.get('/api/me',headers=outsider_headers).json()['is_admin'] is False
    assert client.get('/api/catalog',headers=outsider_headers).status_code==403
    assert client.post('/api/consent',headers=outsider_headers).status_code==200
    assert client.get('/api/catalog',headers=outsider_headers).status_code==200
    assert client.get('/api/lessons/eng_l1',headers=outsider_headers).status_code==200
    assert client.get('/api/progress',headers=outsider_headers).json()['attempts_count']==0
    assert client.post('/api/consent',headers=hdr()).status_code==200
    questions=main.CATALOG['subjects'][3]['lessons'][0]['questions']
    payload={'lesson_id':'eng_l1','question_ids':[q['id'] for q in questions],
             'answers':[q['answer'] for q in questions]}
    assert client.post('/api/attempts',json=payload,headers=outsider_headers).status_code==200
    assert client.get('/api/progress',headers=outsider_headers).json()['attempts_count']==1
    assert client.get('/api/progress',headers=hdr()).json()['attempts_count']==0
    assert client.get('/api/health').json()['free_public'] is True
    assert client.delete('/api/me',headers=outsider_headers).status_code==200
    assert client.get('/api/catalog',headers=outsider_headers).status_code==403


def test_public_free_does_not_unlock_paid_ai(client, monkeypatch):
    from app import tutor
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    monkeypatch.setenv('AI_ENABLED','1')
    monkeypatch.setenv('OPENAI_API_KEY','test-only-no-real-call')
    newcomer=UID+555
    headers=hdr(sign(uid=newcomer))
    client.post('/api/consent',headers=headers)
    status=client.get('/api/tutor/status',headers=headers)
    assert status.status_code==200
    assert status.json()['enabled'] is False and status.json()['remaining']==0
    assert client.post('/api/tutor/consent',headers=headers).status_code==403
    assert client.post('/api/tutor/ask',headers=headers,json={
        'lesson_id':'eng_l1','question':'Tish anatomiyasi nima?'}).status_code==403
    assert client.post('/api/tutor/lesson',headers=headers,json={
        'lesson_id':'eng_l1','question':'Tish anatomiyasi nima?'}).status_code==200


def test_free_rate_limits_per_user_and_action(client, monkeypatch):
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    user_headers=hdr(sign(uid=UID+300))
    client.post('/api/consent',headers=user_headers)
    payload={'lesson_id':'eng_l1','question':'What is the tooth?'}
    for _ in range(12):
        assert client.post('/api/tutor/lesson',headers=user_headers,json=payload).status_code==200
    assert client.post('/api/tutor/lesson',headers=user_headers,json=payload).status_code==429
    # Other users and other actions have separate quotas.
    client.post('/api/consent',headers=hdr())
    assert client.post('/api/tutor/lesson',headers=hdr(),json=payload).status_code==200
    assert client.get('/api/catalog',headers=user_headers).status_code==200


def test_approval_gate_pending_approved_revoked_and_persistent_progress(client,monkeypatch):
    from app.store import Store
    import tempfile
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    monkeypatch.setenv('ACCESS_APPROVAL_ENABLED','1')
    newcomer=UID+998
    headers=hdr(sign(uid=newcomer))
    assert client.get('/api/me',headers=headers).json()['access_status']=='not_requested'
    assert client.get('/api/catalog',headers=headers).status_code==403
    assert client.post('/api/consent',headers=headers).status_code==403
    assert client.post('/api/tutor/lesson',headers=headers,json={
      'lesson_id':'eng_l1','question':'What is a tooth?'}).status_code==403
    assert client.get('/api/catalog').status_code==401
    assert client.get('/api/catalog',headers=hdr(sign(uid=newcomer,now=int(time.time())-4000))).status_code==401
    status,created=main.STORE.request_access(newcomer)
    assert status=='pending' and created is True
    assert main.STORE.request_access(newcomer)==('pending',False)
    assert client.get('/api/catalog',headers=headers).status_code==403
    assert main.STORE.review_access(newcomer,'approved',UID)=='approved'
    assert client.post('/api/consent',headers=headers).status_code==200
    assert client.get('/api/catalog',headers=headers).status_code==200
    questions=main.CATALOG['subjects'][3]['lessons'][0]['questions']
    payload={'lesson_id':'eng_l1','question_ids':[q['id'] for q in questions],
             'answers':[q['answer'] for q in questions]}
    assert client.post('/api/attempts',headers=headers,json=payload).status_code==200
    assert client.get('/api/progress',headers=headers).json()['attempts_count']==1
    main.STORE.review_access(newcomer,'revoked',UID)
    assert client.get('/api/catalog',headers=headers).status_code==403
    assert client.get('/api/progress',headers=headers).status_code==403
    main.STORE.review_access(newcomer,'approved',UID)
    assert client.get('/api/progress',headers=headers).json()['attempts_count']==1
    assert client.get('/api/catalog',headers=hdr()).status_code==403
    # A user who deletes their account also deletes their registration.
    assert client.delete('/api/me',headers=headers).status_code==200
    assert main.STORE.access_status(newcomer)=='not_requested'
    assert client.get('/api/catalog',headers=headers).status_code==403


def test_approval_gate_admin_bypass_still_requires_privacy(client,monkeypatch):
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    monkeypatch.setenv('ACCESS_APPROVAL_ENABLED','1')
    monkeypatch.setattr(main,'ALLOWED_IDS',{UID})
    assert client.get('/api/me',headers=hdr()).json()['access_status']=='approved'
    assert client.get('/api/catalog',headers=hdr()).status_code==403
    assert client.post('/api/consent',headers=hdr()).status_code==200
    assert client.get('/api/catalog',headers=hdr()).status_code==200


def test_access_requests_persist_without_deleting_old_records(client,monkeypatch):
    monkeypatch.setenv('PUBLIC_FREE_ENABLED','1')
    monkeypatch.setenv('ACCESS_APPROVAL_ENABLED','1')
    other=UID+777
    main.STORE.request_access(other)
    assert main.STORE.access_status(other)=='pending'
    from app.store import Store
    reopened=Store(main.STORE.path)
    assert reopened.access_status(other)=='pending'
    reopened.review_access(other,'rejected',UID)
    assert reopened.access_status(other)=='rejected'
    assert other not in reopened.pending_access()
    assert reopened.request_access(other)==('rejected',False)
