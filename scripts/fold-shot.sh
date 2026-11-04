#!/usr/bin/env bash
# Screenshot of the Z Fold's inner screen (screencap needs a display id when there are two)
# Usage: scripts/fold-shot.sh OUT.png [cover]
source "$(dirname "$0")/env.sh" >/dev/null
DISP=4630947004648141459; [ "${2:-}" = cover ] && DISP=4630947123231501204
adb -s RZGL62ZE1AZ exec-out screencap -d "$DISP" -p > "$1"
