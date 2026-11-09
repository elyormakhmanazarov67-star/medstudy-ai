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
3. Generate the iOS platform project and dependencies:

   ```bash
   flutter create . --platforms=ios --project-name medstudy_ai --org uz.medstudy
   flutter pub get
   ```

4. Connect and unlock your iPhone, trust the Mac, and enable **Developer Mode** as directed by Xcode.
5. Open `ios/Runner.xcworkspace` in Xcode. In **Signing & Capabilities**, select a valid Apple development team and a unique bundle identifier for your account. Don't put certificates, profiles, tokens, or Apple passwords in Git.
6. List targets with `flutter devices`, then start an on-device **debug** run with:

   ```bash
   flutter run -d YOUR_DEVICE_ID --dart-define=MEDSTUDY_API_URL=https://medstudy-ai-mobile-staging-staging.up.railway.app
   ```

7. Confirm registration, administrator approval, sign-in, lessons, questions, diagrams, dark theme, and swipe-back on the physical iPhone. Progress is currently local per device and does **not** synchronize between Android and iOS.

A personal Apple development team may allow limited self-device testing. TestFlight and App Store distribution require the corresponding Apple Developer Program setup and review. Windows/BlueStacks cannot compile or sign a real iPhone application.

## Safety boundaries

- No signing credentials or Apple ID secrets are stored in this repository.
- Never share Apple or Railway admin passwords in chat.
- Leave `main`, the production Telegram bot and the working Android APK unchanged.
- The iOS Simulator workflow uses **macOS GitHub Actions minutes** in a private repo; more cloud runs may be billable. It is triggered for a branch-specific explicit commit tag only, not for ordinary code changes.
