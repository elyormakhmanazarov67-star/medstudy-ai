# MedStudy AI 2.0 — First iOS Simulator Build (SUCCESS)

## Verified result — 2026-11-09

- Development branch: `feature/ios-v2`
- GitHub Actions run: https://github.com/elyormakhmanazarov67-star/medstudy-ai/actions/runs/42677800334
- Workflow result: **SUCCESS**
- Mac Xcode detected, Flutter/Dart analysis and widget tests passed, and native iOS Simulator compilation completed.
- Artifact: `medstudy-ai-ios-SIMULATOR-NOT-IPHONE` (~55.3 MB archive).
- The artifact expires on **2026-11-16** unless rebuilt.
- Build targets the **Railway staging** HTTPS API, not the production Telegram server.
- The build checked that private lesson JSON and anatomy assets were **not** directly packaged in the app.

**Important:** This is an **unsigned iOS Simulator app**, not an IPA and not installable on a physical iPhone. Simulator compilation confirms project buildability; it is not proof of correct behavior on a real device.

## Next: test on a real iPhone via Xcode on a Mac

1. On a Mac, install Xcode and the current Flutter SDK; run `flutter doctor` and resolve any iOS/Xcode issues.
2. Clone the private repository, check out `feature/ios-v2`, then open Terminal in its `mobile/` directory.
3. From the repository root, use the preparation helper on macOS (no Apple credentials are requested):

   ```bash
   bash mobile/scripts/prepare-iphone.sh
   ```

   This checks for Xcode, generates the native iOS project, downloads Flutter dependencies, sets the home-screen name to **MedStudy AI**, displays `flutter doctor` results, and lists connected devices.

4. Connect and unlock your iPhone, trust the Mac, and enable **Developer Mode** as directed by Xcode.
5. Open `ios/Runner.xcworkspace` in Xcode. In **Signing & Capabilities**, select a valid Apple development team and a unique bundle identifier for your account. Don't put certificates, profiles, tokens, or Apple passwords in Git.
6. List targets with `flutter devices`, then start an on-device **debug** run with:

   ```bash
   flutter run -d YOUR_DEVICE_ID --dart-define=MEDSTUDY_API_URL=https://medstudy-ai-mobile-staging-staging.up.railway.app
   ```

7. Confirm registration, administrator approval, sign-in, lessons, questions, diagrams, dark theme, and swipe-back on the physical iPhone. Progress is currently local per device and does **not** synchronize between Android and iOS.

A free **Apple Personal Team** in Xcode supports limited testing on your own iPhone; Apple states personal provisioning profiles expire after **7 days**, after which rebuilding and reinstalling may be necessary. For TestFlight and App Store distribution you must enroll in the Apple Developer Program. Windows/BlueStacks cannot compile or sign a physical iPhone build. The existing 55.3 MB artifact is for the iOS Simulator only, and cannot be installed on a physical iPhone.

**Required decision:** Do you have access to a Mac with Xcode (your own or one you can use)? If not, signing with a Personal Team cannot be completed from Windows, and a generic GitHub macOS runner without your own provisioning access will not solve that on its own. We can keep developing the iPhone UI while obtaining a legitimate macOS build/signing setup.

## Safety boundaries

- No signing credentials or Apple ID secrets are stored in this repository.
- Never share Apple or Railway admin passwords in chat.
- Leave `main`, the production Telegram bot and the working Android APK unchanged.
- The iOS Simulator workflow uses **macOS GitHub Actions minutes** in a private repo; more cloud runs may be billable. It is triggered for a branch-specific explicit commit tag only, not for ordinary code changes.

## Current real-device status

- Native iOS Simulator compilation: **passed** (run `42677800334`).
- Repository setup helper for Mac: [`mobile/scripts/prepare-iphone.sh`](../mobile/scripts/prepare-iphone.sh).
- Physical iPhone signed build: **not yet produced**, no Apple team/device signing has been configured.
- No extra macOS GitHub Actions build was started for the preparation script.
