#!/bin/sh
# planning-with-files: post-tool reminder to keep progress.md current.

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"

if [ -n "$PLAN_DIR" ]; then
    PLAN_FILE="${PLAN_DIR}/task_plan.md"
elif [ -f task_plan.md ]; then
    PLAN_FILE="task_plan.md"
else
    exit 0
fi

if [ -f "$PLAN_FILE" ]; then
    echo "[planning-with-files] Update progress.md with what you just did. If a phase is now complete, update task_plan.md status."
fi
exit 0
