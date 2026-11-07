# MedStudy AI v0.5 — Entwicklungsplan / Ish rejasi (DRAFT)

**Maqsad:** Talabalar uchun xavfsiz, tekshiriladigan, o‘zbekcha tibbiy ta’lim Mini App. Bu hujjat ish rejasi, tayyor tijoriy funksiyalar tavsifi emas.

## Tekshirilgan v0.4 asos
- FastAPI + Telegram Web App initData tasdiqlash
- 1 fan, 2 mavzu, 22 original test
- SQLite progress va xatolarni takrorlash
- Opt-in AI Ustoz (OpenAI Responses API), savollar soni bo‘yicha kunlik limit
- Railway: production=main; staging=v0.4-test, alohida volume
- Mavjud sinovlar: 15/15 local pass (haqiqiy pullik AI API testi emas)

## v0.5 uchun tartib
1. **Xavfsiz ishlab chiqish:** faqat v0.5-dev branchida kod; production ga avtomatik deploy yo‘q.
2. **Shaxsiy progress:** har bir mavzudagi oxirgi to‘liq test natijasi, takrorlash tavsiyalari va sifatli testlar.
3. **AI Ustoz:** faqat ekspert ko‘rigidan o‘tgan dars fragmentlari, savolga mos manba, shaxsiy va bemor ma’lumotlarini kiritmaslik, xatoga chidamli UI, alohida rozilik.
4. **Kontent bazasi:** fanlarni JSON yoki boshqariladigan kontent sxemasi bilan kengaytirish; mavjud 2 dars sinov materiallari. Yangi fanlar faqat manbasi tekshirilgan original matnlar bilan qo‘shiladi.
5. **Tijoratga tayyorgarlik:** premium uchun ma’lumotlar sxemasi va UI maketi, lekin to‘lovlarni qabul qilishni rasmiy huquqiy, moliyaviy va xavfsizlik tekshiruvidan keyin yoqish.
6. **Sifat nazorati:** avtomatik testlar, Telegram webhook sinovi, staging deploy, foydalanuvchi roziligi, ma’lumotlarni o‘chirish, SQLite backup/restore, hosting xarajatlari.

## Ochilgan muammolar va cheklovlar
- Darslar hali ekspert tomonidan tasdiqlanmagan; sotuvga chiqarmaslik.
- OpenAI API balansi/ruxsatlari va pullik sinov hali tasdiqlanmagan; AI_ENABLED=0 qoldirish.
- AI_DAILY_LIMIT va AI_GLOBAL_DAILY_LIMIT xarajatlar uchun qat’iy dollar limiti emas; loyihaning haqiqiy to‘lov chegaralari alohida talab etiladi.
- Staging test bot uchun alohida token ishlatish; production bot tokenidan nusxa olmaslik.
- Foydalanuvchi ma’lumotlari, ayniqsa voyaga yetmaganlar ma’lumotlari uchun qonuniy asos, maxfiylik va xavfsizlik tekshiruvi talab etiladi.

## Release mezonlari
- [ ] Tanlangan v0.5 funksiyalarining yozma talablari
- [ ] Backend va frontend regressiya sinovlari
- [ ] Staging’da yopiq amaliy test
- [ ] Klinik/tibbiy mazmun ekspert tekshiruvi
- [ ] Xavfsizlik va shaxsiy ma’lumotlar bo‘yicha tekshiruv
- [ ] Production deploydan oldin qo‘lda yakuniy tasdiq
