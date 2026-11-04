#!/usr/bin/env bash
# Build Touch.java into a dex and push it.  Run: adb shell CLASSPATH=/data/local/tmp/touch.dex app_process / Touch ...
set -euo pipefail
source "$(dirname "$0")/../../scripts/env.sh" >/dev/null
D="$(cd "$(dirname "$0")" && pwd)"; B="$KA_ROOT/build/touchinject"; mkdir -p "$B"
JAR="$(ls -d "$ANDROID_SDK_ROOT"/platforms/android-*/android.jar | sort -V | tail -1)"
javac -source 11 -target 11 -cp "$JAR" -d "$B" "$D/Touch.java"
"$ANDROID_SDK_ROOT/build-tools/36.0.0/d8" --lib "$JAR" --output "$B" "$B"/Touch.class
mv "$B/classes.dex" "$B/touch.dex"
adb -s "${KA_SERIAL:-RZGL62ZE1AZ}" push "$B/touch.dex" /data/local/tmp/touch.dex
