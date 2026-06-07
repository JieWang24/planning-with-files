#!/bin/bash
# planning-with-files: Post-tool-use hook for Codex

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"
PLAN_FILE="${PLAN_DIR:+${PLAN_DIR}/}task_plan.md"

if [ -f "$PLAN_FILE" ]; then
    echo "[planning-with-files] Update progress.md with what you just did. If a phase is now complete, update task_plan.md status."
    echo "[codex-scholar] For KB edits, route project-owned ideas/specs to Designs/ before Experiments/, Results/, or paper claims."
fi
exit 0
