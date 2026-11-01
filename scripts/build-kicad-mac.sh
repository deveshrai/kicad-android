#!/usr/bin/env bash
# Native macOS (arm64, wxOSX/Cocoa, Metal canvas) build of the same KiCad tree (kicad/, branch
# android), kept alongside the Android port as a desktop reference and for running kicad-cli
# on the Mac.  Needs: deps-mac (vcpkg arm64-osx) and scripts/build-wxosx.sh.
#
# Usage: scripts/build-kicad-mac.sh [--configure-only] [ninja targets...]
#   Result: build/install/kicad-mac/KiCad.app, copied to dist/mac/KiCad-<version>.app
set -euo pipefail
source "$(dirname "$0")/env.sh"

SRC="$KA_ROOT/kicad"
BUILD="$KA_ROOT/build/kicad-mac"
PREFIX="$KA_ROOT/build/install/kicad-mac"
DEPS="$KA_ROOT/deps-mac/vcpkg_installed/arm64-osx"
WX="$KA_ROOT/build/install/wxosx"
LETTER="$(tr -d '[:space:]' < "$KA_ROOT/android/BUILD_LETTER")"

# vcpkg's static archives don't record their dependencies and KiCad's find modules link only
# the top-level library: append the static closure (as in the Android build).
STATIC_PKGS="cairo fontconfig harfbuzz freetype2 libcurl libgit2 libzstd sqlite3 icu-uc icu-i18n odbc libjpeg"
STATIC_LIBS="$(PKG_CONFIG_LIBDIR="$DEPS/lib/pkgconfig" pkgconf --define-variable=prefix="$DEPS" \
    --static --libs $STATIC_PKGS | tr ' ' '\n' | grep -vxE -- '-lc\+\+|-pthread' | tr '\n' ' ')"

CONFIGURE_ONLY=0
if [ "${1:-}" = "--configure-only" ]; then CONFIGURE_ONLY=1; shift; fi

cmake -S "$SRC" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0 \
    -DKICAD_VERSION_EXTRA="$LETTER" \
    -DCMAKE_PREFIX_PATH="$DEPS;$DEPS/share;$WX" \
    -DCMAKE_PROGRAM_PATH="$DEPS/tools/glslang;$DEPS/tools/spirv-tools;$DEPS/tools/spirv-cross;$DEPS/tools/protobuf;$DEPS/tools/gettext/bin" \
    -DwxWidgets_CONFIG_EXECUTABLE="$WX/bin/wx-config" \
    -DwxWidgets_CONFIG_OPTIONS="--prefix=$WX" \
    -DSQLite3_ROOT="$DEPS" \
    -DPYTHON_EXECUTABLE="$(command -v python3)" \
    -DCMAKE_C_STANDARD_LIBRARIES="$STATIC_LIBS" \
    -DCMAKE_CXX_STANDARD_LIBRARIES="$STATIC_LIBS" \
    -DOCC_INCLUDE_DIR="$DEPS/include/opencascade" \
    -DNGSPICE_LIB_NAME=libngspice.0.dylib \
    -DKICAD_BUILD_QA_TESTS=OFF \
    -DKICAD_SPICE_QA=OFF \
    -DKICAD_BUILD_I18N=OFF \
    -DKICAD_USE_SENTRY=OFF \
    -DKICAD_UPDATE_CHECK=OFF \
    -DKICAD_INSTALL_DEMOS=OFF \
    "$@"

[ "$CONFIGURE_ONLY" = 1 ] && exit 0
cmake --build "$BUILD" -- -k 0

# Install.  wxWidgets is referenced through @rpath with no LC_RPATH pointing at it, so tell the
# dependency scan where to look (cmake/InstallSteps/InstallMacOS.cmake), and as the scan still
# misses indirect wx libraries, copy all of them into the bundle and redo the relocation step.
# ngspice is built without XSPICE code models; the install step expects their directory.
mkdir -p "$DEPS/lib/ngspice"
export KICAD_MACOS_DEPENDENCY_DIRS="$WX/lib:$DEPS/lib"
cmake --install "$BUILD" || true
APP="$PREFIX/KiCad.app"
cp -a "$WX"/lib/libwx_*.dylib "$APP/Contents/Frameworks/"
printf '%s\n' 'cmake_policy( SET CMP0012 NEW )' \
    "set( KICAD_CMAKE_MODULE_PATH \"$SRC/cmake\" )" \
    "include( \"$SRC/cmake/InstallSteps/RefixupMacOS.cmake\" )" \
    "refix_kicad_bundle( \"$APP\" )" > "$BUILD/refix.cmake"
cmake -P "$BUILD/refix.cmake"
codesign --force --deep -s - "$APP"
"$APP/Contents/MacOS/kicad-cli" version

VER="10.99$LETTER"
mkdir -p "$KA_ROOT/dist/mac"
rm -rf "$KA_ROOT/dist/mac/KiCad-$VER.app"
cp -R "$PREFIX/KiCad.app" "$KA_ROOT/dist/mac/KiCad-$VER.app"
echo "dist/mac/KiCad-$VER.app"
