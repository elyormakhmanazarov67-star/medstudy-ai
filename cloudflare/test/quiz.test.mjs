import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, webcrypto } from 'node:crypto';
import catalog from '../generated/catalog.mjs';
import { handleRequest } from '../src/worker.mjs';

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const TOKEN = '111111:offline-test-token';
const UID = 900009001;
const lessonId = 'ergonomika';
const lesson = catalog.subjects.flatMap(s => s.lessons).find(l => l.id === lessonId);

function telegram(uid = UID) {
  const p = new URLSearchParams();
  p.set('user', JSON.stringify({ id: uid, first_name: 'Offline test' }));
  p.set('auth_date', String(Math.floor(Date.now()/1000)));
  const data = [...p.entries()].sort(([a],[b]) => a.localeCompare(b))
    .map(([key,val]) => key+'='+val).join('\n');
  const key = createHmac('sha256', 'WebAppData').update(TOKEN).digest();
  p.set('hash', createHmac('sha256', key).update(data).digest('hex'));
  return p.toString();
}

class MockD1 {
  constructor() { this.users = new Set([UID, UID+1]); this.attempts = []; this.answers = []; this.rates = new Map(); }
  prepare(sql) {
    const db = this;
    return { bind(...args) {
      return {
        sql, args,
        async first() {
          if (sql.startsWith('SELECT status FROM access_requests')) return {status:'approved'};
          if (sql.startsWith('SELECT 1 AS accepted FROM users')) return db.users.has(args[0]) ? {accepted:1} : null;
          if (sql.startsWith('SELECT id FROM attempts')) return [...db.attempts]
            .filter(a => a.user_id === args[0] && a.lesson_id === args[1] &&
              ['full','retry'].includes(a.mode)).sort((a,b)=>b.id-a.id)[0] || null;
          if (sql.startsWith('SELECT COUNT(*) AS n')) return {n:db.attempts.filter(a => a.user_id === args[0]).length};
          throw new Error('Unmocked first SQL: '+sql);
        },
        async all() {
          if (sql.startsWith('SELECT question_id FROM answers')) return { results:db.answers.filter(
            a => a.attempt_id === args[0] && a.correct === 0).map(a => ({question_id:a.question_id})) };
          if (sql.startsWith('SELECT a.lesson_id')) {
            const latest = new Map();
            for (const a of db.attempts.filter(a => a.user_id === args[0] && a.mode === 'full'))
              if (!latest.has(a.lesson_id) || a.id > latest.get(a.lesson_id).id) latest.set(a.lesson_id, a);
            return {results:[...latest.values()].map(a => ({
              lesson_id:a.lesson_id,score:a.score,total:a.total,created_at:a.created_at
            }))};
          }
          if (sql.startsWith('SELECT lesson_id,score,total,mode,created_at')) return {results:
            db.attempts.filter(a => a.user_id === args[0]).sort((a,b) => b.id-a.id)
              .slice(0,args[1]).map(({lesson_id,score,total,mode,created_at}) =>
                ({lesson_id,score,total,mode,created_at}))
          };
          throw new Error('Unmocked all SQL: '+sql);
        },
        async run() {
          if (sql.startsWith('INSERT INTO rate_limits')) {
            const [uid, action, minute, limit] = args;
            const key = uid+':'+action;
            const prev = db.rates.get(key);
            if (prev && prev.minute === minute && prev.requests >= limit)
              return {meta:{changes:0}};
            db.rates.set(key,{minute,requests:prev?.minute===minute ? prev.requests+1 : 1});
            return {meta:{changes:1}};
          }
          if (sql.startsWith('INSERT INTO attempts(')) {
            const [id,user_id,lesson_id,score,total,mode,created_at]=args;
            if (db.attempts.some(x => x.id===id)) throw new Error('Duplicate ID');
            db.attempts.push({id,user_id,lesson_id,score,total,mode,created_at});
            return {meta:{changes:1}};
          }
          if (sql.startsWith('INSERT INTO answers(')) {
            const [attempt_id,question_id,chosen,correct] = args;
            db.answers.push({attempt_id,question_id,chosen,correct});
            return {meta:{changes:1}};
          }
          throw new Error('Unmocked run SQL: '+sql);
        },
      };
    }};
  }
  async batch(statements) {
    // Mimics D1's atomic prepared-statement batch.
    const oldAttempts = [...this.attempts], oldAnswers=[...this.answers];
    try { return await Promise.all(statements.map(s => s.run())); }
    catch (error) { this.attempts=oldAttempts;this.answers=oldAnswers;throw error; }
  }
}

async function send(db, path, {uid=UID, method='GET', body, signed=true}={}) {
  const headers = {'Content-Type':'application/json'};
  if(signed) headers['X-Telegram-Init-Data']=telegram(uid);
  const request = new Request('https://medstudy.example.org'+path, {
    method, headers, ...(body===undefined?{}:{body:JSON.stringify(body)})
  });
  const response = await handleRequest(request, {
    DB:db,BOT_TOKEN:TOKEN,ACCESS_APPROVAL_ENABLED:'1',PUBLIC_FREE_ENABLED:'0'
  });
  return {status:response.status, json:await response.json()};
}

test('Cloudflare D1 quiz saves, reviews and shows only own results', async () => {
  const db = new MockD1();
  const ids=lesson.questions.map(q=>q.id);
  const answers=lesson.questions.map(()=>0);
  const saved=await send(db, '/api/attempts',{method:'POST',body:{lesson_id:lessonId,question_ids:ids,answers}});
  assert.equal(saved.status,200);
  assert.equal(saved.json.total,10);
  assert.equal(saved.json.mode,'full');
  assert.equal(db.attempts.length,1);
  assert.equal(db.answers.length,10);
  const wrong=await send(db,'/api/review/'+lessonId);
  assert.equal(wrong.status,200);
  const wrongIds=wrong.json.questions.map(q=>q.id);
  assert.ok(wrongIds.length>0);
  assert.equal(wrongIds.length, saved.json.details.filter(d=>!d.correct).length);
  assert.ok(wrong.json.questions.every(q=>!Object.hasOwn(q,'answer')));

  const retryAnswers=wrongIds.map(id=>lesson.questions.find(q=>q.id===id).answer);
  const retry=await send(db,'/api/attempts',{method:'POST',body:{
    lesson_id:lessonId,question_ids:wrongIds,answers:retryAnswers
  }});
  assert.equal(retry.status,200);
  assert.equal(retry.json.mode,'retry');
  assert.equal(retry.json.score,wrongIds.length);
  assert.equal((await send(db,'/api/review/'+lessonId)).json.questions.length,0);

  const progress=await send(db,'/api/progress');
  assert.equal(progress.status,200);
  assert.equal(progress.json.attempts_count,2);
  assert.equal(progress.json.latest.length,1);
  assert.equal(progress.json.latest[0].lesson_id,lessonId);
  assert.equal(progress.json.latest[0].score,saved.json.score);
  const history=await send(db,'/api/history?limit=10');
  assert.equal(history.json.items.length,2);
  assert.equal(history.json.items[0].mode,'retry');
  assert.equal(history.json.items[1].mode,'full');
  assert.equal((await send(db,'/api/history',{uid:UID+1})).json.items.length,0);
  assert.equal((await send(db,'/api/progress',{uid:UID+1})).json.attempts_count,0);
  assert.equal((await send(db,'/api/review/'+lessonId,{uid:UID+1})).json.questions.length,0);
});

test('Quiz rejects forged scores, wrong IDs, invalid answers and unsigned users', async () => {
  const db=new MockD1();
  const ids=lesson.questions.map(q=>q.id);
  const answers=ids.map(()=>0);
  const good={lesson_id:lessonId,question_ids:ids,answers};
  const forged=await send(db,'/api/attempts',{method:'POST',body:{...good,score:100,answers:[0]}});
  assert.equal(forged.status,422);
  const fakeIds=await send(db,'/api/attempts',{method:'POST',body:{...good,question_ids:['fake']}});
  assert.equal(fakeIds.status,400);
  const badAnswer=await send(db,'/api/attempts',{method:'POST',body:{...good,answers:answers.map(()=>5)}});
  assert.equal(badAnswer.status,422);
  const unsigned=await send(db,'/api/attempts',{method:'POST',signed:false,body:good});
  assert.equal(unsigned.status,401);
  assert.equal(db.attempts.length,0);
  assert.equal(db.answers.length,0);
});

test('No Telegram webhook is enabled and daily free preview is not a live bot', async () => {
  const db=new MockD1();
  assert.equal((await send(db,'/telegram/webhook')).status,503);
  assert.equal((await send(db,'/api/unimplemented')).status,501);
});
