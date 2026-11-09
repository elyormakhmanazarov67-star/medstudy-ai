# MedStudy AI — Flutter mobil ilovasi

Android va iOS uchun boshlang'ich **offline mobil MVP**. Telegram bot va Railway
serverlarini o'zgartirmaydi. Kod alohida \`feature/native-mobile-mvp\` shoxida.

## Birinchi versiyada
- 6 fan, 81 mavzu, 631 test savoli (joriy MedStudy AI katalogidan)
- 14 anatomik SVG sxema, lotincha anatomik belgilar
- O'zbek lotin yozuvida ma'ruza matnlari va test izohlari
- O'qilgan darslar va testning eng yaxshi natijalari qurilmada saqlanadi
- Oq-yashil va qora-yashil ko'rinishlar
- Dars va testlar faqat ilova ichida; asl PDF/Word/PPT yuklab olish yo'q

**Hozirgi cheklov:** bu offline MVP. Mustaqil akkaunt, xavfsiz server
sinxronizatsiyasi, jonli AI Ustoz, Pro to'lov va push xabarnomalar hali
ulanmagan. Mavjud backend Telegram initData talab qiladi, shuning uchun
uni mobil akkauntga xavfsiz moslashtirish alohida ish bo'ladi.

## Flutter bilan ishga tushirish

\`\`\`sh
cd mobile
flutter create . --platforms=android,ios --project-name medstudy_ai --org uz.medstudy
flutter pub get
flutter run
\`\`\`

Hozircha Android/iOS platforma generator papkalari GitHub'da yo'q:
\`flutter create\` ular uchun birinchi marta kerak. iOS build uchun Mac va
Xcode talab etiladi. Windows kompyuterida Android'ni sinab ko'rish mumkin.

## Kontent manbalari

\`assets/data/lessons.json\` — \`content/lessons.json\` bilan bir xil blob,
14 ta \`assets/illustrations/anat_*.svg\` — mavjud loyiha sxemalari.
O'qituvchi PDF/DOC/PPT fayllari kiritilmaydi; faqat mustaqil qisqa
konspektlar va testlar.

Katalogdagi \`AI_RESEARCH_DRAFT\` va \`USER_SOURCE_DRAFT\` materiallar
mutaxassis tekshiruviga muhtoj. Darslar klinik maslahat o'rnini bosmaydi.


## MedStudy AI 2.0 — mobile login pilot (feature/mobile-auth-v2)
- Flutter: Sozlamalar -> Talaba kabineti -> yangi akkaunt yaratish yoki kirish.
- Server endpoints: POST /api/mobile/register, POST /api/mobile/login, GET /api/mobile/me,
  POST /api/mobile/logout. Parollar scrypt orqali xeshlanadi; sessiya tokenining faqat
  SHA-256 xeshi SQLite'da saqlanadi. 14 kunlik muddati bor.
- Yangi akkauntlar avtomatik ochilmaydi: Telegram administrator tomonidan tasdiqlanadi.
  Admin Mini App'ning autentifikatsiyalangan Telegram HTTP so'rovlari bilan:
  GET /api/mobile/admin/pending,
  POST /api/mobile/admin/accounts/{id}/approve,
  POST /api/mobile/admin/accounts/{id}/revoke.
- Android build uchun HTTPS manzilni `--dart-define=MEDSTUDY_API_URL=https://YOUR-STAGING-DOMAIN`
  sifatida bering. Manzil berilmasa mobil darslar offline ishlaydi, login ulanmaydi.
- Test APK GitHub Actions -> MedStudy AI Mobile Flutter CI -> artifacts.
- Google Play/App Storega tayyor emas: email verification va account recovery yo'q;
  maxsus staging servisida tekshiring, haqiqiy studentlarni hali ommaviy taklif qilmang.
- Production Railway xizmatini o'zgartirmang. Staging'da mustaqil persistent SQLite volume
  yoki boshqa barqaror DB kerak. DATABASE_PATH (yoki MOBILE_AUTH_DB_PATH) doimiy diskka
  ko'rsatishi zarur. Sessions TLS orqali uzatiladi va mobil qurilmada secure storage'da saqlanadi.
- Telegram /api katalog API login bilan avtomatik ishlamaydi: server progress
  sinxronizatsiyasi keyingi bosqich.
