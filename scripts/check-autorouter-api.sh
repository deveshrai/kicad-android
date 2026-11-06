#!/bin/bash
# List library calls in the autorouter jar's classes that Android (API 35) does not have.
# Run after scripts/build-autorouter.sh, for example after a Freerouting update.  Calls in
# code that never runs on the routing path (DRC reports, analytics, the version check) are fine.
set -euo pipefail
KA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$KA_ROOT/scripts/env.sh" >/dev/null
"$JAVA_HOME/bin/java" "$KA_ROOT/android/autorouter/tools/ApiCheck.java" \
    "$ANDROID_SDK_ROOT/platforms/android-35/android.jar" "$KA_ROOT/build/autorouter/classes" \
    | grep -v 'CLASS(non-jdk) io/swagger'
