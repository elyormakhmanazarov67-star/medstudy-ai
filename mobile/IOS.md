# MedStudy AI 2.0 — iOS development

This uses the same Flutter code as the Android app. **No duplicate student
accounts, backend, or admin site are needed.** Changes stay on
`feature/mobile-auth-v2`, separate from the production Telegram bot.

## Current scope

- Student registration with name, email, and password inside the iOS app.
- Administrator approval through the existing staging web dashboard.
- Sign in and fetch authorized course catalog, lesson questions, diagrams.
- Local per-account learning progress (not yet synced between phones).
- Green/white or green/dark visual theme.
- AI Ustoz, subscriptions, and App Store publication are **not yet implemented**.

Staging API: `https://medstudy-ai-mobile-staging-staging.up.railway.app`
Admin panel: `https://medstudy-ai-mobile-staging-staging.up.railway.app/mobile-admin`

## Build validation (no Apple membership required)

A manual GitHub Actions workflow is available:

`.github/workflows/ios-simulator.yml`

The workflow file is currently on `feature/mobile-auth-v2`, not the
repository's default `main` branch. GitHub may **not display its manual
Run workflow button yet**: manual dispatch normally requires the workflow
to be registered on the default branch. Do not merge development code into
production just to make this test runnable. When the development branch is
approved for merging, select the iOS workflow in GitHub Actions, run it on
the iOS development branch, and inspect the unsigned simulator artifact.

It runs on a macOS GitHub runner and builds an unsigned iOS **Simulator**
application. The resulting artifact **cannot be installed on a real iPhone**
or submitted to TestFlight/App Store. This workflow has NO Apple keys, signing
credentials, or automatic publication. It does not run automatically because
private-repository macOS Actions usage can be billed.

When testing locally on a Mac with Xcode:

```bash
cd mobile
flutter create . --platforms=ios --project-name medstudy_ai --org uz.medstudy
flutter pub get
flutter run --dart-define=MEDSTUDY_API_URL=https://medstudy-ai-mobile-staging-staging.up.railway.app
```

For a physical iPhone, Xcode code signing and an Apple account are required.
A free personal Apple developer account may be used for testing your own
phone from a Mac (with restrictions). For TestFlight or App Store distribution,
a paid Apple Developer Program membership and proper signing are required.
No API keys or passwords should be pasted into source code or chat.

## Before distribution

1. Confirm real-device login, approval, lessons, diagram rendering, and quiz
   completion under poor network conditions.
2. Add iOS app icons and app-launch branding.
3. Implement account deletion, password recovery, email verification, data
   privacy disclosures, and user-facing support/contact information.
4. Add server-side progress sync for Android ⇄ iPhone continuity.
5. Decide on Apple Developer enrollment and distribution only when ready.

Production service and `main` are intentionally unchanged.
