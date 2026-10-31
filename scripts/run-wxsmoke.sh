#!/usr/bin/env bash
# Installs and launches the wxQt smoke-test APK on the emulator, then drives keyboard and
# mouse input through adb and prints what the app reported (WXSMOKE lines in logcat).
set -euo pipefail
source "$(dirname "$0")/env.sh"

APK="$KA_ROOT/build/wxsmoke/android-build/wxsmoke.apk"
PKG=org.kicad.wxsmoke
SHOTS="$KA_ROOT/build/screenshots"
mkdir -p "$SHOTS"

adb -e install -r -g "$APK"
adb -e logcat -c
adb -e shell am start -n "$PKG/org.qtproject.qt.android.bindings.QtActivity"
sleep 6
adb -e exec-out screencap -p > "$SHOTS/wxsmoke-launch.png"

# Mouse: hover, left click, right click and wheel inside the input panel
adb -e shell input mouse tap 1280 900
adb -e shell input mouse motionevent HOVER_MOVE 1300 950 || true
adb -e shell input mouse scroll 1280 900 --axis VSCROLL,-1 || true

# Keyboard: printable keys and a Ctrl chord, sent as physical keyboard events
adb -e shell input keyboard text kicad
adb -e shell input keyboard keycombination KEYCODE_CTRL_LEFT KEYCODE_Z || true
adb -e shell input keyboard keyevent KEYCODE_ESCAPE

sleep 2
adb -e exec-out screencap -p > "$SHOTS/wxsmoke-input.png"
adb -e logcat -d | grep -E "WXSMOKE|FATAL|AndroidRuntime" | tail -40
echo "screenshots in $SHOTS"
