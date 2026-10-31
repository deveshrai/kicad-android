#!/usr/bin/env bash
# Build libkimalloc.so: operator new/delete on mimalloc, loaded ahead of libc++_shared.
# See android/kimalloc/kimalloc.cpp for why. mimalloc is compiled as C from its single-file
# build (the vcpkg port compiles it as C++, which would make it depend on libc++).
set -euo pipefail
source "$(dirname "$0")/env.sh"

MI_VERSION=3.5.3
MI_SHA512=ef24d926153eb81c95e6c79c335eed12c6e14523a2dd817faddc3f666909a244eab5f4be43cc01a6d8c8d62b5695d29fb535b3762128cdef50a7ee55302b2886
OUT="$KA_ROOT/build/kimalloc"
SRC="$OUT/src/mimalloc-$MI_VERSION"
T="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/darwin-x86_64"
TARGET="--target=aarch64-linux-android$KA_ANDROID_API"

mkdir -p "$OUT/src"

if [ ! -f "$SRC/src/static.c" ]; then
    curl -sSfL -o "$OUT/src/mimalloc-$MI_VERSION.tar.gz" \
        "https://github.com/microsoft/mimalloc/archive/refs/tags/v$MI_VERSION.tar.gz"
    echo "$MI_SHA512  $OUT/src/mimalloc-$MI_VERSION.tar.gz" | shasum -a 512 -c - >/dev/null
    tar xzf "$OUT/src/mimalloc-$MI_VERSION.tar.gz" -C "$OUT/src"
fi

"$T/bin/clang" $TARGET -O2 -fPIC -DNDEBUG -I "$SRC/include" -c "$SRC/src/static.c" -o "$OUT/mimalloc.o"
"$T/bin/clang++" $TARGET -std=c++20 -O2 -fPIC -shared -fno-exceptions -fno-rtti -nostdlib++ \
    -I "$SRC/include" "$KA_ROOT/android/kimalloc/kimalloc.cpp" "$OUT/mimalloc.o" \
    -Wl,-z,global -Wl,--no-undefined -Wl,-soname,libkimalloc.so -llog \
    -o "$OUT/libkimalloc.so"
