# MedStudy AI v0.4 — OpenAI AI Ustoz (Railway)

**Holat:** sinov versiyasi; tijoratga tayyor yoki ekspert tekshiruvidan o‘tgan tibbiy manba emas.

## Nima qo‘shildi?

- Telegram Mini App ichida **AI Ustoz** sahifasi; mavjud 2 mavzudan birini tanlab savol berish.
- OpenAI Responses API (sukut bo‘yicha `gpt-6-luna`) orqali o‘zbekcha, tanlangan darsdan olingan parchalarga tayanib izohlash.
- Alohida AI roziligi; savol matni va yuborilgan dars parchalari **OpenAI API'ga** o‘tadi, lekin bizning SQLite bazamizda saqlanmaydi. `store:false` yuboriladi; providerga oid ma’lumotlar uning siyosatiga ko‘ra qayta ishlanishi mumkin.
- Kuniga **5 ta savol/foydalanuvchi** va **40 ta savol/barcha foydalanuvchilar** uchun serverdagi atomar cheklov (UTC bo‘yicha). Muvaffaqiyatsiz so‘rov ham limitga kirishi mumkin. Bu pulda qattiq budjet kafolati emas.
- API kaliti faqat Railway serveridagi maxfiy o‘zgaruvchida, JS/Telegram clientda emas.
- Dastur `AI_ENABLED=0` bo‘lsa darslar/testlar bo‘yicha odatdagidek ishlayveradi.
- AI roziligini bekor qilish va hisob ma’lumotlarini o‘chirish mumkin. Oldingi SQLite jadvallariga o‘zgartirish yo‘q; yangi jadvallar dastur ishga tushganda avtomatik qo‘shiladi.

## 1. Kodni GitHub'ga yangilash

1. Dastlab hozirgi **Railway 0.3 servisini va Volume'ni o‘chirmang**.
2. Ushbu ZIP'ni oching. Ichidagi `app`, `content`, `Dockerfile`, `requirements.txt`, README va boshqa loyiha fayllarini **avvalgi private `medstudy-ai`** GitHub repository'siga yuklab, mavjud kod fayllarini almashtiring. `data/medstudy.db`, `.env` va tokenni hech qachon GitHub'ga yuklamang.
3. Railway avtomatik redeploy qilsa, `Deployments` da `Success` holatini kuting. Eski `DATABASE_PATH=/app/data/medstudy.db`, Volume mount `/app/data`, Telegram bot va webhook o‘zgaruvchilari **o‘zgartirilmasin**.
4. `https://medstudy-ai-production-f1c8.up.railway.app/api/health` orqali `version: 0.4.0` ni tekshiring. AI hali o‘chirilgan — bu ataylab shunday.

## 2. OpenAI API'ni maxfiy sozlash

1. `https://platform.openai.com/` platformasida **MedStudy AI** uchun alohida API Project yarating. API uchun mavjud hisobdagi ruxsat va billing shartlariga rioya qiling.
2. Project -> Limits bo‘limida o‘zingizga maqbul xarajat limiti va ogohlantirish qo‘ying. Agar haqiqiy maksimal sarf cheklovi kerak bo‘lsa, **Enforce a hard limit** sozlamasi mavjudligini tekshiring. Limit qo‘llanishida kechikish bo‘lishi mumkin.
3. Shu loyihada **server uchun API key** yarating. Hech kimga yubormang. Boshqa ilovalar bilan bo‘lishmang.
4. Railway -> `medstudy-ai` -> Variables bo‘limiga qo‘shing:

```
OPENAI_API_KEY=<API key — faqat Railway'ga, GitHub'ga EMAS>
OPENAI_MODEL=gpt-6-luna
AI_DAILY_LIMIT=5
AI_GLOBAL_DAILY_LIMIT=40
AI_ENABLED=1
```

Oldingi `BOT_TOKEN`, `ALLOWED_USER_IDS`, `TELEGRAM_WEBHOOK_SECRET`, `DATABASE_PATH`, `WEB_APP_URL`, `AUTO_SET_WEBHOOK` o‘zgartirilmaydi.

5. O‘zgarishlarni **Deploy** qilib, `Deployments -> View logs` ni tekshiring. API kalitni log yoki skrinshotda ko‘rsatmang.

## 3. Telegram ichida birinchi sinov

1. `@ProfiMedStudy_bot` -> Mini App'ni oching. Pastdagi **AI Ustoz** tabiga o‘ting.
2. U yerda OpenAI'ga savol va dars parchasi yuborilishi haqidagi **alohida rozilikni** o‘qing, ma’qul bo‘lsa tasdiqlang.
3. `Ergonomika` mavzusini tanlab `Ergonomika nima uchun muhim?` deb so‘rang.
4. Javobni dars bilan solishtiring. AI aniq bo‘lmagan narsa haqida taxmin qilmasligi kerak.
5. `Natijalar` hamda testlar oldingidek ishlayotganini tekshiring. Yopib qayta ochganda SQLite progress saqlanishi kerak.

## Xatolik bo‘lsa

- `AI hozir o‘chirilgan` -> `AI_ENABLED=1`, `OPENAI_API_KEY` Railway Variables'da borligini tekshiring.
- `OpenAI API kaliti yoki modelga ruxsatni tekshiring` -> Project key va model ruxsatlarini tekshiring.
- `OpenAI API limiti yoki balansi tugagan` -> API billing/limitlarni tekshiring. ChatGPT obunasi API hisobini moliyalashtirmaydi.
- `Kunlik AI so‘rovlar limiti tugadi` -> UTC kuni yangilanishini kuting yoki pilot siyosatini qayta ko‘rib chiqing; limitni keskin oshirmang.
- 401/403 -> Mini App'ni Telegram ichida oching, `ALLOWED_USER_IDS` hamda foydalanuvchi roziligini tekshiring.
- Serverning `/api/health` yo‘li faol, ammo Telegram ishlamasa — webhook Variables/loglarni alohida tekshiring.

## Muhim cheklovlar

- Avvalgi universitet darsliklarining **katalog tavsiflari** tekshirilgan, ammo to‘liq matnlarning barcha faktlari klinik ekspertiza qilinmagan. Hozircha **yopiq pilot**.
- AI javoblarining faktik aniqligini o‘qituvchi / mutaxassis bilan tekshiring; haqiqiy bemor ma’lumotini yubormang.
- Faqat tanlangan darsdan 3 tagacha bo‘lim olinadi; bu to‘liq qidiruv / universitet kutubxonasiga jonli ulanish emas.
- `store:false` API so‘rov natijasining Responses obyekt sifatida saqlanmasligini so‘raydi; bu provayderning barcha ishlov berish va retention siyosati nol degani emas.
- Loyiha ommaga ochilmasin, `ALLOWED_USER_IDS` bo‘sh qoldirilmasin. Billing va shaxsiy ma’lumotlarga oid qonuniy talablarni tijoratga chiqishdan oldin tekshiring.
- Jonli OpenAI chaqiruvi bu muhitda sinab ko‘rilmagan: API so‘rov testlari **mock** bilan bajarilgan.

## Texnik sinov

```
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

Barcha mavjud dars va test ma’lumotlari `content/lessons.json` da. Docker boshlanish komandasi avvalgidek. Database migratsiya `app/store.py` orqali amalga oshadi.
