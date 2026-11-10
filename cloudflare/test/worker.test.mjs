import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, webcrypto } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { handleRequest, verifyTelegramInitData } from '../src/worker.mjs';

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const TOKEN = '111111:test-demo-token';
const UID = 902345612;
const domain = 'https://medstudy-free-preview.example';
function signedTelegram(uid = UID, now = Date.now()) {
  const p = new URLSearchParams();
  p.append('auth_date', String(Math.floor(now/1000)));
  p.append('user', JSON.stringify({ id: uid, first_name: 'Fake' }));
  const canonical = [...p.entries()].sort(([a],[b])=>a.localeCompare(b))
    .map(([k,v])=>k+'='+v).join('\n');
  const secret = createHmac('sha256','WebAppData').update(TOKEN).digest();
  const hash = createHmac('sha256',secret).update(canonical).digest('hex');
  p.append('hash',hash);
  return p.toString();
}
function request(path, method='GET', signed=true) {
  const headers = signed ? { 'X-Telegram-Init-Data': signedTelegram() } : {};
  return new Request(domain+path,{method,headers});
}
function fakeDb({ approved=true, consented=true }={}) {
  return {
    prepare(sql) {
      return {
        bind(...values) {
          return {
            async first() {
              if (sql.startsWith('SELECT status')) return approved ? {status:'approved'} : {status:'pending'};
              if (sql.startsWith('SELECT 1 AS accepted')) return consented ? {accepted:1} : null;
              throw new Error('Unexpected query: '+sql);
            },
            async run() { consented = true; return {success:true}; }
          };
        }
      };
    }
  };
}
function env(db) { return {
  DB: db, BOT_TOKEN: TOKEN,
  ACCESS_APPROVAL_ENABLED:'1', PUBLIC_FREE_ENABLED:'0'
};}
async function responseJson(path, opts={}) {
  const reply=await handleRequest(request(path,opts.method||'GET',opts.signed!==false), env(opts.db));
  return { status:reply.status, body:await reply.json() };
}

test('offline build preserves the existing Mini App JS, SVGs and 81 lessons', () => {
  assert.ok(existsSync('cloudflare/public/index.html'));
  assert.ok(existsSync('cloudflare/public/static/app.js'));
  assert.ok(existsSync('cloudflare/public/static/illustrations/preklinik/ergonomika.svg'));
  const html=readFileSync('cloudflare/public/index.html','utf8');
  assert.match(html,/app.js\?v=/);
});

test('health endpoint is safe without Telegram token or D1, and marks preview', async () => {
  const reply=await handleRequest(new Request(domain+'/api/health'),{});
  assert.equal(reply.status,200);
  const body=await reply.json();
  assert.equal(body.status,'ok');
  assert.equal(body.migration_ready,false);
  assert.equal(body.version,'1.0.3');
});

test('Telegram signed initData validates signature and rejects duplicates or expired data', async () => {
  assert.equal(await verifyTelegramInitData(signedTelegram(), TOKEN), UID);
  await assert.rejects(verifyTelegramInitData(signedTelegram().replace('Fake','Other'),TOKEN));
  await assert.rejects(verifyTelegramInitData(signedTelegram()+'&hash=other',TOKEN));
  await assert.rejects(verifyTelegramInitData(signedTelegram(UID,Date.now()-4000000),TOKEN));
  await assert.rejects(verifyTelegramInitData(signedTelegram(), 'wrong-token'));
});

test('all personal endpoints fail closed without signature, D1 or approval', async () => {
  assert.equal((await responseJson('/api/me',{signed:false,db:fakeDb()})).status,401);
  assert.equal((await responseJson('/api/me',{db:null})).status,503);
  assert.equal((await responseJson('/api/me',{db:fakeDb({approved:false})})).status,403);
  assert.equal((await responseJson('/api/catalog',{db:fakeDb({consented:false})})).status,403);
});

test('consent, subjects and lessons work for approved fake student; answers are hidden', async () => {
  const db=fakeDb({approved:true,consented:false});
  const before=await responseJson('/api/me',{db});
  assert.equal(before.status,200);
  assert.equal(before.body.consented,false);
  const consent=await responseJson('/api/consent',{db,method:'POST'});
  assert.equal(consent.status,200);
  assert.equal(consent.body.consented,true);
  const subjects=await responseJson('/api/catalog',{db});
  assert.equal(subjects.status,200);
  assert.equal(subjects.body.subjects.length,6);
  assert.equal(subjects.body.subjects.reduce((sum,s)=>sum+s.lessons.length,0),81);
  const lesson=await responseJson('/api/lessons/ergonomika',{db});
  assert.equal(lesson.status,200);
  assert.equal(lesson.body.subject_id,'stom_prerest');
  assert.equal(lesson.body.questions.length,10);
  assert.ok(!lesson.body.questions.some(q=>Object.hasOwn(q,'answer')));
  const missing=await responseJson('/api/lessons/unknown',{db});
  assert.equal(missing.status,404);
});

test('unsupported writes and webhook return an explicit disabled response', async () => {
  assert.equal((await responseJson('/api/attempts',{db:fakeDb(),method:'POST'})).status,501);
  assert.equal((await responseJson('/telegram/webhook',{db:fakeDb()})).status,503);
});
