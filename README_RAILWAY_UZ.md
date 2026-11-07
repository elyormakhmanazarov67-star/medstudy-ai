# MedStudy AI Mini App v0.3 — Railway hosting qo‘llanmasi

Bu loyiha Telegram orqali kiriladigan **yopiq sinov** uchun: 1 fan, 2 dars, 22 savol, SQLite va Telegram webhook (`/start`, `/myid`, `/help`, `/privacy`).

**Hozirgi holat:** serverga avtomatik joylanmagan. Railway'da alohida loyiha yaratish va tokenni Railway Variables bo‘limiga kiritish kerak. Maxfiy ma’lumotlarni Telegram chatiga yoki GitHub'ga yubormang.

## A. Loyihani Railway'ga chiqarish

1. **Yangi, PRIVATE GitHub repository** yarating (masalan `medstudy-miniapp`). ZIP ichidagi fayllarni repository'ning ildiziga yuklang, lekin `.env`, `*.db` va tokenlarni hech qachon yuklamang. Ehtiyot bo‘ling: **shaxsiy ma’lumotli mahalliy bazani GitHub'ga yubormang**.
2. https://railway.com da **New Project → Deploy from GitHub Repo** ni bosing. Yangi repository'ni ulang. Railway ildizdagi `Dockerfile` orqali quradi.
3. Xizmatda **Settings → Networking → Generate Domain** ni bosing. `https://...up.railway.app` manzilini yozib oling.
4. **Variables** bo‘limiga quyidagilarni kiriting (faqat o‘zingizning Railway boshqaruv panelingizga):

```
BOT_TOKEN=<BotFather bergan token>
ALLOWED_USER_IDS=<Telegram ID raqamingiz>
TELEGRAM_WEBHOOK_SECRET=<32 belgili taxmin qilib bo‘lmaydigan matn>
DATABASE_PATH=/app/data/medstudy.db
WEB_APP_URL=https://<Railway Generate Domain manzili>
DEV_PREVIEW=0
AUTO_SET_WEBHOOK=0
```

`TELEGRAM_WEBHOOK_SECRET` uchun Windows PowerShell'da quyidagi buyruqni bajaring (natijasini chatga yubormang):

```
$alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'; -join (1..40 | ForEach-Object { $alphabet[[System.Security.Cryptography.RandomNumberGenerator]::GetInt32($alphabet.Length)] })
```

5. **Volume** qo‘shing, mount path **`/app/data`** bo‘lsin. Bu shart: SQLite natijalari qayta joylash yoki qayta ishga tushganda yo‘qolmasin. Railway'ning Volume sozlamalari reja bo‘yicha farqlanishi mumkin.
6. Deployment **Active** bo‘lganda `https://<sizning-domeningiz>/api/health` ochib `{ "status": "ok", ... }` natijasini tekshiring.
7. **Kompyuterdagi eski MedStudy AI polling botini to‘xtating** (Ctrl+C). Uning bir xil Telegram tokeni bilan ishlashi muammoga sabab bo‘ladi. Eski lokal botning SQLite test tarixi **avtomatik ko‘chmaydi**; eski bazani o‘chirib yubormang.
8. Railway Variables'da `AUTO_SET_WEBHOOK=1` ni o‘rnating va **Redeploy** qiling. Logda `Telegram webhook + Mini App menu configured.` yozuvi chiqishi kerak. Bu Telegram botga HTTPS webhook hamda Mini App menyusini o‘rnatadi.
9. Telegram'dagi botga `/start` yuboring va **📱 MedStudy AI ni ochish** tugmasini bosing. `ALLOWED_USER_IDS` da ko‘rsatilgan sinovchi kirishi mumkin. Ilova ichida maxfiylik roziligini bering, test topshiring va progressni tekshiring.
10. Kompyuterni o‘chirsangiz ham telefoningiz orqali testni yana oching. Oldingi natija saqlanishi kerak. Natija saqlanmasa, Volume mount path va `DATABASE_PATH` ni tekshiring.

### Muhim qo‘shimcha

- Telegram webhook `/telegram/webhook` secret-token tekshiruvi bilan himoyalangan. Bot API tokenini URLga qo‘shmang.
- `AUTO_SET_WEBHOOK=0` rejimida HTTPS Mini App ishlaydi, ammo Telegram `/start` buyruqlariga server javob bermaydi. `1` faqat yuqoridagi 7-bosqichdan keyin yoqiladi.
- Telegramda oldingi chat botning inline chat menyulari cloud versiyada emas — **bu server variantida chat buyruqlari Mini App'ni ochuvchi boshlang‘ich menyuga almashtiriladi**. Darslar va testlar Mini App ichida mavjud.
- Dastlabki materiallar tibbiy ekspert tasdig‘ini kutmoqda. Bot faqat yopiq testda ishlatilsin.
- Ishlab turgan Mini App versiyasining avvalgi lokal progressini ko‘chirish kerak bo‘lsa, `/app/data/medstudy.db` bazasini xavfsiz usulda eksport/import qilish zarur; avtomatik migratsiya bu versiyada yo‘q.
- Hosting 24/7 rejimi tanlangan Railway tarifiga, mablag‘ va resurslarga bog‘liq. Doimiy ishlashni tekshiring, backup va monitoring sozlang.
- Railway xizmat narxi yoki bepul limitlar o‘zgarishi mumkin. Deploydan oldin Billing bo‘limini tekshiring.

## B. Texnik qismlar

`Dockerfile` bitta FastAPI serverini ko‘taradi. `PORT` ni Railway belgilaydi, shuning uchun qo‘shimcha proxy yozish talab etilmaydi. Domain va TLS'ni Railway boshqaradi. `/api/health` sog‘lom javob qaytaradi. `ALLOWED_USER_IDS` sinovchilarni cheklaydi. `app/auth.py` Telegram Mini App initData imzosini tekshiradi.

## C. Mahalliy sinov

`DEV_PREVIEW=1` faqat `127.0.0.1` demo uchun. Ommaviy hostingda har doim `0` bo‘lsin. Avtomatik test uchun `python -m pytest -q` (pytest alohida o‘rnatilishi kerak).
