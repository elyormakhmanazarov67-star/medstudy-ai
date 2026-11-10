# MedStudy AI 2.0 — ruxsatli Android/iOS mobil ilova

Kod: feature/mobile-auth-v2. Ishlab turgan Telegram Mini App va Railway production o'zgarmagan.

## Talabalarga ruxsat
1. Talaba ilovani ochganda darslar va testlar berilmaydi.
2. Ism, email, parol bilan ro'yxatdan o'tadi: status pending.
3. Telegram admin arizani ko'radi: /mobilepending.
4. Admin /mobileapprove ID yoki Tasdiqlash tugmasi bilan tasdiqlaydi.
5. Shundan keyingina talaba login qiladi va serverdan darslar, testlar, anatomiya sxemalarini oladi.
6. /mobilereject ID arizani rad etadi; /mobilerevoke ID oldin berilgan ruxsat va faol sessiyalarni bekor qiladi.

Yangi serverga bot ulanganida admin Telegramga yangi ariza haqida Tasdiqlash / Rad etish tugmali xabar oladi. Bu buyruqlar HAZIRGI production botda hali faol emas. Bir Telegram botning webhookini staging va productionga bir vaqtda ulash mumkin emas; ishlab turgan webhookni o'zgartirmaslik kerak.

## Himoya
- Flutter APK ichiga darslar JSON va anatomiya SVG fayllari joylanmaydi. GitHub'da tarixiy assets manba sifatida qoladi, APKga kirmaydi.
- /api/mobile/catalog va /api/mobile/diagrams/{id} endpointlari faqat tasdiqlangan akkauntning bearer tokeni bilan ishlaydi.
- Har ishga tushirish va ilovaga qaytishda sessiya server bilan tekshiriladi; internet yo'q bo'lsa, kontent berilmaydi.
- Parollar scrypt xeshi bilan, sessiyalar SHA-256 xeshlangan tokenlar bilan saqlanadi. Telefon tokenni secure storage orqali saqlaydi.
- Progress qurilmada mobil akkauntga alohida bog'lanadi. Server sinxronizatsiyasi keyingi bosqich.
- Materiallar mustaqil o'quv konspektlari; original PDF/Word/PPT fayllari APKda yo'q.

## Test server
Productionga deploy qilmang. Mustaqil staging API, HTTPS va persistent DB kerak. Yangi backend branch stagingga o'rnatilmagan.

Flutterda:
    cd mobile
    flutter create . --platforms=android,ios --project-name medstudy_ai --org uz.medstudy
    flutter pub get
    flutter run --dart-define=MEDSTUDY_API_URL=https://YOUR-STAGING-DOMAIN

Android internet permission manifestga qo'shilishi kerak; GitHub Actions buni avtomatik qiladi.
GitHub Actions ichidagi Android APK xavfsiz defaultga ega: server URL berilmagan bo'lsa, darslar bloklanadi.
iOS build uchun Mac, Xcode va signing kerak.

## API yo'llari
POST /api/mobile/register; POST /api/mobile/login; GET /api/mobile/me; POST /api/mobile/logout;
GET /api/mobile/catalog; GET /api/mobile/diagrams/{id};
GET /api/mobile/admin/pending; POST /api/mobile/admin/accounts/{id}/approve;
POST /api/mobile/admin/accounts/{id}/reject; POST /api/mobile/admin/accounts/{id}/revoke.

Haqiqiy talabalarni qabul qilishdan avval email verification, parolni tiklash, foydalanuvchi ma'lumotlarini o'chirish va qo'shimcha security review talab etiladi.
