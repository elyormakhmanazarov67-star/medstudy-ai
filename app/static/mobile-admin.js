'use strict';
const byId = id => document.getElementById(id);
const status = message => { byId('status').textContent = message; };
const headers = () => ({
  'X-Mobile-Admin-Key': byId('secret').value,
  'Content-Type': 'application/json'
});

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    cache: 'no-store',
    credentials: 'omit',
    headers: headers()
  });
  if (!response.ok) {
    if (response.status === 403) throw Error('Maxfiy kalit noto‘g‘ri.');
    throw Error('Server xatosi: ' + response.status);
  }
  return response.json();
}

async function review(id, decision) {
  if (!window.confirm('Mobil akkaunt ' + id + ': ' + decision + '. Tasdiqlaysizmi?')) return;
  try {
    await request('/api/mobile/admin-console/review', {
      method: 'POST', body: JSON.stringify({account_id: id, decision})
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
        + ', kanal/chat ID ' + (telegram.chat_configured ? 'bor' : 'YO‘Q') + '. Railway Variables ni tekshiring.';
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

byId('load').addEventListener('click', load);
byId('revoke').addEventListener('click', () => {
  const id = Number(byId('account-id').value);
  if (!Number.isSafeInteger(id) || id < 1) { status('Akkaunt ID raqamini tekshiring.'); return; }
  review(id, 'revoked');
});

byId('resend-pending').addEventListener('click', async () => {
  try {
    const result = await request('/api/mobile/admin-console/resend-pending', { method: 'POST' });
    status(result.sent ? 'Telegramga xabar yuborildi.' : 'Yuboriladigan yangi arizalar yo‘q.');
  } catch (error) {
    status(error.message + ' Telegram botini kanalga administrator qiling.');
  }
});
