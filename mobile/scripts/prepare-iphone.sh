#!/usr/bin/env bash
set -euo pipefail

# Run on a Mac:
#   bash mobile/scripts/prepare-iphone.sh
# Does not collect Apple credentials or modify production services.

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "MedStudy AI iPhone setup requires a Mac with Xcode. Windows/Linux cannot sign/install an iOS app." >&2
  exit 2
fi

for program in xcodebuild xcrun plutil flutter; do
  if ! command -v "$program" >/dev/null 2>&1; then
    echo "Missing $program. Install Xcode (including command-line tools) and Flutter first." >&2
    exit 2
  fi
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MOBILE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$MOBILE_DIR"

echo "== Xcode =="
xcodebuild -version

echo "== Generate iPhone project =="
flutter create . --platforms=ios --project-name medstudy_ai --org uz.medstudy

echo "== Resolve Flutter and iOS plugins =="
flutter pub get

echo "== Set iPhone Home Screen name =="
plutil -replace CFBundleDisplayName -string "MedStudy AI" ios/Runner/Info.plist
plutil -lint ios/Runner/Info.plist

echo "== Flutter iOS readiness check =="
flutter doctor -v

echo "== Available devices =="
flutter devices

cat <<'STEPS'

NEXT STEPS ON YOUR OWN MAC:
1. Connect/unlock your iPhone and choose Trust This Computer.
2. Enable Developer Mode in Settings > Privacy & Security if prompted.
3. Open mobile/ios/Runner.xcworkspace in Xcode.
4. Select Runner > Signing & Capabilities > Automatically manage signing.
5. Add your Apple Account to Xcode locally and select your Personal Team
   (or your Apple Developer Program team).
6. Set a unique bundle identifier if Xcode reports a signing conflict.
7. In a Terminal in the mobile directory run:
      flutter devices
      flutter run -d DEVICE_ID --dart-define=MEDSTUDY_API_URL=https://medstudy-ai-mobile-staging-staging.up.railway.app

Use the staging HTTPS URL above; do not point your test build to
production Telegram. Don't paste Apple passwords or certificates into chat or Git.
STEPS
