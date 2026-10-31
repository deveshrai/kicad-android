#!/usr/bin/env bash
# Cross-compile KiCad's third-party dependencies for Android with vcpkg (manifest mode).
# Usage: scripts/build-deps.sh [extra vcpkg args]
set -euo pipefail
source "$(dirname "$0")/env.sh"

cd "$KA_ROOT/deps"
exec vcpkg install \
    --triplet=arm64-android \
    --x-install-root="$KA_ROOT/deps/vcpkg_installed" \
    --clean-after-build \
    "$@"
