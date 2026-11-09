# MedStudy AI 3.0 Beta — Android roadmap and safety checklist

## Scope of this development branch

Working branch: `feature/android-v3`
Based on: `feature/mobile-auth-v2` (Android 2.0 pilot).
The existing installed Android APK, Telegram Mini App, production Railway
service and `main` are **not changed**.

### Implemented in source

- Name/branding: **MedStudy AI 3.0 · Beta** on the Flutter dashboard,
  settings page and test APK launcher.
- Modern, layered gradient and shadow for the study dashboard.
- Touch-controlled **3D schematic dental arch**: rotate, pinch to zoom,
  double-tap or button to reset. Renders locally; no unlicensed external
  medical models or network assets are embedded.
- Clear disclaimer: the simplified teaching geometry is **not** suitable
  for diagnosis or anatomically precise clinical education.
- Read-only student profile (display name and email) from the approved
  user's authenticated `/api/mobile/me` response.
- Fix: previous Android pilot wrote `read:` and `best:` values outside
  the student-scoped storage keys. New study progress is stored per account.
- Backend account-scoped `GET/PUT /api/mobile/progress`:
  approved bearer token required; arbitrary lesson IDs are rejected;
  scores cannot exceed the topic's number of questions; stored values
  merge as completed=OR and best_score=maximum, and revoked tokens fail.
- Mobile client stores progress locally first, then attempts HTTPS sync.
  It can merge newer server scores with its local values.
- Regression tests for 3D interaction, account scoping, backend permissions
  and retained existing study catalog.

## Important boundaries

**Not yet deployed:** Railway mobile staging still follows
`feature/mobile-auth-v2`. The new `/api/mobile/progress` endpoints
exist **only in this feature branch**, so the initial 3.0 test APK will
fall back to local progress until the backend is safely upgraded.
Do not advertise cross-device progress sync until staging is deployed and
an end-to-end test passes.

**Existing old progress:** Android 2.0 may have written unscoped progress
to legacy keys; that data cannot safely be assigned to one of multiple
student accounts automatically. Do not copy it into another account.

**Score integrity:** This is beta progress persistence, not server-verified
exam grading. A modified client could submit a forged plausible score.
Before using scores for certificates, competitions, grades or payments,
evaluate attempts and answers on the server rather than trusting clients.

**Not yet complete:** password recovery/email verification, account
deletion, a full review of all medical lesson content, verified 3D anatomy
assets, server-side anti-cheating, and public Google Play publication.

## Release strategy

1. Keep existing stable Android version installed while reviewing v3 test results.
2. Use GitHub Actions Flutter + backend suites on `feature/android-v3`.
3. Once the Android APK passes, install on a **test device** or emulator
   (debug keystore may differ between ephemeral runners; uninstalling an
   older APK can remove local progress).
4. Validate UI, 3D gestures, logins, lesson reading and quiz scores.
5. Agree on a safe staging upgrade plan with persistent DB backup and rollback
   before deploying `feature/android-v3` backend and enabling sync.
6. Add password recovery, account deletion and verified anatomy assets.
7. Plan a stable signed release with a persistent signing key and migration
   strategy before Play Store submission.

Do not merge into `main` or switch production Telegram
webhooks as part of Android 3.0 beta testing.
