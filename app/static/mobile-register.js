'use strict';
const form = document.getElementById('registration');
const status = document.getElementById('status');
const submit = document.getElementById('submit');
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  submit.disabled = true;
  status.textContent = 'Ariza yuborilmoqda…';
  try {
    const response = await fetch('/api/mobile/register', {
      method: 'POST',
      mode: 'same-origin',
      credentials: 'omit',
      cache: 'no-store',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        email: document.getElementById('email').value.trim(),
        display_name: document.getElementById('display_name').value.trim(),
        password: document.getElementById('password').value
      })
    });
    if (response.status === 202) {
      form.reset();
      status.textContent = 'Arizangiz qabul qilindi. Administrator tasdig‘ini kuting. Tasdiqlanmaguncha ilovaga kira olmaysiz.';
    } else if (response.status === 429) {
      status.textContent = 'Juda ko‘p urinish. Keyinroq qayta urinib ko‘ring.';
    } else if (response.status === 422) {
      status.textContent = 'Ism, email yoki parol talabga mos kelmayapti. Parol kamida 12 ta belgidan iborat bo‘lsin.';
    } else {
      status.textContent = 'Server xatosi (' + response.status + '). Ariza yuborilmadi.';
    }
  } catch (_) {
    status.textContent = 'Internet bilan ulanishda xato. Tarmoqni tekshiring va qayta urinib ko‘ring.';
  } finally {
    submit.disabled = false;
  }
});