/* Telegram command gateway for the separate MedStudy AI Cloudflare preview.
 * Default OFF. Never configure the production Telegram bot or setWebhook here.
 * Only authenticated webhook updates from a TEST BOT can reach the handler.
 */
const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'}
});
const fail = (status, detail) => json({ detail }, status);
const isUid = x => Number.isSafeInteger(x) && x > 0 && x < 1e16;
const parseIDs = text => new Set(
  String(text || '').split(/[,;]/).map(x => x.trim()).filter(x => /^[1-9][0-9]{0,15}$/.test(x)).map(Number)
);
const administrators = env => parseIDs(env.ADMIN_USER_IDS || env.ALLOWED_USER_IDS);
const today = () => new Date().toISOString();
function checkSecret(provided, expected) {
  if (!expected || !/^[A-Za-z0-9_-]{16,256}$/.test(expected)) return false;
  if (!provided || provided.length !== expected.length) return false;
  let diff = 0;
  for (let i=0; i < expected.length; i++) diff |= expected.charCodeAt(i) ^ provided.charCodeAt(i);
  return diff === 0;
}
function validWebAppURL(env, request) {
  // No arbitrary URLs supplied by Telegram update, only this Worker origin.
  const url = new URL(request.url);
  const publicUrl = String(env.WEB_APP_URL || url.origin);
  try {
    const parsed = new URL(publicUrl);
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
        parsed.search || parsed.hash || parsed.pathname !== '/') return '';
    if (parsed.origin !== url.origin) return '';
    return parsed.origin;
  } catch { return ''; }
}

async function telegramAPI(method, payload, env) {
  const response = await fetch('https://api.telegram.org/bot' + env.BOT_TOKEN + '/' + method, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  // Never expose the Bot API response: it may contain a private token.
  if (!response.ok) throw new Error('Telegram API unavailable');
  const result = await response.json();
  if (!result.ok) throw new Error('Telegram API rejected request');
}

async function accessStatus(db, uid) {
  const row = await db.prepare('SELECT status FROM access_requests WHERE user_id=?').bind(uid).first();
  return row?.status || 'not_requested';
}
async function requestAccess(db, uid) {
  const inserted = await db.prepare(
    "INSERT OR IGNORE INTO access_requests(user_id,status,requested_at) VALUES (?,'pending',?)"
  ).bind(uid, today()).run();
  return {created:(inserted.meta?.changes || 0)>0, status:await accessStatus(db,uid)};
}
async function pendingRequests(db) {
  const rows = await db.prepare(
    "SELECT user_id FROM access_requests WHERE status='pending' ORDER BY requested_at LIMIT 15"
  ).all();
  return (rows.results || []).map(x=>x.user_id);
}
async function decide(db, adminUid, targetUid, decision) {
  const current = await accessStatus(db,targetUid);
  if (current==='not_requested' && decision!=='approved') {
    return 'Foydalanuvchi avval /start yuborishi kerak';
  }
  if (decision==='revoked' && current!=='approved') {
    return 'Faqat tasdiqlangan ruxsat bekor qilinadi';
  }
  if (current==='not_requested') {
    await db.prepare(
      "INSERT INTO access_requests(user_id,status,requested_at,reviewed_at,reviewed_by) VALUES (?,'approved',?,?,?)"
    ).bind(targetUid,today(),today(),adminUid).run();
  } else {
    await db.prepare(
      'UPDATE access_requests SET status=?,reviewed_at=?,reviewed_by=? WHERE user_id=?'
    ).bind(decision,today(),adminUid,targetUid).run();
  }
  return '✅ ' + targetUid + ': ' + decision;
}
const button = url => url ? { inline_keyboard: [
  [{ text:'📱 MedStudy AI ni ochish', web_app: {url} }]
] } : undefined;

async function handleCommand(update, env, request, outbound) {
  const message = update.message;
  const db = env.DB, adminSet = administrators(env);
  const publicUrl = validWebAppURL(env, request);
  const approval = env.ACCESS_APPROVAL_ENABLED === '1';
  const publicFree = env.PUBLIC_FREE_ENABLED === '1';

  if (update.callback_query) {
    const callback=update.callback_query;
    const admin=callback.from?.id;
    const data=String(callback.data || '');
    const match = /^access:(approve|reject|revoke):([1-9][0-9]{0,15})$/.exec(data);
    let answer='Bu amal faqat administratorga ruxsat etilgan';
    if (approval && isUid(admin) && adminSet.has(admin) && match) {
      const target=Number(match[2]);
      const decision={approve:'approved',reject:'rejected',revoke:'revoked'}[match[1]];
      answer=await decide(db,admin,target,decision);
      if (answer.startsWith('✅')) {
        try { await outbound('sendMessage',{chat_id:target,text:'MedStudy AI ruxsat holati: '+decision+
          (decision==='approved'?'. /start yuborib ilovani oching.':'.')},env); }
        catch { /* Student may not have opened the bot; decision is persisted. */ }
      }
    }
    if (typeof callback.id==='string' && callback.id.length<=256) {
      await outbound('answerCallbackQuery',{callback_query_id:callback.id,text:answer.slice(0,180)},env);
    }
    return;
  }
  if (!message || message.chat?.type!=='private' || !isUid(message.from?.id) ||
      message.from?.is_bot || message.chat?.id!==message.from.id) return;

  const uid=message.from.id;
  const text=String(message.text || '').trim().slice(0,512);
  const [first,...rest]=text.split(/\s+/);
  const cmd=(first?.startsWith('/') ? first.split('@')[0].toLowerCase() : '');
  const target=rest.join(' ').trim();
  const admin=adminSet.has(uid);
  let body, markup;
  if (cmd==='/myid') {
    body='Sizning Telegram ID: '+uid+'. Uni ochiq joyda ulashmang.';
  } else if (approval && admin && ['/approve','/reject','/revoke'].includes(cmd)) {
    if (!/^[1-9][0-9]{0,15}$/.test(target) || !isUid(Number(target))) {
      body='Format: /approve 123456789 yoki /reject 123456789 yoki /revoke 123456789';
    } else {
      const decision={'/approve':'approved','/reject':'rejected','/revoke':'revoked'}[cmd];
      body=await decide(db,uid,Number(target),decision);
      if (body.startsWith('✅')) {
        try { await outbound('sendMessage',{chat_id:Number(target),
          text:'MedStudy AI ruxsat holati: '+decision+
          (decision==='approved'?'. /start yuborib ilovani oching.':'.')},env); }
        catch { /* Persisted decision is still visible via /status. */ }
      }
    }
  } else if (approval && admin && cmd==='/requests') {
    const pending=await pendingRequests(db);
    body=pending.length ? 'Kutilayotgan so‘rovlar:\n'+pending.join('\n')+
      '\n\n/approve ID, /reject ID yoki /revoke ID' : 'Kutilayotgan so‘rovlar yo‘q.';
  } else if (cmd==='/privacy') {
    body='Telegram ID, rozilik va test natijalari saqlanadi. Kirish holati va vaqt belgisi qayd etiladi. Bu rasmiy universitet xizmati emas.';
  } else if (approval && cmd==='/status') {
    const status=admin?'approved':await accessStatus(db,uid);
    body={
      approved:'✅ Mini App ochiq.',pending:'⏳ Administrator javobi kutilmoqda.',
      rejected:'❌ So‘rov rad etilgan.',revoked:'⛔ Ruxsat bekor qilingan.',
      not_requested:'/start orqali qabul so‘rovini yuboring.'
    }[status];
  } else if (approval && admin && cmd==='/help') {
    body='MedStudy AI administrator buyruqlari:\n/requests — arizalar\n/approve ID\n/reject ID\n/revoke ID\n/myid';
  } else if (approval && !admin && (cmd==='/start' || cmd==='/help' || !cmd)) {
    const {created,status}=await requestAccess(db,uid);
    if (created) {
      for (const adminUid of [...adminSet].slice(0,5)) {
        const keyboard={inline_keyboard:[[{
          text:'✅ Tasdiqlash',callback_data:'access:approve:'+uid
        },{
          text:'❌ Rad etish',callback_data:'access:reject:'+uid
        }]]};
        try { await outbound('sendMessage',{chat_id:adminUid,
          text:'📩 MedStudy AI Mini App kirish so‘rovi.\nTelegram ID: '+uid,
          reply_markup:keyboard},env); }
        catch { /* Keep pending request for /requests. */ }
      }
    }
    if (status==='approved') {
      body='✅ Ruxsat tasdiqlangan. MedStudy AI Mini App’ni ochishingiz mumkin.';
      markup=button(publicUrl);
    } else {
      body={
        pending:'⏳ So‘rov administratorga yuborildi. /status orqali tekshiring.',
        rejected:'❌ So‘rov rad etilgan. Administratorga murojaat qiling.',
        revoked:'⛔ Ruxsat bekor qilingan. Administratorga murojaat qiling.'
      }[status];
    }
  } else if (!publicFree && !admin && !parseIDs(env.ALLOWED_USER_IDS).has(uid)) {
    body='MedStudy AI hozir yopiq sinovda. /myid orqali ID ni ko‘ring.';
  } else if (cmd==='/start' || cmd==='/help' || !cmd) {
    body='🎓 MedStudy AI — 6 fan, 81 mavzu. Mini App’ni oching.';
    markup=button(publicUrl);
  } else {
    body='Mini App uchun /start yoki /status buyrug‘ini yuboring.';
  }
  const payload={chat_id:uid,text:body || 'MedStudy AI'};
  if (markup) payload.reply_markup=markup;
  await outbound('sendMessage',payload,env);
}

export async function handleTelegramWebhook(request, env, outbound=telegramAPI) {
  // This flag is intentionally not present in wrangler.jsonc. A new isolated
  // TEST BOT must be configured before enabling it explicitly.
  if (env.TELEGRAM_WEBHOOK_ENABLED !== '1') {
    return fail(503,'Telegram webhook hali ko‘chirilmagan');
  }
  if (request.method!=='POST') return fail(405,'Method not allowed');
  if (!env.DB || !env.BOT_TOKEN || !checkSecret(
    request.headers.get('X-Telegram-Bot-Api-Secret-Token'),
    env.TELEGRAM_WEBHOOK_SECRET
  )) return fail(403,'Forbidden');

  const contentLength=Number(request.headers.get('content-length') || 0);
  if (contentLength>65_536) return fail(413,'Payload too large');
  let update;
  try {
    const raw=await request.text();
    if (raw.length>65_536) return fail(413,'Payload too large');
    update=JSON.parse(raw);
  } catch { return fail(400,'Invalid JSON'); }
  if (!update || typeof update!=='object' || !Number.isSafeInteger(update.update_id) ||
      update.update_id<0) return fail(400,'Invalid update');

  // The unique update ID prevents repeated /start or callback effects on
  // Telegram retries; unprocessed reservations are cleared if sending fails.
  const inserted=await env.DB.prepare(
    'INSERT OR IGNORE INTO telegram_updates(update_id,received_at) VALUES (?,?)'
  ).bind(update.update_id,today()).run();
  if (!(inserted.meta?.changes>0)) return json({ok:true});
  try {
    await handleCommand(update,env,request,outbound);
    return json({ok:true});
  } catch {
    await env.DB.prepare('DELETE FROM telegram_updates WHERE update_id=?')
      .bind(update.update_id).run();
    return fail(502,'Telegram processing failed');
  }
}
