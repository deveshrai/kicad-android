#!/usr/bin/env bash
# Configure and build KiCad (kicad/, branch android) for Android arm64 against the vcpkg deps,
# wxQt and Qt for Android.
# Usage: scripts/build-kicad-android.sh [--configure-only] [ninja targets...]
set -euo pipefail
source "$(dirname "$0")/env.sh"

SRC="$KA_ROOT/kicad"
BUILD="$KA_ROOT/build/kicad-android"
DEPS="$KA_ROOT/deps/vcpkg_installed/arm64-android"
HOSTDEPS="$KA_ROOT/deps/vcpkg_installed/arm64-osx"
WX="$KA_ROOT/build/install/android"

CONFIGURE_ONLY=0
if [ "${1:-}" = "--configure-only" ]; then CONFIGURE_ONLY=1; shift; fi

"$QT_ANDROID_PATH/bin/qt-cmake" -S "$SRC" -B "$BUILD" -G Ninja \
    -DQT_HOST_PATH="$QT_HOST_PATH" \
    -DANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" \
    -DANDROID_NDK_ROOT="$ANDROID_NDK_ROOT" \
    -DANDROID_PLATFORM="android-$KA_ANDROID_API" \
    -DANDROID_ABI="$KA_ANDROID_ABI" \
    -DANDROID_STL=c++_shared \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_FIND_ROOT_PATH="$DEPS;$WX;$QT_ANDROID_PATH" \
    -DCMAKE_PREFIX_PATH="$DEPS;$DEPS/share;$WX" \
    -DCMAKE_PROGRAM_PATH="$HOSTDEPS/tools/glslang;$HOSTDEPS/tools/spirv-tools;$HOSTDEPS/tools/protobuf;$HOSTDEPS/tools/gettext/bin" \
    -DwxWidgets_CONFIG_EXECUTABLE="$WX/bin/wx-config" \
    -DwxWidgets_CONFIG_OPTIONS="--prefix=$WX" \
    -DPYTHON_EXECUTABLE="$(command -v python3)" \
    -DNGSPICE_LIB_NAME=libngspice.so \
    -DOCC_INCLUDE_DIR="$DEPS/include/opencascade" \
    -DKICAD_BUILD_QA_TESTS=OFF \
    -DKICAD_SPICE_QA=OFF \
    -DKICAD_BUILD_I18N=OFF \
    -DKICAD_USE_SENTRY=OFF \
    -DKICAD_UPDATE_CHECK=OFF \
    -DKICAD_BUILD_NATIVE_MODEL_PREVIEW=OFF \
    -DKICAD_WAYLAND=OFF \
    -DKICAD_INSTALL_DEMOS=OFF \
    "$@"

[ "$CONFIGURE_ONLY" = 1 ] && exit 0
cmake --build "$BUILD" -- -k 0 "$@"
