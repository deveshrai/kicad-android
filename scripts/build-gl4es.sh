#!/usr/bin/env bash
# Builds gl4es (https://github.com/ptitSeb/gl4es, MIT; cloned unmodified into toolchain/gl4es)
# for Android arm64.  gl4es implements desktop OpenGL 2.1 (immediate mode, display lists,
# fixed-function lighting) on top of GLES 2, which the KiCad 3D viewer needs: Android has no
# desktop GL.  The result, libGL.so, is shipped in the APK, where glad's loader dlopen()s it.
#
# gl4es is used as-is; its AGENTS.md doesn't accept AI-written changes, so adaptations go on
# the KiCad/wx side.  Run outside the Claude Code sandbox: `! scripts/build-gl4es.sh`
set -euo pipefail
source "$(dirname "$0")/env.sh" >/dev/null

SRC="$KA_ROOT/toolchain/gl4es"
B="$KA_ROOT/build/gl4es-android"
OUT="$KA_ROOT/build/install/android/lib"

echo "gl4es $(git -C "$SRC" log --oneline -1)"
cmake -S "$SRC" -B "$B" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM="android-$KA_ANDROID_API" \
    -DCMAKE_BUILD_TYPE=Release \
    -DANDROID=ON -DNOX11=ON -DUSE_ANDROID_LOG=ON
cmake --build "$B"

LIB="$(find "$SRC/lib" "$B" -name 'libGL.so*' -type f 2>/dev/null | head -1)"
[ -n "$LIB" ] || { echo "libGL.so not found after the build" >&2; exit 1; }
mkdir -p "$OUT"
cp "$LIB" "$OUT/libGL.so"
ls -la "$OUT/libGL.so"
