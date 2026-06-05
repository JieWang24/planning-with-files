#!/bin/sh
# planning-with-files: SessionStart hook for Claude Code.
# Runs session catchup (post-/clear recovery), then renders active-plan context
# via the same renderer as UserPromptSubmit.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BASE_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python)}"

# Locate session-catchup.py across plugin / skill / home layouts.
CATCHUP=""
for c in \
    "$BASE_ROOT/scripts/session-catchup.py" \
    "$BASE_ROOT/skills/planning-with-files/scripts/session-catchup.py" \
    "$HOME/.claude/skills/planning-with-files/scripts/session-catchup.py"; do
    if [ -f "$c" ]; then CATCHUP="$c"; break; fi
done

if [ -n "$PYTHON_BIN" ] && [ -n "$CATCHUP" ]; then
    "$PYTHON_BIN" "$CATCHUP" "$(pwd)"
fi

sh "$SCRIPT_DIR/user-prompt-submit.sh"
exit 0
