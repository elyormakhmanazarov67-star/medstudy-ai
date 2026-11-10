/* MedStudy AI Cloudflare Free preview: no live webhook and no quiz writes.
 * This pilot deliberately fails closed for missing secrets, missing D1, and
 * missing approvals. It never copies private Railway data automatically.
 */
import catalog from '../generated/catalog.mjs';

const reply = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store', 'x-content-type-options': 'nosniff' }
});
const error = (status, detail) => reply({ detail }, status);
const hex = bytes => [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2, '0')).join('');

async function hmac(keyBytes, message) {
  const key = await crypto.subtle.importKey(
    'raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  return crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
}
function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}
export async function verifyTelegramInitData(raw, token, now = Date.now()) {
  if (!raw || !token || raw.length > 16384) throw new Error('Telegram ma’lumotlari yo‘q');
  const pairs = [...new URLSearchParams(raw).entries()];
  if (pairs.length !== new Set(pairs.map(([name]) => name)).size) throw new Error('Takroriy maydon');
  const data = Object.fromEntries(pairs);
  const supplied = data.hash;
  if (!/^[a-fA-F0-9]{64}$/.test(supplied || '')) throw new Error('Imzo mavjud emas');
  delete data.hash;
  const check = Object.entries(data).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([k, v]) => k + '=' + v).join('\n');
  const encoder = new TextEncoder();
  const key = await hmac(encoder.encode('WebAppData'), token);
  const actual = hex(await hmac(key, check));
  if (!timingSafeEqual(actual, supplied.toLowerCase())) throw new Error('Telegram tasdiqlanmadi');
  const authDate = Number(data.auth_date);
  let user;
  try { user = JSON.parse(data.user); } catch { throw new Error('Foydalanuvchi ma’lumoti topilmadi'); }
  if (!Number.isSafeInteger(user?.id) || user.id <= 0 || !Number.isSafeInteger(authDate)) {
    throw new Error('Foydalanuvchi ma’lumoti topilmadi');
  }
  const seconds = Math.floor(now / 1000);
  if (authDate < seconds - 3600 || authDate > seconds + 30) throw new Error('Kirish muddati tugagan');
  return user.id;
}

function admins(env) {
  const raw = env.ADMIN_USER_IDS || env.ALLOWED_USER_IDS || '';
  return new Set(raw.split(/[,;]/).map(x => x.trim()).filter(Boolean).map(Number));
}
function allowlist(env) {
  return new Set((env.ALLOWED_USER_IDS || '').split(/[,;]/).map(x => x.trim())
    .filter(Boolean).map(Number));
}
async function signedUser(request, env) {
  if (!env.BOT_TOKEN) return { failure: error(503, 'Test Telegram tokeni sozlanmagan') };
  let uid;
  try { uid = await verifyTelegramInitData(request.headers.get('X-Telegram-Init-Data') || '', env.BOT_TOKEN); }
  catch { return { failure: error(401, 'Telegram imzosi haqiqiy emas') }; }
  if (!env.DB) return { failure: error(503, 'D1 ma’lumotlar bazasi ulanmagan') };
  const admin = admins(env).has(uid);
  const status = (await env.DB.prepare('SELECT status FROM access_requests WHERE user_id=?')
    .bind(uid).first())?.status || 'not_requested';
  const approvalRequired = env.ACCESS_APPROVAL_ENABLED === '1';
  const publicFree = env.PUBLIC_FREE_ENABLED === '1';
  if (!publicFree && !admin && !allowlist(env).has(uid) &&
      !(approvalRequired && status === 'approved')) {
    return { failure: error(403, 'Yopiq sinov. Administrator ruxsati kerak.') };
  }
  return { uid, admin, status, approvalRequired, publicFree };
}
async function approvedUser(request, env) {
  const session = await signedUser(request, env);
  if (session.failure) return session;
  if (session.approvalRequired && !session.admin && session.status !== 'approved') {
    return { failure: error(403, 'Mini App uchun administrator tasdig‘i kerak') };
  }
  return session;
}
async function consentedUser(request, env) {
  const session = await approvedUser(request, env);
  if (session.failure) return session;
  const hasConsent = await env.DB.prepare('SELECT 1 AS accepted FROM users WHERE user_id=?')
    .bind(session.uid).first();
  if (!hasConsent) return { failure: error(403, 'Avval maxfiylik shartlariga rozilik bering') };
  return session;
}

function publicQuestion(q) {
  return { id: q.id, q: q.q, options: q.options };
}
// Quiz and progress logic must match app/main.py, but this Worker remains a
// preview until the bot, admin flow and final Railway migration are verified.
function lessonById(id) {
  for (const subject of catalog.subjects) {
    const lesson = subject.lessons.find(l => l.id === id);
    if (lesson) return { subject, lesson };
  }
  return null;
}

function validID(text) {
  return typeof text === 'string' && /^[a-zA-Z0-9_-]{1,100}$/.test(text);
}

async function wrongQuestionIds(db, uid, lessonId) {
  const latest = await db.prepare(
    "SELECT id FROM attempts WHERE user_id=? AND lesson_id=? AND mode IN ('full','retry') ORDER BY id DESC LIMIT 1"
  ).bind(uid, lessonId).first();
  if (!latest) return [];
  const result = await db.prepare(
    'SELECT question_id FROM answers WHERE attempt_id=? AND correct=0 ORDER BY id'
  ).bind(latest.id).all();
  return (result.results || []).map(row => row.question_id);
}

async function reserveRateLimit(db, uid, action, maxPerMinute) {
  const minute = new Date().toISOString().slice(0, 16);
  const updated = await db.prepare(
    "INSERT INTO rate_limits (user_id,action,window_utc_minute,requests) VALUES (?,?,?,1) " +
    "ON CONFLICT(user_id,action) DO UPDATE SET " +
    "requests=CASE WHEN rate_limits.window_utc_minute=excluded.window_utc_minute " +
    "THEN rate_limits.requests+1 ELSE 1 END, window_utc_minute=excluded.window_utc_minute " +
    "WHERE rate_limits.window_utc_minute<>excluded.window_utc_minute OR rate_limits.requests<?"
  ).bind(uid, action, minute, maxPerMinute).run();
  return (updated.meta?.changes || 0) > 0;
}

async function submitAttempt(request, env) {
  const session = await consentedUser(request, env);
  if (session.failure) return session.failure;

  const length = Number(request.headers.get('content-length') || 0);
  if (length > 16_384) return error(413, 'So‘rov hajmi katta');
  let input;
  try {
    const body = await request.text();
    if (body.length > 16_384) return error(413, 'So‘rov hajmi katta');
    input = JSON.parse(body);
  } catch { return error(400, 'Test ma’lumotlari noto‘g‘ri'); }

  const lessonId = input?.lesson_id;
  const ids = input?.question_ids, answers = input?.answers;
  const category = input?.category ?? 'required';
  if (!validID(lessonId) || !['required', 'supplementary'].includes(category) ||
    !Array.isArray(ids) || !Array.isArray(answers) || ids.length < 1 ||
    ids.length > 100 || answers.length !== ids.length ||
    !ids.every(validID) ||
    !answers.every(x => Number.isInteger(x) && x >= 0 && x <= 3)) {
    return error(422, 'Test javoblari noto‘g‘ri');
  }
  const found = lessonById(lessonId);
  if (!found) return error(404, 'Mavzu topilmadi');

  const supplementary = category === 'supplementary';
  const questions = supplementary ? (found.lesson.supplement_questions || []) : found.lesson.questions;
  if (!questions.length) return error(409, 'Bu bo‘lim uchun test hali tayyorlanmagan');
  const fullIds = questions.map(q => q.id);
  let mode, chosenQuestions;
  const same = (left, right) => left.length === right.length &&
    left.every((value, index) => value === right[index]);
  if (same(ids, fullIds)) {
    mode = supplementary ? 'supplementary' : 'full';
    chosenQuestions = questions;
  } else if (!supplementary) {
    const wrong = await wrongQuestionIds(env.DB, session.uid, lessonId);
    if (!wrong.length || !same(ids, wrong)) return error(400, 'Savollar ro‘yxati mos emas');
    const lookup = new Map(questions.map(q => [q.id, q]));
    chosenQuestions = wrong.map(id => lookup.get(id));
    if (chosenQuestions.some(q => !q)) return error(400, 'Savollar ro‘yxati mos emas');
    mode = 'retry';
  } else {
    return error(400, 'Savollar ro‘yxati mos emas');
  }
  const details = chosenQuestions.map((question, index) => ({
    question_id: question.id,
    chosen: answers[index],
    answer: question.answer,
    correct: answers[index] === question.answer,
    explanation: question.explanation,
  }));
  const score = details.filter(item => item.correct).length;
  if (!await reserveRateLimit(env.DB, session.uid, 'quiz', 20)) {
    return error(429, 'Juda ko‘p so‘rov yuborildi. Bir daqiqadan so‘ng qayta urinib ko‘ring.');
  }

  // Use a unique client-generated integer ID so all statements can run in one
  // atomic D1 batch, without relying on last_insert_rowid() across statements.
  const random = crypto.getRandomValues(new Uint32Array(2));
  const attemptId = Number(
    ((BigInt(random[0]) << 32n) | BigInt(random[1])) & ((1n << 52n) - 1n)
  ) + 1;
  const createdAt = new Date().toISOString();
  const statements = [
    env.DB.prepare(
      'INSERT INTO attempts(id,user_id,lesson_id,score,total,mode,created_at) VALUES (?,?,?,?,?,?,?)'
    ).bind(attemptId, session.uid, lessonId, score, details.length, mode, createdAt),
    ...details.map(item => env.DB.prepare(
      'INSERT INTO answers(attempt_id,question_id,chosen,correct) VALUES (?,?,?,?)'
    ).bind(attemptId, item.question_id, item.chosen, Number(item.correct))),
  ];
  // D1 batch executes the prepared statements in a single transaction.
  await env.DB.batch(statements);
  return reply({ score, total: details.length, mode,
    percent: Math.round(score * 100 / details.length), details });
}

async function studentProgress(request, env, kind) {
  const session = await consentedUser(request, env);
  if (session.failure) return session.failure;
  const uid = session.uid;
  if (kind === 'progress') {
    const [count, recent] = await Promise.all([
      env.DB.prepare('SELECT COUNT(*) AS n FROM attempts WHERE user_id=?').bind(uid).first(),
      env.DB.prepare(
        "SELECT a.lesson_id,a.score,a.total,a.created_at FROM attempts a " +
        "JOIN (SELECT lesson_id,MAX(id) AS attempt_id FROM attempts WHERE user_id=? AND mode='full' GROUP BY lesson_id) x " +
        "ON a.id=x.attempt_id ORDER BY a.lesson_id"
      ).bind(uid).all(),
    ]);
    return reply({ attempts_count: count?.n || 0,
      latest: (recent.results || []).map(item => ({
        ...item,
        title: lessonById(item.lesson_id)?.lesson.title || item.lesson_id,
        percent: item.total ? Math.round(item.score * 100 / item.total) : 0,
      }))
    });
  }
  if (kind === 'history') {
    const rawLimit = new URL(request.url).searchParams.get('limit');
    const limit = Math.max(1, Math.min(50, Number.parseInt(rawLimit || '20', 10) || 20));
    const history = await env.DB.prepare(
      'SELECT lesson_id,score,total,mode,created_at FROM attempts WHERE user_id=? ORDER BY id DESC LIMIT ?'
    ).bind(uid, limit).all();
    return reply({ items: (history.results || []).map(item => ({
      ...item,
      title: lessonById(item.lesson_id)?.lesson.title || item.lesson_id,
      percent: item.total ? Math.round(item.score * 100 / item.total) : 0,
    })) });
  }
  return error(404, 'Not found');
}

async function reviewWrong(request, env, lessonId) {
  const session = await consentedUser(request, env);
  if (session.failure) return session.failure;
  const found = lessonById(lessonId);
  if (!found) return error(404, 'Mavzu topilmadi');
  const ids = await wrongQuestionIds(env.DB, session.uid, lessonId);
  const lookup = new Map(found.lesson.questions.map(q => [q.id, q]));
  return reply({ lesson_id: lessonId,
    questions: ids.map(id => lookup.get(id)).filter(Boolean).map(publicQuestion) });
}

export async function handleRequest(request, env) {
  const url = new URL(request.url), path = url.pathname;
  if (path === '/api/health' && request.method === 'GET') {
    return reply({ status: 'ok', version: catalog.version, provider: 'cloudflare-preview',
      migration_ready: false, approval_required: env.ACCESS_APPROVAL_ENABLED === '1' });
  }
  if (path.startsWith('/telegram') || path.startsWith('/bot/')) {
    return error(503, 'Telegram webhook hali ko‘chirilmagan');
  }
  if (!path.startsWith('/api/')) {
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return error(404, 'Not found');
  }
  if (request.method === 'OPTIONS') return error(405, 'Method not allowed');
  if (path === '/api/me' && request.method === 'GET') {
    const session = await signedUser(request, env);
    if (session.failure) return session.failure;
    const consent = await env.DB.prepare('SELECT 1 AS accepted FROM users WHERE user_id=?')
      .bind(session.uid).first();
    return reply({ consented: Boolean(consent), test_mode: !session.publicFree,
      free_public: session.publicFree, is_admin: session.admin,
      approval_required: session.approvalRequired,
      access_status: session.admin ? 'approved' : session.status });
  }
  if (path === '/api/consent' && request.method === 'POST') {
    const session = await approvedUser(request, env);
    if (session.failure) return session.failure;
    await env.DB.prepare('INSERT OR IGNORE INTO users (user_id,consented_at) VALUES (?,?)')
      .bind(session.uid, new Date().toISOString()).run();
    return reply({ consented: true });
  }
  if (path === '/api/catalog' && request.method === 'GET') {
    const session = await consentedUser(request, env);
    if (session.failure) return session.failure;
    return reply({ status: 'DRAFT', subjects: catalog.subjects.map(subject => ({
      id: subject.id, title: subject.title,
      lessons: subject.lessons.map(lesson => ({
        id: lesson.id, title: lesson.title,
        section_count: lesson.sections.length, question_count: lesson.questions.length
      }))
    })) });
  }
  if (path.startsWith('/api/lessons/') && request.method === 'GET') {
    const session = await consentedUser(request, env);
    if (session.failure) return session.failure;
    const id = decodeURIComponent(path.slice('/api/lessons/'.length));
    if (!/^[a-z0-9_-]{1,100}$/i.test(id)) return error(404, 'Mavzu topilmadi');
    for (const subject of catalog.subjects) {
      const lesson = subject.lessons.find(l => l.id === id);
      if (!lesson) continue;
      return reply({ subject_id: subject.id, subject_title: subject.title,
        id: lesson.id, title: lesson.title, sections: lesson.sections,
        alphabet: lesson.alphabet || [], sources: lesson.sources || [],
        question_count: lesson.questions.length,
        questions: lesson.questions.map(publicQuestion) });
    }
    return error(404, 'Mavzu topilmadi');
  }
  if (path === '/api/attempts' && request.method === 'POST') {
    return submitAttempt(request, env);
  }
  if (path === '/api/progress' && request.method === 'GET') {
    return studentProgress(request, env, 'progress');
  }
  if (path === '/api/history' && request.method === 'GET') {
    return studentProgress(request, env, 'history');
  }
  if (path.startsWith('/api/review/') && request.method === 'GET') {
    const id = decodeURIComponent(path.slice('/api/review/'.length));
    if (!validID(id)) return error(404, 'Mavzu topilmadi');
    return reviewWrong(request, env, id);
  }
  // Remaining endpoints, including bot commands, are still not implemented.
  return error(501, 'Ushbu funksiya Cloudflare sinov versiyasida hali tayyor emas');
}

export default {
  async fetch(request, env) {
    try { return await handleRequest(request, env); }
    catch (e) {
      // Don't leak SQL statements, Telegram initData or private tokens.
      return error(503, 'Sinov serverida vaqtinchalik xatolik');
    }
  }
};
