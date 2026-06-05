#!/bin/bash
# planning-with-files: Stop hook for Claude Code

HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
PLAN_DIR="$(sh "${HOOK_DIR}/resolve-plan-dir.sh" 2>/dev/null)"
PLAN_FILE="${PLAN_DIR:+${PLAN_DIR}/}task_plan.md"

if [ ! -f "$PLAN_FILE" ]; then
    exit 0
fi

TOTAL=$(grep -c "### Phase" "$PLAN_FILE" || true)
COMPLETE=$(grep -cF "**Status:** complete" "$PLAN_FILE" || true)
IN_PROGRESS=$(grep -cF "**Status:** in_progress" "$PLAN_FILE" || true)
PENDING=$(grep -cF "**Status:** pending" "$PLAN_FILE" || true)

STATUS_TOTAL=$((COMPLETE + IN_PROGRESS + PENDING))

if [ "$STATUS_TOTAL" -eq 0 ]; then
    COMPLETE=$(grep -c "\[complete\]" "$PLAN_FILE" || true)
    IN_PROGRESS=$(grep -c "\[in_progress\]" "$PLAN_FILE" || true)
    PENDING=$(grep -c "\[pending\]" "$PLAN_FILE" || true)
    STATUS_TOTAL=$((COMPLETE + IN_PROGRESS + PENDING))
fi

count_table_status() {
    awk -v want="$1" '
        function trim(s) {
            sub(/^[[:space:]]+/, "", s)
            sub(/[[:space:]]+$/, "", s)
            return s
        }
        function normalize_status(s) {
            s = trim(s)
            gsub(/\*\*/, "", s)
            gsub(/`/, "", s)
            gsub(/[。.,;:：]+$/, "", s)
            s = tolower(trim(s))
            gsub(/[[:space:]-]+/, "_", s)
            if (s == "done" || s == "completed" || s == "完成" || s == "已完成") return "complete"
            if (s == "in_progress" || s == "working" || s == "进行中") return "in_progress"
            if (s == "todo" || s == "not_started" || s == "未开始" || s == "待办" || s == "待处理") return "pending"
            return s
        }
        /^[[:space:]]*\|/ {
            line = $0
            sub(/^[[:space:]]*\|/, "", line)
            sub(/\|[[:space:]]*$/, "", line)
            n = split(line, cells, /\|/)
            if (n < 2) next
            if (normalize_status(cells[2]) == want) count++
        }
        END { print count + 0 }
    ' "$PLAN_FILE"
}

TABLE_COMPLETE=$(count_table_status complete)
TABLE_IN_PROGRESS=$(count_table_status in_progress)
TABLE_PENDING=$(count_table_status pending)
TABLE_TOTAL=$((TABLE_COMPLETE + TABLE_IN_PROGRESS + TABLE_PENDING))

if [ "$TABLE_TOTAL" -gt 0 ] && { [ "$TOTAL" -eq 0 ] || [ "$STATUS_TOTAL" -eq 0 ]; }; then
    COMPLETE=$TABLE_COMPLETE
    IN_PROGRESS=$TABLE_IN_PROGRESS
    PENDING=$TABLE_PENDING
    TOTAL=$TABLE_TOTAL
    STATUS_TOTAL=$TABLE_TOTAL
elif [ "$TOTAL" -eq 0 ] && [ "$STATUS_TOTAL" -gt 0 ]; then
    TOTAL=$STATUS_TOTAL
fi

: "${TOTAL:=0}"
: "${COMPLETE:=0}"
: "${IN_PROGRESS:=0}"
: "${PENDING:=0}"

if [ "$COMPLETE" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    echo "{\"followup_message\": \"[planning-with-files] ALL PHASES COMPLETE ($COMPLETE/$TOTAL). If the user has additional work, add new phases to task_plan.md before starting.\"}"
    exit 0
fi

echo "{\"followup_message\": \"[planning-with-files] Task incomplete ($COMPLETE/$TOTAL phases done). Update progress.md, then read task_plan.md and continue working on the remaining phases.\"}"
exit 0
