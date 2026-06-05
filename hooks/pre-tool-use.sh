#!/bin/sh
# planning-with-files: short pre-Bash reminder (PreToolUse).
# Prints a one-line plan reminder to stdout; the Python adapter forwards it as
# PreToolUse additionalContext. Never blocks the tool call.

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"

if [ -n "$PLAN_DIR" ]; then
    PLAN_FILE="${PLAN_DIR}/task_plan.md"
elif [ -f task_plan.md ]; then
    PLAN_FILE="task_plan.md"
else
    exit 0
fi
[ -f "$PLAN_FILE" ] || exit 0

TITLE=$(awk 'NF { sub(/^#[[:space:]]*/, ""); print; exit }' "$PLAN_FILE")
[ -z "$TITLE" ] && TITLE="$PLAN_FILE"
printf '[planning-with-files] Active plan: %s\n' "$TITLE"
printf 'Re-read task_plan.md / findings.md if this command changes project state.\n'
exit 0
