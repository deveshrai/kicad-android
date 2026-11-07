#!/usr/bin/env bash
# Record a hands-on test session on a device: rolling screen recordings, full logcat, the crash
# buffer and periodic memory samples of the KiCad process, all under build/sessions/<timestamp>/.
#
# Usage: scripts/record-session.sh [-s SERIAL]      (stop with Ctrl+C or by killing it)
#   Screen recordings are pulled when the script stops.
set -uo pipefail
source "$(dirname "$0")/env.sh"

SERIAL_ARGS=()
if [ "${1:-}" = "-s" ]; then SERIAL_ARGS=(-s "$2"); fi
ADB=(adb ${SERIAL_ARGS[@]+"${SERIAL_ARGS[@]}"})   # bash 3.2: empty arrays trip set -u

OUT="$KA_ROOT/build/sessions/$(date +%Y%m%d-%H%M%S)"
DEVREC=/sdcard/kicad-rec
mkdir -p "$OUT"
echo "$OUT"

"${ADB[@]}" shell "rm -rf $DEVREC; mkdir -p $DEVREC"
"${ADB[@]}" logcat -c
"${ADB[@]}" shell getprop > "$OUT/device-props.txt"

# Rolling 3-minute screen recordings (screenrecord's limit), numbered on the device
"${ADB[@]}" shell "i=0; while true; do i=\$((i+1)); f=$DEVREC/part\$(printf %03d \$i).mp4; \
    screenrecord --bit-rate 6000000 --time-limit 180 \$f || { rm -f \$f; i=\$((i-1)); sleep 5; }; done" &
REC_PID=$!

"${ADB[@]}" logcat -v threadtime -b main,system,crash > "$OUT/logcat.txt" &
LOG_PID=$!

# Memory of the KiCad process every 10 s
(
    while true; do
        P=$("${ADB[@]}" shell pidof "$KA_APP_ID" 2>/dev/null | tr -d '\r')
        if [ -n "$P" ]; then
            echo "$(date +%T) pid=$P $("${ADB[@]}" shell dumpsys meminfo "$P" 2>/dev/null | grep -E 'TOTAL PSS|TOTAL RSS' | tr -s ' ' | tr '\n' ' ')"
        else
            echo "$(date +%T) not running"
        fi
        sleep 10
    done
) > "$OUT/memory.txt" &
MEM_PID=$!

cleanup() {
    kill "$REC_PID" "$LOG_PID" "$MEM_PID" 2>/dev/null
    "${ADB[@]}" shell "pkill -INT screenrecord" 2>/dev/null
    sleep 3
    "${ADB[@]}" pull "$DEVREC" "$OUT/screen" >/dev/null 2>&1
    "${ADB[@]}" logcat -d -b crash > "$OUT/crash-buffer.txt" 2>/dev/null
    echo "session saved to $OUT"
    exit 0
}
trap cleanup INT TERM

wait "$LOG_PID"
cleanup
