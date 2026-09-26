#!/usr/bin/env bash
# Runs on an Android emulator in CI (see .github/workflows/ci.yml, job "emulator").
# 1) UI tests of the real app. 2) Real SMS sent to the emulator: a scam must raise a warning
# notification, an ordinary text must not.
set -euo pipefail

PKG=com.sentovara.scamcheck
RUNNER="$PKG.test/androidx.test.runner.AndroidJUnitRunner"

./gradlew --no-daemon -q :app:installDebug :app:installDebugAndroidTest
for p in RECEIVE_SMS READ_CONTACTS POST_NOTIFICATIONS; do
  adb shell pm grant "$PKG" "android.permission.$p"
done

run_instrumentation() {
  local out
  out=$(adb shell am instrument -w -e class "$1" "$RUNNER")
  echo "$out"
  grep -q "^OK (" <<<"$out" || { echo "FAILED: $1"; exit 1; }
}

run_instrumentation "$PKG.UiFlowTest"
run_instrumentation "$PKG.SmsSetup"

notifications() { adb shell dumpsys notification --noredact; }

adb emu sms send 5559999 "See you at 6 tonight, I'll bring the snacks"
adb emu sms send 5551234 "Royal Mail: your parcel is on hold. Pay the 1.45 fee: https://rm-redelivery-royalmail.info/pay"

for _ in $(seq 1 30); do
  if notifications | grep -q "Likely scam"; then break; fi
  sleep 2
done
if ! notifications | grep -q "Likely scam"; then
  echo "FAILED: no scam warning after the scam SMS"; notifications | grep -i -A3 scamcheck || true; exit 1
fi
if notifications | grep -q "text from 5559999"; then
  echo "FAILED: the ordinary SMS raised a warning"; exit 1
fi
echo "Emulator smoke test passed: scam SMS warned, ordinary SMS did not."
