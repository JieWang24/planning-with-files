#!/bin/bash
# planning-with-files: User prompt submit hook for Codex

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"
PLAN_FILE="${PLAN_DIR:+${PLAN_DIR}/}task_plan.md"
PROGRESS_FILE="${PLAN_DIR:+${PLAN_DIR}/}progress.md"

# Session gating is handled by the Python Codex adapter. Keep this shell script
# focused on rendering active-plan context so PWF_HOOKS=on/off and temporary
# prompt suppression behave consistently across Codex CLI and App.

if [ -f "$PLAN_FILE" ]; then
    echo "[planning-with-files] ACTIVE PLAN — current state:"
    head -50 "$PLAN_FILE"
    echo ""
    echo "=== recent progress ==="
    tail -20 "$PROGRESS_FILE" 2>/dev/null
    echo ""
    echo "[planning-with-files] Read findings.md for research context. Continue from the current phase."
fi
exit 0
