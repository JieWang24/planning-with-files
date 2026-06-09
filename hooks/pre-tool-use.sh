#!/bin/sh
# planning-with-files: Pre-tool-use hook for Codex

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"
if [ -n "$PLAN_DIR" ]; then
    PLAN_FILE="${PLAN_DIR}/task_plan.md"
    FINDINGS_FILE="${PLAN_DIR}/findings.md"
elif [ -f task_plan.md ]; then
    PLAN_FILE="task_plan.md"
    FINDINGS_FILE="findings.md"
else
    echo '{"decision": "allow"}'
    exit 0
fi

if [ -f "$PLAN_FILE" ]; then
    TITLE=$(awk 'NF { sub(/^#[[:space:]]*/, ""); print; exit }' "$PLAN_FILE")
    if [ -z "$TITLE" ]; then
        TITLE="$PLAN_FILE"
    fi
    printf '[planning-with-files] Active plan: %s (%s)\n' "$TITLE" "$PLAN_FILE" >&2
    printf 'Re-read %s / %s if this Bash command changes project state. Do not read other plans.\n' "$PLAN_FILE" "$FINDINGS_FILE" >&2
fi

echo '{"decision": "allow"}'
exit 0
