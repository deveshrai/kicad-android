#!/usr/bin/env bash
# Advance the Android build letter (10.99a -> 10.99b -> ...) and push it into the KiCad build's
# version string. Usage: scripts/bump-build.sh [letter]
set -euo pipefail
source "$(dirname "$0")/env.sh"
F="$KA_ROOT/android/BUILD_LETTER"
CUR="$(tr -d '[:space:]' < "$F")"
NEXT="${1:-$(echo "$CUR" | tr 'a-y' 'b-z')}"
echo "$NEXT" > "$F"
cmake -DKICAD_VERSION_EXTRA="$NEXT" "$KA_ROOT/build/kicad-android" >/dev/null
echo "build letter: $CUR -> $NEXT"
