from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import AuthError, verify_init_data
from .core import load_catalog, find_lesson, public_question, grade
from .store import Store
from .study_plan import build_study_plan
from .plans import plans_catalog
from . import tutor
from .lesson_helper import prepare_answer
from .telegram_gateway import router as telegram_router, configure_telegram

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
CATALOG = load_catalog(ROOT / 'content' / 'lessons.json')
STORE = Store(os.getenv('DATABASE_PATH', str(ROOT / 'data' / 'medstudy.db')))
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ALLOWED_IDS = {int(x.strip()) for x in os.getenv('ALLOWED_USER_IDS', '').replace(';', ',').split(',') if x.strip()}
DEV_PREVIEW = os.getenv('DEV_PREVIEW', '0') == '1'

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEV_PREVIEW and os.getenv('RAILWAY_ENVIRONMENT_ID'):
        raise RuntimeError('DEV_PREVIEW=1 is not allowed on Railway')
    await configure_telegram()
    yield

app = FastAPI(title='MedStudy AI Mini App', docs_url=None, redoc_url=None, lifespan=lifespan)
app.include_router(telegram_router)
app.mount('/static', StaticFiles(directory=ROOT / 'app' / 'static'), name='static')

@app.get('/')
def index():
    return FileResponse(ROOT / 'app' / 'static' / 'index.html', headers={'Cache-Control':'no-store'})

@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '0.5.0-draft', 'draft': True}


def current_user(request: Request, x_telegram_init_data: Annotated[str | None, Header()] = None) -> int:
    # Local demo for browser testing. NEVER expose DEV_PREVIEW on a public server.
    if DEV_PREVIEW and request.client and request.client.host in {'127.0.0.1', '::1'} and request.headers.get('x-dev-preview') == 'local-only' and request.headers.get('host', '').split(':')[0] in {'localhost', '127.0.0.1'}:
        return 999999991
    try:
        uid = verify_init_data(x_telegram_init_data or '', BOT_TOKEN)
    except (AuthError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if not ALLOWED_IDS or uid not in ALLOWED_IDS:
        raise HTTPException(status_code=403, detail='Yopiq sinov. Administrator ruxsati kerak.')
    return uid


def consent_required(uid: int = Depends(current_user)) -> int:
    if not STORE.has_consent(uid):
        raise HTTPException(status_code=403, detail='Avval maxfiylik shartlariga rozilik bering')
    return uid

@app.get('/api/me')
def me(uid: int = Depends(current_user)):
    return {'consented': STORE.has_consent(uid), 'test_mode': True}

@app.post('/api/consent')
def consent(uid: int = Depends(current_user)):
    STORE.consent(uid)
    return {'consented': True}

@app.delete('/api/me')
def delete_me(uid: int = Depends(current_user)):
    STORE.delete_user(uid)
    return {'deleted': True}

@app.get('/api/catalog')
def catalog(uid: int = Depends(consent_required)):
    return {'status': 'DRAFT', 'subjects': [
        {'id': s['id'], 'title': s['title'], 'lessons': [
            {'id': l['id'], 'title': l['title'], 'section_count':len(l['sections']), 'question_count':len(l['questions']), 'teacher_material_count':len(l.get('teacher_materials', [])), 'supplement_count':len(l.get('supplementary', []))}
            for l in s['lessons']]} for s in CATALOG['subjects']
    ]}

@app.get('/api/lessons/{lesson_id}')
def lesson(lesson_id: str, uid: int = Depends(consent_required)):
    found = find_lesson(CATALOG, lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    subject, l = found
    return {'subject_id':subject['id'], 'subject_title':subject['title'], 'id':l['id'], 'title':l['title'],
            'sections':l['sections'], 'teacher_materials':l.get('teacher_materials', []), 'supplementary':l.get('supplementary', []), 'sources':l.get('sources',[]),
            'question_count':len(l['questions']), 'questions':[public_question(q) for q in l['questions']],
            'supplement_sections':l.get('supplement_sections', []),
            'supplement_question_count':len(l.get('supplement_questions', [])),
            'supplement_questions':[public_question(q) for q in l.get('supplement_questions', [])]}

class AttemptBody(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)
    question_ids: list[str] = Field(min_length=1, max_length=100)
    answers: list[int] = Field(min_length=1, max_length=100)
    category: str = Field(default='required', pattern='^(required|supplementary)
def submit(data: AttemptBody, uid: int = Depends(consent_required)):
    found = find_lesson(CATALOG, data.lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    is_supplement = data.category == 'supplementary'
    questions = (found[1].get('supplement_questions', []) if is_supplement
                 else found[1]['questions'])
    if not questions:
        raise HTTPException(409, 'Bu bo‘limda tasdiqlangan test hozircha yo‘q')
    lookup = {q['id']: q for q in questions}
    full_ids = [q['id'] for q in questions]
    wrong_ids = (STORE.latest_wrong_ids(uid, data.lesson_id)
                 if not is_supplement else [])
    if data.question_ids == full_ids:
        chosen_questions = questions
        mode = 'supplementary' if is_supplement else 'full'
    elif not is_supplement and wrong_ids and data.question_ids == wrong_ids:
        chosen_questions = [lookup[qid] for qid in wrong_ids if qid in lookup]
        if len(chosen_questions) != len(wrong_ids):
            raise HTTPException(400, 'Savollar ro‘yxati mos emas')
        mode = 'retry'
    else:
        raise HTTPException(400, 'Savollar ro‘yxati mos emas')
    try:
        score, details = grade(chosen_questions, data.answers)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    # Retrying a subset creates a new attempt for that subset, not a full test score.
    STORE.save_attempt(uid, data.lesson_id, score, details, mode=mode)
    return {'score':score, 'total':len(details), 'mode':mode,'percent':round(score*100/len(details)),
            'details':details}

@app.get('/api/progress')
def progress(uid: int = Depends(consent_required)):
    data = STORE.latest(uid)
    return {'attempts_count':STORE.attempt_count(uid), 'latest':[
        {**row,'title':find_lesson(CATALOG,row['lesson_id'])[1]['title']
         if find_lesson(CATALOG,row['lesson_id']) else row['lesson_id'],
         'percent':round(row['score']*100/row['total'])}
        for row in data]}

@app.get('/api/history')
def attempt_history(uid: int = Depends(consent_required), limit: int = 20):
    rows = STORE.attempt_history(uid, limit)
    return {'items': [
        {**row,
         'title': (find_lesson(CATALOG, row['lesson_id']) or
                   (None, {'title': row['lesson_id']}))[1]['title'],
         'percent': round(row['score'] * 100 / row['total']) if row['total'] else 0}
        for row in rows
    ]}


@app.get('/api/plans')
def preview_plans(uid: int = Depends(consent_required)):
    return plans_catalog()


@app.get('/api/study-plan')
def study_plan(uid: int = Depends(consent_required)):
    latest = STORE.latest(uid)
    wrong_counts = {
        lesson['id']: len(STORE.latest_wrong_ids(uid, lesson['id']))
        for subject in CATALOG['subjects']
        for lesson in subject['lessons']
    }
    return build_study_plan(CATALOG, latest, wrong_counts)


@app.get('/api/review/{lesson_id}')
def review(lesson_id: str,uid: int = Depends(consent_required)):
    found = find_lesson(CATALOG,lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    wrong = STORE.latest_wrong_ids(uid,lesson_id)
    qmap = {q['id']:q for q in found[1]['questions']}
    return {'lesson_id':lesson_id,'questions':[public_question(qmap[q]) for q in wrong if q in qmap]}


# AI Tutor is a strictly opt-in pilot. No API call occurs without both existing
# Telegram-authenticated app consent and separate consent for OpenAI processing.

def _bounded_positive(name: str, default: int, cap: int) -> int:
    try:
        return max(1, min(int(os.getenv(name, str(default))), cap))
    except ValueError:
        return default


@app.get('/api/tutor/status')
def tutor_status(uid: int = Depends(consent_required)):
    limit = _bounded_positive('AI_DAILY_LIMIT', 5, 20)
    used = STORE.ai_usage(uid)
    return {'enabled': tutor.enabled(), 'consented': STORE.has_ai_consent(uid),
            'used': used, 'limit': limit, 'remaining': max(0, limit-used)}


class LessonHelpQuestion(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=5, max_length=500)
    mode: str = Field(default="explain", pattern="^(explain|example|recall)$")


@app.post('/api/tutor/lesson')
def free_lesson_help(data: LessonHelpQuestion, uid: int = Depends(consent_required)):
    """Private free study helper: no OpenAI call and no transcripts saved."""
    found = find_lesson(CATALOG, data.lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    if not found[1]['sections']:
        raise HTTPException(409, 'Mavzu bo‘yiça o‘qituvçi konspekti hozirça kiritilmagan')
    if not data.question.strip():
        raise HTTPException(422, 'Savol bo‘sh bo‘lishi mumkin emas')
    return prepare_answer(found[1], data.question, data.mode)


@app.post('/api/tutor/consent')
def tutor_consent(uid: int = Depends(consent_required)):
    STORE.consent_ai(uid)
    return {'consented': True}


@app.delete('/api/tutor/consent')
def tutor_revoke_consent(uid: int = Depends(consent_required)):
    STORE.revoke_ai_consent(uid)
    return {'consented': False}


class TutorQuestion(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=5, max_length=500)
    mode: str = Field(default="explain", pattern="^(explain|example|recall)$")


@app.post('/api/tutor/ask')
async def tutor_ask(data: TutorQuestion, uid: int = Depends(consent_required)):
    if not tutor.enabled():
        raise HTTPException(503, 'AI hozir o‘chirilgan. Administrator sozlamalarini tekshirsin.')
    if not STORE.has_ai_consent(uid):
        raise HTTPException(403, 'OpenAI ga savol yuborish uchun alohida rozilik kerak')
    lesson_found = find_lesson(CATALOG, data.lesson_id)
    if not lesson_found:
        raise HTTPException(404, 'Mavzu topilmadi')
    if not lesson_found[1]['sections']:
        raise HTTPException(409, 'Dars uchun tasdiqlangan manba hali yo‘q')
    if not data.question.strip():
        raise HTTPException(422, 'Savol bo‘sh bo‘lishi mumkin emas')
    # Reject obvious personally identifying data to reduce accidental exposure.
    import re
    if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\+?998[\d -]{8,}|sk-[a-zA-Z0-9_-]{12,}', data.question):
        raise HTTPException(422, 'Savoldan telefon, email yoki maxfiy kalitni olib tashlang')
    per_user = _bounded_positive('AI_DAILY_LIMIT', 5, 20)
    globally = _bounded_positive('AI_GLOBAL_DAILY_LIMIT', 40, 1000)
    try:
        used = STORE.reserve_ai_request(uid, per_user, globally)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(429 if isinstance(exc, ValueError) else 403, str(exc)) from exc
    try:
        result = await tutor.generate_answer(lesson_found[1], data.question.strip(), mode=data.mode)
    except tutor.TutorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {**result, 'remaining': max(0, per_user-used),
            'notice': 'AI javobi tekshirilmagan o‘quv materialiga asoslangan. Klinik maslahat emas.'}
)

@app.post('/api/attempts')
def submit(data: AttemptBody, uid: int = Depends(consent_required)):
    found = find_lesson(CATALOG, data.lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    questions = found[1]['questions']
    if not questions:
        raise HTTPException(409, 'O‘qituvçi materiali bo‘yiça test hozirça yo‘q')
    lookup = {q['id']:q for q in questions}
    full_ids = [q['id'] for q in questions]
    wrong_ids = STORE.latest_wrong_ids(uid, data.lesson_id)
    # Allowed modes: all questions, or exactly the questions wrong on the latest attempt.
    if data.question_ids == full_ids:
        chosen_questions = questions
        mode = 'full'
    elif wrong_ids and data.question_ids == wrong_ids:
        chosen_questions = [lookup[qid] for qid in wrong_ids]
        mode = 'retry'
    else:
        raise HTTPException(400, 'Savollar ro‘yxati mos emas')
    try:
        score, details = grade(chosen_questions, data.answers)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    # Retrying a subset creates a new attempt for that subset, not a full test score.
    STORE.save_attempt(uid, data.lesson_id, score, details, mode=mode)
    return {'score':score, 'total':len(details), 'mode':mode,'percent':round(score*100/len(details)),
            'details':details}

@app.get('/api/progress')
def progress(uid: int = Depends(consent_required)):
    data = STORE.latest(uid)
    return {'attempts_count':STORE.attempt_count(uid), 'latest':[
        {**row,'title':find_lesson(CATALOG,row['lesson_id'])[1]['title']
         if find_lesson(CATALOG,row['lesson_id']) else row['lesson_id'],
         'percent':round(row['score']*100/row['total'])}
        for row in data]}

@app.get('/api/history')
def attempt_history(uid: int = Depends(consent_required), limit: int = 20):
    rows = STORE.attempt_history(uid, limit)
    return {'items': [
        {**row,
         'title': (find_lesson(CATALOG, row['lesson_id']) or
                   (None, {'title': row['lesson_id']}))[1]['title'],
         'percent': round(row['score'] * 100 / row['total']) if row['total'] else 0}
        for row in rows
    ]}


@app.get('/api/plans')
def preview_plans(uid: int = Depends(consent_required)):
    return plans_catalog()


@app.get('/api/study-plan')
def study_plan(uid: int = Depends(consent_required)):
    latest = STORE.latest(uid)
    wrong_counts = {
        lesson['id']: len(STORE.latest_wrong_ids(uid, lesson['id']))
        for subject in CATALOG['subjects']
        for lesson in subject['lessons']
    }
    return build_study_plan(CATALOG, latest, wrong_counts)


@app.get('/api/review/{lesson_id}')
def review(lesson_id: str,uid: int = Depends(consent_required)):
    found = find_lesson(CATALOG,lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    wrong = STORE.latest_wrong_ids(uid,lesson_id)
    qmap = {q['id']:q for q in found[1]['questions']}
    return {'lesson_id':lesson_id,'questions':[public_question(qmap[q]) for q in wrong if q in qmap]}


# AI Tutor is a strictly opt-in pilot. No API call occurs without both existing
# Telegram-authenticated app consent and separate consent for OpenAI processing.

def _bounded_positive(name: str, default: int, cap: int) -> int:
    try:
        return max(1, min(int(os.getenv(name, str(default))), cap))
    except ValueError:
        return default


@app.get('/api/tutor/status')
def tutor_status(uid: int = Depends(consent_required)):
    limit = _bounded_positive('AI_DAILY_LIMIT', 5, 20)
    used = STORE.ai_usage(uid)
    return {'enabled': tutor.enabled(), 'consented': STORE.has_ai_consent(uid),
            'used': used, 'limit': limit, 'remaining': max(0, limit-used)}


class LessonHelpQuestion(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=5, max_length=500)
    mode: str = Field(default="explain", pattern="^(explain|example|recall)$")


@app.post('/api/tutor/lesson')
def free_lesson_help(data: LessonHelpQuestion, uid: int = Depends(consent_required)):
    """Private free study helper: no OpenAI call and no transcripts saved."""
    found = find_lesson(CATALOG, data.lesson_id)
    if not found:
        raise HTTPException(404, 'Mavzu topilmadi')
    if not found[1]['sections']:
        raise HTTPException(409, 'Mavzu bo‘yiça o‘qituvçi konspekti hozirça kiritilmagan')
    if not data.question.strip():
        raise HTTPException(422, 'Savol bo‘sh bo‘lishi mumkin emas')
    return prepare_answer(found[1], data.question, data.mode)


@app.post('/api/tutor/consent')
def tutor_consent(uid: int = Depends(consent_required)):
    STORE.consent_ai(uid)
    return {'consented': True}


@app.delete('/api/tutor/consent')
def tutor_revoke_consent(uid: int = Depends(consent_required)):
    STORE.revoke_ai_consent(uid)
    return {'consented': False}


class TutorQuestion(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=5, max_length=500)
    mode: str = Field(default="explain", pattern="^(explain|example|recall)$")


@app.post('/api/tutor/ask')
async def tutor_ask(data: TutorQuestion, uid: int = Depends(consent_required)):
    if not tutor.enabled():
        raise HTTPException(503, 'AI hozir o‘chirilgan. Administrator sozlamalarini tekshirsin.')
    if not STORE.has_ai_consent(uid):
        raise HTTPException(403, 'OpenAI ga savol yuborish uchun alohida rozilik kerak')
    lesson_found = find_lesson(CATALOG, data.lesson_id)
    if not lesson_found:
        raise HTTPException(404, 'Mavzu topilmadi')
    if not lesson_found[1]['sections']:
        raise HTTPException(409, 'Dars uchun tasdiqlangan manba hali yo‘q')
    if not data.question.strip():
        raise HTTPException(422, 'Savol bo‘sh bo‘lishi mumkin emas')
    # Reject obvious personally identifying data to reduce accidental exposure.
    import re
    if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\+?998[\d -]{8,}|sk-[a-zA-Z0-9_-]{12,}', data.question):
        raise HTTPException(422, 'Savoldan telefon, email yoki maxfiy kalitni olib tashlang')
    per_user = _bounded_positive('AI_DAILY_LIMIT', 5, 20)
    globally = _bounded_positive('AI_GLOBAL_DAILY_LIMIT', 40, 1000)
    try:
        used = STORE.reserve_ai_request(uid, per_user, globally)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(429 if isinstance(exc, ValueError) else 403, str(exc)) from exc
    try:
        result = await tutor.generate_answer(lesson_found[1], data.question.strip(), mode=data.mode)
    except tutor.TutorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {**result, 'remaining': max(0, per_user-used),
            'notice': 'AI javobi tekshirilmagan o‘quv materialiga asoslangan. Klinik maslahat emas.'}
