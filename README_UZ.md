# MedStudy AI — Telegram Mini App v0.3 (DRAFT)

**Railway serverga joylash uchun README_RAILWAY_UZ.md faylini o‘qing.**

**Holat:** faol Telegram serveriga ulanmagan, hali ommaga chiqarilmagan. 1 fan, 2 mavzu, 22 test savoliga ega ishlaydigan dastur prototipi. Barcha darslar tibbiy ekspert tasdig‘ini kutmoqda.

## 1. Nimalar mavjud?

- Telegram ichida ochiladigan mobil dizayn
- Stomatologiya fanidan 2 ta mavzu va 22 ta test
- Barcha natijalarni **server tomonida** tekshirish (javoblar test vaqtida brauzerga berilmaydi)
- SQLite orqali shaxsiy test natijalari, takrorlash uchun xato savollar
- Ma’lumotlarni saqlashga alohida rozilik va foydalanuvchi ma’lumotlarini o‘chirish
- Telegram `initData` imzosini HMAC-SHA-256 orqali tekshirish, 1 soatlik muddat va sinovchilar ID ro‘yxati
- Lokal kompyuter uchun demo rejimi (faqat 127.0.0.1)

**Hozir yo‘q:** generativ AI bilan chat, to‘lov tizimi, ko‘p fanli kutubxona, ommaviy hosting va Google Drive’dan avtomatik sinxronizatsiya.

## 2. Windows 11 — lokal ko‘rish (Telegram tokenisiz)

1. ZIP faylni alohida papkaga chiqaring.
2. Python 3.10 yoki yangiroq versiyasini o‘rnating.
3. `setup_windows.bat` faylini ishga tushiring.
4. `.env` faylini ochib `DEV_PREVIEW=1` qiling. `BOT_TOKEN` bo‘sh yoki namuna bo‘lib qolishi mumkin, **faqat lokal demo** uchun.
5. `run_local.bat` faylini ishga tushiring.
6. Kompyuter brauzerida `http://127.0.0.1:8000/?demo=1` manziliga kiring.

Lokal demo uchun Telegram va internetdagi domen shart emas. Demo foydalanuvchisi alohida sinov IDdan foydalanadi. **DEV_PREVIEW=1 rejimini hech qachon internetga chiqariladigan serverda yoqmang**. Lokal server faqat `127.0.0.1` da ishlaydi.

## 3. Telegram ichida ishlatish

### A) Telegram bot yaratish

1. Telegram’da rasmiy `@BotFather` yordamida `/newbot` buyrug‘i orqali bot yarating.
2. Botning **tokenini** oling va faqat `.env` ga saqlang. Hech qachon chatga, GitHubga yoki screenshotga chiqarib yubormang.
3. O‘zingizning Telegram raqamli IDingizni bilish uchun ishonchli usuldan foydalaning; kerak bo‘lsa botdagi avvalgi `/myid` komandasi yordamida ham olish mumkin. `.env` da `ALLOWED_USER_IDS=123456789` qilib ko‘rsating. Sinovchi IDlarini vergul bilan ajrating. Raqamlarni hech kimdan ochiq kanalda so‘ramang.

### B) HTTPS server

Telegram Mini Apps uchun **haqiqiy HTTPS URL** kerak. Internetdan telefon orqali ochiladigan domen + TLS sertifikat bo‘lishi shart. Mini App backendini serverda ishga tushiring:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# .env ning maxfiy qiymatlarini serverning maxfiy sozlamalarida saqlang
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Buni ishonchli reverse proxy (masalan Caddy/Nginx) orqali HTTPS bilan taqdim qiling. Internetda faqat HTTPS/443 endpointini oching. `DEV_PREVIEW=0` bo‘lsin. `data/` papkasi saqlanib turadigan (persistent) diskka joylashishi kerak, aks holda server qayta ishga tushganda natijalar yo‘qolishi mumkin. Xavfsiz zaxiralash va kirish nazoratini yoqing.

**Muhim:** lokal HTTP brauzerda ishlasa ham, Telegram’da ishga tushirish uchun ommaviy HTTPS manzil talab qilinadi.

### C) Telegram menyusini sozlash

1. `.env` faylida `WEB_APP_URL=https://sizning-domeningiz.example` qiymatini kiriting.
2. `python configure_menu.py` (Windows: `configure_menu_windows.bat`) ni ishga tushiring.
3. Bot chatiga qayting va “MedStudy AI” menyu tugmasini bosing. Istasangiz xuddi shu URLni `@BotFather` `/setmenubutton` orqali sozlang.

Rasmiy Telegram hujjati: https://core.telegram.org/bots/webapps

## 4. Fayllar tuzilishi

- `app/main.py` — API va HTTPS ilova logikasi
- `app/auth.py` — Telegram WebApp.initData tekshirish
- `app/store.py` — SQLite natijalar bazasi
- `app/core.py` — mavzular va test baholash
- `app/static/index.html`, `style.css`, `app.js` — Telegram Mini App interfeysi
- `content/lessons.json` — o‘zbekcha 2 ta mavzu va 22 ta savol
- `configure_menu.py` — Telegram menyusi uchun yordamchi skript
- `tests/` — avtomatik testlar

## 5. Ma’lumotlar va o‘quv manbalari

O‘quv modullari mustaqil yozilgan. SamDTU elektron kutubxonasining katalog havolalari keltiriladi. U yerdagi to‘liq darsliklar bilan barcha faktlar mustaqil qiyoslanmagan. Klinik amaliyot uchun ko‘rsatma deb qabul qilmang. Tijorat nashridan avval malakali stomatolog yoki o‘qituvchi ekspert tekshiruvidan o‘tkazishi kerak.

**Maxfiylik:** faqat Telegram ID, rozilik sanasi, test javoblari va ballar saqlanadi; ism, telefon raqami va chat matnlari saqlanmaydi. Dastur foydalanuvchisi ilova ichida ma’lumotlarini o‘chira oladi. Ilova ommaga chiqarilishidan oldin O‘zbekistonning amaldagi shaxsiy ma’lumotlar va tijorat qoidalariga mosligini tekshiring. Test foydalanuvchilari uchun ham rozilik va aniq xabardor qilish zarur.

## 6. Yangi mavzu qo‘shish

`content/lessons.json` tarkibida kerakli fan `subjects[]`, mavzu `lessons[]`, bo‘lim `sections[]` va savollar `questions[]` formatida saqlanadi. Har savolda 4 variant, `answer` (0,1,2,3) va `explanation` bor. Server qayta ishga tushganda katalog qayta o‘qiladi. Dastlab kichik guruhda tekshiring.

## 7. Sinovlar

```bash
python -m pip install pytest
python -m pytest -q
```

## Xavfsizlik chegarasi

- Demo rejimini ommaviy serverda yoqmang; u faqat `127.0.0.1` uchun.
- `BOT_TOKEN`ni hech kimga bermang, `.env` faylini Gitga qo‘shmang.
- `ALLOWED_USER_IDS` bo‘sh bo‘lsa Telegram orqali hech kim kirolmaydi.
- `Telegram.WebApp.initDataUnsafe` hech qachon autentifikatsiya uchun ishlatilmaydi.
- Ilova to‘lov qabul qilmaydi va hali ekspert tasdig‘idan o‘tmagan.
