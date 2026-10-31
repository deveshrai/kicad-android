#!/usr/bin/env bash
# Cross-compile wxWidgets (wxQt port, with patches/wxwidgets applied on branch kicad-android)
# for Android arm64 against Qt for Android.
#
# iconv off: bionic's iconv fails wx's UTF-32 conversions (E2BIG) and wxEntry() hangs;
# wx's built-in converters cover what KiCad needs.
#
# Shared libraries: KiCad loads its kifaces (pcbnew, eeschema, ...) as separate .so modules,
# and each must see the same wx instance.
set -euo pipefail
source "$(dirname "$0")/env.sh"

SRC="$KA_TOOLCHAIN/wxWidgets"
BUILD="$KA_ROOT/build/wxqt-android"
PREFIX="$KA_ROOT/build/install/android"

# qt-cmake chains Qt's Android toolchain onto the NDK's and sets QT_HOST_PATH handling.
"$QT_ANDROID_PATH/bin/qt-cmake" -S "$SRC" -B "$BUILD" -G Ninja \
    -DQT_HOST_PATH="$QT_HOST_PATH" \
    -DANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" \
    -DANDROID_NDK_ROOT="$ANDROID_NDK_ROOT" \
    -DANDROID_PLATFORM="android-$KA_ANDROID_API" \
    -DANDROID_ABI="$KA_ANDROID_ABI" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_FIND_ROOT_PATH="$PREFIX;$QT_ANDROID_PATH" \
    -DwxBUILD_TOOLKIT=qt \
    -DwxBUILD_SHARED=ON \
    -DwxBUILD_SAMPLES=OFF \
    -DwxBUILD_TESTS=OFF \
    -DwxBUILD_DEMOS=OFF \
    -DwxUSE_WEBVIEW=ON \
    -DwxUSE_MEDIACTRL=OFF \
    -DwxUSE_JOYSTICK=OFF \
    -DwxUSE_UIACTIONSIMULATOR=OFF \
    -DwxUSE_SECRETSTORE=OFF \
    -DwxUSE_LIBSDL=OFF \
    -DwxUSE_OPENGL=ON \
    -DwxUSE_STC=ON \
    -DwxUSE_PROPGRID=ON \
    -DwxUSE_AUI=ON \
    -DwxUSE_RICHTEXT=ON \
    -DwxUSE_REGEX=builtin \
    -DwxUSE_EXPAT=builtin \
    -DwxUSE_ZLIB=sys \
    -DwxUSE_LIBICONV=OFF \
    "$@"

cmake --build "$BUILD"
cmake --install "$BUILD"
