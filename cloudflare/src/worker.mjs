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
  // Other endpoints, especially quiz scoring & student history, must be
  // migrated and tested BEFORE we enable student traffic or switch Railway.
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
