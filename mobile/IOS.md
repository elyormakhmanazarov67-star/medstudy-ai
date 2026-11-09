# MedStudy AI 2.0 — iOS development

This uses the same Flutter code as the Android app. **No duplicate student
accounts, backend, or admin site are needed.** iPhone-only changes stay on
`feature/ios-v2`, branched from the working `feature/mobile-auth-v2` Android
pilot. Railway staging remains on the Android branch and production Telegram
remains untouched.

## Current scope

- Student registration with name, email, and password inside the iOS app.
- Administrator approval through the existing staging web dashboard.
- Sign in and fetch authorized course catalog, lesson questions, diagrams.
- Local per-account learning progress (not yet synced between phones).
- Green/white or green/dark visual theme.
- AI Ustoz, subscriptions, and App Store publication are **not yet implemented**.

Staging API: `https://medstudy-ai-mobile-staging-staging.up.railway.app`
Admin panel: `https://medstudy-ai-mobile-staging-staging.up.railway.app/mobile-admin`


## iPhone implementation stage 1

- Reuse the same HTTPS mobile account API and existing admin approvals.
- Show a `CupertinoTabBar` on iOS, `NavigationBar` on Android.
- Use iOS interactive back-swipe page routes for subjects, lessons and tests.
- Apply iPhone keyboard autofill for name, email and password.
- Test Cupertino routes and tab navigation on the Linux Flutter runner; these
  are widget tests, **not** a native iOS build or a substitute for device tests.
- Android builds/tests run from `feature/ios-v2` too, to catch regressions.
- Only the installed Android debug APK is frozen as our baseline, not the
  iOS code branch. No app-store deployment or Apple credentials are added.

### What is still blocked

A real iPhone IPA needs a macOS/Xcode build, provisioning and signing.
The simulator-only macOS workflow is deliberately manual because GitHub
macOS runners for private repositories can incur charges. GitHub does not
normally expose its manual dispatch button before the workflow exists on
the default branch. We will not alter `main` simply to expose
that button or automatically incur cloud macOS costs.

**Windows cannot compile/sign an iPhone IPA by itself.** From a Mac, run
the Flutter commands below and use Xcode with an Apple ID to sign a real-device
debug build. This is not needed while developing shared Dart UI and tests.


## iPhone implementation stage 2

- Student sign-in and registration now use native-styled Cupertino action
  buttons on iOS and retain Material buttons on Android.
- Forms validate fields while the student types and support platform
  autofill, including iCloud Keychain on eligible iPhones.
- The app asks the OS to finish its autofill/save-password flow only after
  receiving an accepted registration request or successful sign-in.
- iOS tab/navigation, page-route, and account-action widget tests run in the
  ordinary Flutter CI jobs. These tests do **not** claim an iOS Simulator build.
- Both branches now run HTTPS staging smoke checks, without editing the
  Railway backend or admin-approval database.

Next, a real iOS Simulator build must be run on macOS with Xcode. The manual
macOS workflow stays intentionally disabled until the owner chooses a runner
and accepts any applicable billing. A physical iPhone build still requires
Apple code signing. Android debug APK 76.9 MB remains the installed baseline.

## Build validation (no Apple membership required)

A manual GitHub Actions workflow is available:

`.github/workflows/ios-simulator.yml`

The workflow file is currently on `feature/ios-v2`, not the
repository's default `main` branch. GitHub may **not display its manual
Run workflow button yet**: manual dispatch normally requires the workflow
to be registered on the default branch. Do not merge development code into
production just to make this test runnable. When a safe workflow registration strategy is selected, run it on
the iOS development branch and inspect the unsigned simulator artifact.

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

Android APK already installed, production Telegram bot, staging backend,
and `main` are intentionally unchanged.
