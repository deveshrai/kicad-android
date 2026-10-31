#!/usr/bin/env bash
# Creates (once) and boots the KiCad test tablet: 2560x1600 landscape, arm64, API 37,
# hardware keyboard enabled so host keyboard/mouse reach the guest as physical KBM devices.
#
# Must run outside Claude Code's command sandbox: the emulator needs Hypervisor.framework
# (hvf). Without it, it falls back to software emulation and its watchdog kills it.
# Run it yourself, e.g. `! scripts/emulator.sh` in the Claude Code prompt.
#
# All adb calls use -e: a physical device may also be attached.
# Usage: scripts/emulator.sh [extra emulator args, e.g. -no-window -wipe-data]
set -euo pipefail
source "$(dirname "$0")/env.sh"

AVD=KiCad_Tablet
AVDROOT="$HOME/.android/avd"
AVDDIR="$AVDROOT/$AVD.avd"
SYSIMG="system-images/android-37.0/google_apis_playstore/arm64-v8a/"

# The cmdline-tools avdmanager in this SDK writes placeholder values (<temp>, <build>) that
# crash emulator 37.x, so write the AVD by hand.  The emulator fills in other defaults.
if [ ! -f "$AVDDIR/config.ini" ]; then
    mkdir -p "$AVDDIR"
    cat > "$AVDROOT/$AVD.ini" <<EOF
avd.ini.encoding=UTF-8
path=$AVDDIR
path.rel=avd/$AVD.avd
target=android-37.0
EOF
    cat > "$AVDDIR/config.ini" <<EOF
AvdId=$AVD
avd.ini.displayname=KiCad Tablet API 37
avd.ini.encoding=UTF-8
abi.type=arm64-v8a
hw.cpu.arch=arm64
hw.cpu.ncore=4
image.sysdir.1=$SYSIMG
tag.id=google_apis_playstore
tag.display=Google Play
PlayStore.enabled=true
hw.device.name=pixel_tablet
hw.device.manufacturer=Google
hw.lcd.width=2560
hw.lcd.height=1600
hw.lcd.density=320
hw.initialOrientation=landscape
hw.keyboard=yes
hw.mainKeys=no
hw.ramSize=4096
disk.dataPartition.size=16G
hw.gpu.enabled=yes
hw.gpu.mode=auto
showDeviceFrame=no
skin.dynamic=yes
skin.name=2560x1600
skin.path=_no_skin
EOF
fi

"$ANDROID_HOME/emulator/emulator" -avd "$AVD" -no-snapshot-save -no-boot-anim "$@" &
adb -e wait-for-device
until [ "$(adb -e shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do sleep 2; done
echo "emulator booted: $(adb -e shell getprop ro.product.model | tr -d '\r'), API $(adb -e shell getprop ro.build.version.sdk | tr -d '\r')"
