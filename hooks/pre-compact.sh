#!/bin/sh
# planning-with-files: PreCompact reminder.
# Fires before context compaction. Reminds the agent to flush in-context
# progress to progress.md; the planning files stay on disk and are re-read
# after compaction. Never blocks compaction.

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"

if [ -n "$PLAN_DIR" ]; then
    PLAN_FILE="${PLAN_DIR}/task_plan.md"
    ATTEST_FILE="${PLAN_DIR}/.attestation"
elif [ -f task_plan.md ]; then
    PLAN_FILE="task_plan.md"
    ATTEST_FILE=".plan-attestation"
else
    exit 0
fi
[ -f "$PLAN_FILE" ] || exit 0

echo '[planning-with-files] PreCompact: context compaction is about to occur.'
echo 'Before it completes: make sure progress.md captures recent actions and task_plan.md status reflects the current phase.'
echo 'task_plan.md, findings.md, progress.md remain on disk and will be re-read after compaction.'
if [ -f "$ATTEST_FILE" ]; then
    ATTEST="$(tr -d '\r\n[:space:]' < "$ATTEST_FILE" 2>/dev/null)"
    [ -n "$ATTEST" ] && echo "Plan-SHA256 at compaction: $ATTEST"
fi
exit 0
