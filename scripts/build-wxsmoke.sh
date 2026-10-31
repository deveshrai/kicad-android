#!/usr/bin/env bash
# Builds the wxQt smoke-test APK (android/wxsmoke) against the Android wx install.
set -euo pipefail
source "$(dirname "$0")/env.sh"

BUILD="$KA_ROOT/build/wxsmoke"
WX_PREFIX="$KA_ROOT/build/install/android"

"$QT_ANDROID_PATH/bin/qt-cmake" -S "$KA_ROOT/android/wxsmoke" -B "$BUILD" -G Ninja \
    -DQT_HOST_PATH="$QT_HOST_PATH" \
    -DANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" \
    -DANDROID_NDK_ROOT="$ANDROID_NDK_ROOT" \
    -DANDROID_PLATFORM="android-$KA_ANDROID_API" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_FIND_ROOT_PATH="$WX_PREFIX;$QT_ANDROID_PATH" \
    -DwxWidgets_DIR="$WX_PREFIX/lib/cmake/wxWidgets-3.3"

cmake --build "$BUILD" --target apk
find "$BUILD" -name "*.apk" -newer "$KA_ROOT/android/wxsmoke/smoke.cpp"
