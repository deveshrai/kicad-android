#!/usr/bin/env bash
# Pushes kicad-cli and everything it loads to the emulator under /data/local/tmp/kicad and
# runs it there.  No GUI: Qt uses its offscreen platform plugin.
#
# Usage: scripts/run-kicad-cli.sh [--push] [kicad-cli args...]   (default args: version)
#   --push   (re)copy binaries and libraries first; otherwise reuse what's on the device
set -euo pipefail
source "$(dirname "$0")/env.sh"

BUILD="$KA_ROOT/build/kicad-android"
DEV=/data/local/tmp/kicad
STAGE="$KA_ROOT/build/stage-cli"
NDKLIB="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android"

if [ "${1:-}" = "--push" ]; then
    shift
    rm -rf "$STAGE"
    mkdir -p "$STAGE/bin" "$STAGE/lib" "$STAGE/plugins/platforms" "$STAGE/etc/fonts" "$STAGE/cache"

    cp "$BUILD/kicad/kicad-cli" "$STAGE/bin/"
    # kifaces are loaded from the executable's directory
    find "$BUILD" -name "_*.kiface" -exec cp {} "$STAGE/bin/" \;
    find "$BUILD" -name "*.so" -not -path "*/CMakeFiles/*" -exec cp {} "$STAGE/lib/" \;
    cp "$KA_ROOT"/build/install/android/lib/libwx_*.so "$STAGE/lib/"
    cp "$KA_ROOT"/deps/vcpkg_installed/arm64-android/lib/*.so "$STAGE/lib/"
    cp "$NDKLIB/libc++_shared.so" "$STAGE/lib/"

    for m in Core Gui Widgets OpenGL OpenGLWidgets Test PrintSupport; do
        cp "$QT_ANDROID_PATH/lib/libQt6${m}_arm64-v8a.so" "$STAGE/lib/"
    done
    cp "$QT_ANDROID_PATH/plugins/platforms/libplugins_platforms_qoffscreen_arm64-v8a.so" \
       "$STAGE/plugins/platforms/"

    # KiCad's stock data (schemas, templates, drawing sheets); from a DESTDIR install
    SHARE="$KA_ROOT/build/install/kicad-android/usr/local/share/kicad"
    [ -d "$SHARE" ] || DESTDIR="$KA_ROOT/build/install/kicad-android" cmake --install "$BUILD" >/dev/null
    mkdir -p "$STAGE/share"
    cp -R "$SHARE" "$STAGE/share/kicad"

    # Debug info makes the kifaces multi-GB; strip it for the device copy
    STRIP="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-strip"
    find "$STAGE/bin" "$STAGE/lib" "$STAGE/plugins" -type f -exec "$STRIP" --strip-debug {} \; 2>/dev/null || true

    # fontconfig: scan Android's system fonts
    cat > "$STAGE/etc/fonts/fonts.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/system/fonts</dir>
  <cachedir>$DEV/cache</cachedir>
</fontconfig>
EOF

    adb -e shell rm -rf "$DEV"
    adb -e push "$STAGE" "$DEV" >/dev/null
    adb -e shell chmod 755 "$DEV/bin/kicad-cli"
    echo "pushed $(du -sh "$STAGE" | cut -f1) to $DEV"
fi

[ $# -eq 0 ] && set -- version

adb -e shell "cd $DEV && \
    LD_LIBRARY_PATH=$DEV/lib \
    QT_QPA_PLATFORM=offscreen \
    QT_PLUGIN_PATH=$DEV/plugins \
    FONTCONFIG_FILE=$DEV/etc/fonts/fonts.conf \
    KICAD_STOCK_DATA_HOME=$DEV/share/kicad \
    HOME=$DEV/home \
    XDG_CONFIG_HOME=$DEV/home/.config \
    $DEV/bin/kicad-cli $*"
