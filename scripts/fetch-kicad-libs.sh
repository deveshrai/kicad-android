#!/usr/bin/env bash
# Download the official KiCad symbol/footprint/template libraries and stage them in the layout
# of a desktop install (symbols/, footprints/, template/), for bundling into the APK.
# 3D models are not included (several GB).
#
# Usage: scripts/fetch-kicad-libs.sh [version]   (default 10.0.8)
set -euo pipefail
source "$(dirname "$0")/env.sh"

VER="${1:-${KICAD_LIBS_VERSION:-10.0.8}}"
DL="$KA_ROOT/build/kicad-libs-$VER"
STAGE="$DL/stage-$VER"

if [ -f "$STAGE/.complete" ]; then
    echo "$STAGE"
    exit 0
fi

mkdir -p "$DL"
for r in kicad-symbols kicad-footprints kicad-templates; do
    [ -f "$DL/$r.tar.gz" ] || curl -sSfL -o "$DL/$r.tar.gz" \
        "https://gitlab.com/kicad/libraries/$r/-/archive/$VER/$r-$VER.tar.gz"
done

TMP="$DL/extract.$$"
mkdir -p "$TMP"
for r in kicad-symbols kicad-footprints kicad-templates; do
    tar xzf "$DL/$r.tar.gz" -C "$TMP"
done

NEW="$DL/stage-$VER.new.$$"
mkdir -p "$NEW/template"
mv "$TMP/kicad-symbols-$VER" "$NEW/symbols"
mv "$TMP/kicad-footprints-$VER" "$NEW/footprints"
cp -R "$TMP/kicad-templates-$VER/Projects/." "$NEW/template/"
cp "$TMP/kicad-templates-$VER/Worksheets/"*.kicad_wks "$NEW/template/" 2>/dev/null || true
# Default global library tables, copied by KiCad's first-run setup
cp "$NEW/symbols/sym-lib-table" "$NEW/footprints/fp-lib-table" "$NEW/template/"
for d in symbols footprints; do
    find "$NEW/$d" -maxdepth 1 \( -name 'CMake*' -o -name '.git*' -o -name '*.md' \) -exec rm -rf {} +
done
echo "$VER" > "$NEW/VERSION"
touch "$NEW/.complete"

[ -e "$STAGE" ] && mv "$STAGE" "$DL/stage-$VER.old.$$"
mv "$NEW" "$STAGE"
echo "$STAGE"
