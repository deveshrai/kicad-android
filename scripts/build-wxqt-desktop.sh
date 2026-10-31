#!/usr/bin/env bash
# Phase 1: build wxWidgets (wxQt port) against desktop Qt 6 on macOS, so KiCad-on-wxQt
# issues can be debugged on the host before going to a device.
set -euo pipefail
source "$(dirname "$0")/env.sh"

SRC="$KA_TOOLCHAIN/wxWidgets"
BUILD="$KA_ROOT/build/wxqt-desktop"
PREFIX="$KA_ROOT/build/install/wxqt-desktop"

cmake -S "$SRC" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_PREFIX_PATH="$QT_HOST_PATH" \
    -DwxBUILD_TOOLKIT=qt \
    -DwxBUILD_SHARED=ON \
    -DwxBUILD_SAMPLES=SOME \
    -DwxUSE_WEBVIEW=ON \
    -DwxUSE_MEDIACTRL=OFF \
    -DwxUSE_JOYSTICK=OFF \
    -DwxUSE_OPENGL=ON \
    -DwxUSE_STC=ON \
    -DwxUSE_PROPGRID=ON \
    -DwxUSE_AUI=ON \
    -DwxUSE_RICHTEXT=ON \
    "$@"

cmake --build "$BUILD"
cmake --install "$BUILD"
