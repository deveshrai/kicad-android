#!/usr/bin/env bash
# Build wxWidgets (toolchain/wxWidgets, the same tree as the Android wxQt build) as the native
# macOS Cocoa port, for the native Mac build of KiCad (scripts/build-kicad-mac.sh).
# The Android/Qt patches in that tree are Qt-only and don't affect this port.
set -euo pipefail
source "$(dirname "$0")/env.sh"

SRC="$KA_TOOLCHAIN/wxWidgets"
BUILD="$KA_ROOT/build/wxosx"
PREFIX="$KA_ROOT/build/install/wxosx"

cmake -S "$SRC" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0 \
    -DwxBUILD_TOOLKIT=osx_cocoa \
    -DwxBUILD_SHARED=ON \
    -DwxBUILD_SAMPLES=OFF \
    -DwxBUILD_TESTS=OFF \
    -DwxBUILD_DEMOS=OFF \
    -DwxUSE_WEBVIEW=ON \
    -DwxUSE_OPENGL=ON \
    -DwxUSE_STC=ON \
    -DwxUSE_PROPGRID=ON \
    -DwxUSE_AUI=ON \
    -DwxUSE_RICHTEXT=ON \
    -DwxUSE_LIBJPEG=builtin \
    -DwxUSE_LIBPNG=builtin \
    -DwxUSE_LIBTIFF=builtin \
    -DwxUSE_ZLIB=builtin \
    -DwxUSE_EXPAT=builtin \
    -DwxUSE_REGEX=builtin \
    "$@"

cmake --build "$BUILD"
cmake --install "$BUILD"
