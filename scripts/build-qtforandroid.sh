#!/usr/bin/env bash
# Build the patched Qt Android platform plugin (android/qtforandroid) and swap it into the Qt
# install that androiddeployqt packages from (the prebuilt one is kept as *.orig).
set -euo pipefail
source "$(dirname "$0")/env.sh"
BUILD="$KA_ROOT/build/qtforandroid"
"$QT_ANDROID_PATH/bin/qt-cmake" -S "$KA_ROOT/android/qtforandroid" -B "$BUILD" -G Ninja \
    -DQT_HOST_PATH="$QT_HOST_PATH" \
    -DANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" \
    -DANDROID_NDK_ROOT="$ANDROID_NDK_ROOT" \
    -DANDROID_PLATFORM="android-$KA_ANDROID_API" \
    -DANDROID_ABI="$KA_ANDROID_ABI" \
    -DCMAKE_BUILD_TYPE=Release \
    -DQTBASE_SRC="$KA_TOOLCHAIN/qtbase-src"
cmake --build "$BUILD"
P="$QT_ANDROID_PATH/plugins/platforms/libplugins_platforms_qtforandroid_${KA_ANDROID_ABI}.so"
[ -f "$P.orig" ] || cp "$P" "$P.orig"
cp "$BUILD/libplugins_platforms_qtforandroid_${KA_ANDROID_ABI}.so" "$P"
echo "installed $P"
