#!/usr/bin/env bash
# Advance the Android build letter (10.99a -> 10.99b -> ...) and push it into the KiCad build's
# version string. Usage: scripts/bump-build.sh [letter]
set -euo pipefail
source "$(dirname "$0")/env.sh"
F="$KA_ROOT/android/BUILD_LETTER"
CUR="$(tr -d '[:space:]' < "$F")"
# a..z, then aa, ab, .. az, ba, .. zz
next_letter() {
    case "$1" in
        z)   echo aa ;;
        ?)   echo "$1" | tr 'a-y' 'b-z' ;;
        zz)  echo "build letters exhausted after zz" >&2; exit 1 ;;
        ?z)  echo "$(echo "${1:0:1}" | tr 'a-y' 'b-z')a" ;;
        ??)  echo "${1:0:1}$(echo "${1:1:1}" | tr 'a-y' 'b-z')" ;;
        *)   echo "bad build letter '$1'" >&2; exit 1 ;;
    esac
}
NEXT="${1:-$(next_letter "$CUR")}"
echo "$NEXT" > "$F"
cmake -DKICAD_VERSION_EXTRA="$NEXT" "$KA_ROOT/build/kicad-android" >/dev/null
echo "build letter: $CUR -> $NEXT"
