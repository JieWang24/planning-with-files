#!/bin/bash
# planning-with-files: Pre-tool-use hook for Codex

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"
PLAN_FILE="${PLAN_DIR:+${PLAN_DIR}/}task_plan.md"

if [ -f "$PLAN_FILE" ]; then
    TITLE=$(awk 'NF { sub(/^#[[:space:]]*/, ""); print; exit }' "$PLAN_FILE")
    if [ -z "$TITLE" ]; then
        TITLE="$PLAN_FILE"
    fi
    printf '[planning-with-files] Active plan: %s
' "$TITLE" >&2
    printf 'Read task_plan.md/findings.md if this Bash command changes project state.
' >&2
fi

echo '{"decision": "allow"}'
exit 0
