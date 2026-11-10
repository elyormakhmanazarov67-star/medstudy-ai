import { test } from 'node:test';
import assert from 'node:assert/strict';
import { handleTelegramWebhook } from '../src/telegram.mjs';

const TOKEN = '111111:fake-test-token-only';
const SECRET = 'test_webhook_secret_123456789';
const ADMIN = 900000011;
const STUDENT = 900000033;
const ORIGIN='https://medstudy-ai-free-preview.example.workers.dev';
class MockDB {
  constructor() {
    this.access=new Map();
    this.updates=new Set();
  }
  prepare(sql) {
    const db=this;
    return {bind(...args){
      return {
        async first() {
          if (sql.startsWith('SELECT status FROM access_requests')) {
            const value=db.access.get(args[0]);
            return value ? {status:value.status} : null;
          }
          throw Error('Unexpected query: '+sql);
        },
        async all() {
          if (sql.startsWith('SELECT user_id FROM access_requests')) {
            return {results:[...db.access].filter(([id,x])=>x.status==='pending')
              .map(([user_id])=>({user_id})).slice(0,15)};
          }
          throw Error('Unexpected query: '+sql);
        },
        async run() {
          if (sql.startsWith('INSERT OR IGNORE INTO telegram_updates')) {
            if(db.updates.has(args[0]))return {meta:{changes:0}};
            db.updates.add(args[0]);return {meta:{changes:1}};
          }
          if (sql.startsWith('DELETE FROM telegram_updates')) {
            return {meta:{changes:Number(db.updates.delete(args[0]))}};
          }
          if (sql.startsWith('INSERT OR IGNORE INTO access_requests')) {
            if(db.access.has(args[0]))return {meta:{changes:0}};
            db.access.set(args[0],{status:'pending'});
            return {meta:{changes:1}};
          }
          if (sql.startsWith('INSERT INTO access_requests')) {
            db.access.set(args[0],{status:'approved'});
            return {meta:{changes:1}};
          }
          if (sql.startsWith('UPDATE access_requests')) {
            db.access.set(args[3],{status:args[0]});
            return {meta:{changes:1}};
          }
          throw Error('Unexpected D1 statement: '+sql);
        }
      };
    }};
  }
}

const env = db => ({
  DB:db,
  BOT_TOKEN:TOKEN,
  TELEGRAM_WEBHOOK_ENABLED:'1',
  TELEGRAM_WEBHOOK_SECRET:SECRET,
  ACCESS_APPROVAL_ENABLED:'1',
  PUBLIC_FREE_ENABLED:'0',
  ADMIN_USER_IDS:String(ADMIN),
});

function update(id,uid,cmd) {
  return {update_id:id,message:{
    chat:{id:uid,type:'private'},from:{id:uid,first_name:'Fake'},text:cmd
  }};
}
function callback(id,uid,command,target=STUDENT) {
  return {update_id:id,callback_query:{
    id:'fake-callback-'+id,from:{id:uid},
    data:'access:'+command+':'+target,
  }};
}
async function send(db,updateData,{
  config=env(db),header=SECRET,outbound,method='POST'
}={}) {
  const calls=[];
  const api=outbound || (async (method,payload)=>{calls.push({method,payload})});
  const request=new Request(ORIGIN+'/telegram/webhook',{
    method,
    headers:{'content-type':'application/json','X-Telegram-Bot-Api-Secret-Token':header},
    ...(method==='POST'?{body:JSON.stringify(updateData)}:{}),
  });
  const result=await handleTelegramWebhook(request,config,api);
  return {status:result.status,body:await result.json(),calls};
}
test('default disabled: no webhook updates processed even with valid signature',async()=>{
  const db=new MockDB();
  const {status}=await send(db,update(1,STUDENT,'/start'),{
    config:{...env(db),TELEGRAM_WEBHOOK_ENABLED:'0'}
  });
  assert.equal(status,503);
  assert.equal(db.access.size,0);
});
test('wrong webhook secret or missing token is rejected before touching D1',async()=>{
  const db=new MockDB();
  assert.equal((await send(db,update(1,STUDENT,'/start'),{header:'wrong'})).status,403);
  assert.equal((await send(db,update(2,STUDENT,'/start'),{
    config:{...env(db),BOT_TOKEN:''}
  })).status,403);
  assert.equal(db.updates.size,0);
});
test('new student /start notifies admin once and no duplicate writes',async()=>{
  const db=new MockDB(),msg=update(8,STUDENT,'/start');
  const first=await send(db,msg);
  assert.equal(first.status,200);
  assert.equal(db.access.get(STUDENT).status,'pending');
  assert.equal(first.calls.filter(x=>x.method==='sendMessage').length,2);
  assert.ok(first.calls.some(x=>x.payload.chat_id===ADMIN));
  assert.ok(first.calls.some(x=>x.payload.chat_id===STUDENT));
  const duplicate=await send(db,msg);
  assert.equal(duplicate.status,200);
  assert.equal(duplicate.calls.length,0);
  const repeated=await send(db,update(9,STUDENT,'/start'));
  assert.equal(repeated.status,200);
  assert.equal(repeated.calls.length,1);
});
test('only configured admin can approve, reject and revoke; student can see status',async()=>{
  const db=new MockDB();await send(db,update(1,STUDENT,'/start'));
  const unauthorized=await send(db,callback(2,STUDENT,'approve'));
  assert.equal(unauthorized.status,200);
  assert.equal(db.access.get(STUDENT).status,'pending');
  const approve=await send(db,callback(3,ADMIN,'approve'));
  assert.equal(approve.status,200);
  assert.equal(db.access.get(STUDENT).status,'approved');
  assert.ok(approve.calls.some(x=>x.method==='answerCallbackQuery'));
  const open=await send(db,update(4,STUDENT,'/start'));
  assert.ok(open.calls[0].payload.reply_markup.inline_keyboard[0][0].web_app.url===ORIGIN);
  assert.equal((await send(db,update(5,STUDENT,'/status'))).calls[0].payload.text,'✅ Mini App ochiq.');
  const revoke=await send(db,update(6,ADMIN,'/revoke '+STUDENT));
  assert.equal(revoke.status,200);
  assert.equal(db.access.get(STUDENT).status,'revoked');
});
test('only private messages from same Telegram user are processed',async()=>{
  const db=new MockDB();
  const bad=update(40,STUDENT,'/start');
  bad.message.chat.id=ADMIN;
  const result=await send(db,bad);
  assert.equal(result.status,200);
  assert.equal(db.access.size,0);
  assert.equal(result.calls.length,0);
});
test('failed send permits Telegram retry of the same update ID',async()=>{
  const db=new MockDB();const event=update(50,STUDENT,'/start');
  const fail=await send(db,event,{outbound:async()=>{throw Error('offline network failure')}});
  assert.equal(fail.status,502);
  assert.equal(db.updates.has(50),false);
  const again=await send(db,event);
  assert.equal(again.status,200);
});
