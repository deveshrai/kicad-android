#!/usr/bin/env bash
# Start a new Claude Code session that picks up the port where the last one stopped.
# Usage: scripts/continue.sh [extra instructions...]
#   e.g. scripts/continue.sh "do P7 next"
set -euo pipefail
cd "$(dirname "$0")/.."

PROMPT="Continue the KiCad Android port. Follow docs/CONTINUE.md (read docs/HANDOVER.md first)."
[ $# -gt 0 ] && PROMPT="$PROMPT Additional instructions from the user: $*"

exec claude "$PROMPT"
