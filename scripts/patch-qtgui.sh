#!/usr/bin/env bash
# Binary patch for Qt 6.12.0's prebuilt libQt6Gui (android arm64): skip the deep copy of the whole
# backing store image on every widget flush.
#
# QBackingStoreDefaultCompositor::toTexture(const QImage &, ...) does `image.detach()` before
# uploading the dirty rectangle, i.e. it copies the full window image (2448x1848x4 = 18 MB on a
# Z Fold, about the same on a tablet) for every flush, such as each status bar update while the
# pointer moves: 15-20% of the main thread while routing in pcbnew.  In this flush path the upload
# is recorded and consumed inside the same flush() call (Vulkan copies to a staging buffer while
# enqueueing, GLES at endFrame) and nothing paints into the image in between, so sharing the
# pixels is safe.  The patch turns that one `bl QImage::detach()` into a NOP.
#
# The stock library is kept as *.orig.  The patch checks the exact bytes first, so it refuses to
# touch a different build.  Run before build-kicad-apk.sh (it is idempotent).
set -euo pipefail
source "$(dirname "$0")/env.sh" >/dev/null

LIB="$QT_ANDROID_PATH/lib/libQt6Gui_arm64-v8a.so"
OFF=$((0x3ea158))
CALL="aa430e94"        # bl QImage::detach()@plt
NOP="1f2003d5"         # nop

cur="$(xxd -p -s $OFF -l 4 "$LIB")"
if [ "$cur" = "$NOP" ]; then echo "libQt6Gui already patched"; exit 0; fi
[ "$cur" = "$CALL" ] || { echo "unexpected bytes $cur at 0x3ea158 in $LIB: not the expected Qt 6.12.0 build" >&2; exit 1; }
# Make sure it is the call in the compositor's no-conversion branch (preceded by add x0, sp, #0x10)
[ "$(xxd -p -s $((OFF - 4)) -l 4 "$LIB")" = "e0430091" ] || { echo "context mismatch" >&2; exit 1; }

[ -f "$LIB.orig" ] || cp -p "$LIB" "$LIB.orig"
printf '\x1f\x20\x03\xd5' | dd of="$LIB" bs=1 seek=$OFF conv=notrunc status=none
echo "patched $LIB (detach at 0x3ea158 -> nop)"
