'use strict';
const byId = id => document.getElementById(id);
const status = message => { byId('status').textContent = message; };

function showSession(signedIn) {
  byId('login-section').hidden = signedIn;
  byId('session-section').hidden = !signedIn;
  document.querySelectorAll('.admin-content').forEach(section => {
    section.hidden = !signedIn;
  });
  if (!signedIn) {
    byId('requests').replaceChildren();
    byId('telegram-status').textContent = 'Kirish talab qilinadi.';
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      cache: 'no-store',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
  } catch (_) {
    throw Error('Serverga ulanib bo‘lmadi. Internetni tekshiring.');
  }
  if (!response.ok) {
    if (response.status === 403) {
      if (path !== '/api/mobile/admin-console/session') showSession(false);
      throw Error(path === '/api/mobile/admin-console/session'
        ? 'Administrator kaliti noto‘g‘ri. Railway Variables dagi MOBILE_ADMIN_KEY qiymatini kiriting.'
        : 'Administrator sessiyasi tugagan. Qayta kiring.');
    }
    if (response.status === 409) throw Error('Telegram bot tokeni yoki chat ID sozlanmagan.');
    if (response.status === 502) throw Error('Telegram xabarni qabul qilmadi. Shaxsiy akkauntingizdan xabar yuboruvchi botga /start yuboring.');
    throw Error('Server xatosi: ' + response.status);
  }
  return response.json();
}

async function signIn() {
  const key = byId('secret').value.trim();
  if (!key) {
    status('Administrator kalitini kiriting.');
    return;
  }
  byId('load').disabled = true;
  try {
    await request('/api/mobile/admin-console/session', {
      method: 'POST',
      headers: { 'X-Mobile-Admin-Key': key },
      body: JSON.stringify({ remember: byId('remember').checked })
    });
    byId('secret').value = '';
    showSession(true);
    await load();
  } catch (error) {
    status(error.message);
  } finally {
    byId('load').disabled = false;
  }
}

async function restoreSession() {
  try {
    const response = await fetch('/api/mobile/admin-console/session', {
      credentials: 'same-origin',
      cache: 'no-store'
    });
    if (response.status === 200) {
      showSession(true);
      await load();
    } else {
      showSession(false);
      status('Kalitni bir marta kiriting. «Bu brauzerda eslab qolish» belgisini qoldiring.');
    }
  } catch (_) {
    showSession(false);
    status('Serverga ulanib bo‘lmadi. Internetni tekshiring.');
  }
}

async function signOut() {
  try {
    await request('/api/mobile/admin-console/logout', { method: 'POST' });
    showSession(false);
    status('Ushbu brauzerdan chiqdingiz. Keyingi safar kalit kerak bo‘ladi.');
  } catch (error) {
    status(error.message);
  }
}

async function review(id, decision) {
  if (!window.confirm('Mobil akkaunt ' + id + ': ' + decision + '. Tasdiqlaysizmi?')) return;
  try {
    await request('/api/mobile/admin-console/review', {
      method: 'POST', body: JSON.stringify({ account_id: id, decision })
    });
    status('Natija saqlandi: ' + id + ' (' + decision + ')');
    await load();
  } catch (error) { status(error.message); }
}

async function load() {
  byId('requests').replaceChildren();
  try {
    const data = await request('/api/mobile/admin-console/pending');
    const telegram = await request('/api/mobile/admin-console/telegram-status');
    byId('telegram-status').textContent = telegram.ready
      ? 'Telegram xabar yuborishga sozlangan.'
      : 'Telegram ulanmagan: bot tokeni ' + (telegram.bot_configured ? 'bor' : 'YO‘Q')
        + ', chat ID ' + (telegram.chat_configured ? 'bor' : 'YO‘Q') + '. Railway Variables ni tekshiring.';
    const items = data.items || [];
    status(items.length ? 'Kutilayotgan arizalar: ' + items.length : 'Yangi arizalar yo‘q.');
    for (const account of items) {
      const item = document.createElement('li');
      const title = document.createElement('strong');
      title.textContent = '#' + account.id + ' — ' + account.display_name;
      const contact = document.createElement('span');
      contact.textContent = account.email;
      item.append(title, contact);
      for (const [decision, label] of [
        ['approved', 'Tasdiqlash'], ['rejected', 'Rad etish']
      ]) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label;
        button.addEventListener('click', () => review(account.id, decision));
        item.append(button);
      }
      byId('requests').append(item);
    }
  } catch (error) { status(error.message); }
}

byId('load').addEventListener('click', signIn);
byId('secret').addEventListener('keydown', event => {
  if (event.key === 'Enter') signIn();
});
byId('logout').addEventListener('click', signOut);

byId('revoke').addEventListener('click', () => {
  const id = Number(byId('account-id').value);
  if (!Number.isSafeInteger(id) || id < 1) {
    status('Akkaunt ID raqamini tekshiring.');
    return;
  }
  review(id, 'revoked');
});

byId('resend-pending').addEventListener('click', async () => {
  try {
    const result = await request('/api/mobile/admin-console/resend-pending', {
      method: 'POST'
    });
    status(result.sent ? 'Telegramga xabar yuborildi.' : 'Yuboriladigan yangi arizalar yo‘q.');
  } catch (error) { status(error.message); }
});

showSession(false);
restoreSession();
