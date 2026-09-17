#!/bin/sh
# planning-with-files: inspect or change the plan bound to THIS Claude Code session.
#
# Usage:
#   session-plan.sh [show]          # bound plan id + canonical files (exit 1 if unbound)
#   session-plan.sh path            # bound plan dir only (for scripts)
#   session-plan.sh list [--all]    # plans in ./.planning, newest first (* = this session)
#   session-plan.sh attach <PLAN_ID> # bind this session to an existing plan (+ catchup)
#   session-plan.sh detach          # remove this session's binding
#   session-plan.sh catchup         # what earlier sessions on the bound plan did after their last plan update
#
# Options: --session <id> overrides PWF_SESSION_ID / CLAUDE_CODE_SESSION_ID.
#
# attach never touches .planning/.active_plan. When no session id is visible it
# still prints PLAN_ROOT= / PLAN_ID= and the PostToolUse hook binds the caller.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=session-lib.sh
. "$SCRIPT_DIR/session-lib.sh"

CMD="show"
ARG=""
ALL=0
SID_OVERRIDE=""
while [ $# -gt 0 ]; do
    case "$1" in
        show|path|list|attach|detach|catchup) CMD="$1" ;;
        --session) SID_OVERRIDE="${2:-}"; shift ;;
        --all) ALL=1 ;;
        -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
        *) ARG="$1" ;;
    esac
    shift
done

if [ -n "$SID_OVERRIDE" ]; then
    SID="$(pwf_safe_session_id "$SID_OVERRIDE")"
else
    SID="$(pwf_session_id)"
fi

binding() {
    [ -n "$SID" ] && pwf_find_binding "$PWD" "$SID"
}

print_files() {
    echo "  task_plan : $1/task_plan.md"
    echo "  findings  : $1/findings.md"
    echo "  progress  : $1/progress.md"
}

phase_summary() {
    awk '
        /^#{2,4}[[:space:]]*(Phase|阶段)/ { h++ }
        /\*\*[[:space:]]*(Status|状态)/ {
            line = tolower($0); s++
            if (line ~ /(complete|done|完成)/) c++
        }
        END { t = (h > s ? h : s); if (t > 0) printf "%d/%d", c, t; else printf "-" }
    ' "$1" 2>/dev/null
}

title_of() {
    awk 'NF { sub(/^#+[[:space:]]*/, ""); print; exit }' "$1" 2>/dev/null | cut -c1-80
}

case "$CMD" in
    show|path)
        found="$(binding)"
        if [ -z "$found" ]; then
            if [ -z "$SID" ]; then
                echo "[planning-with-files] No Claude session id visible (PWF_SESSION_ID / CLAUDE_CODE_SESSION_ID)." >&2
            else
                echo "[planning-with-files] No plan is bound to this session ($SID)." >&2
            fi
            echo "  create: sh \"$SCRIPT_DIR/init-session.sh\" --plan-dir \"<task name>\"" >&2
            echo "  attach: sh \"$SCRIPT_DIR/session-plan.sh\" attach <PLAN_ID>   (see: list)" >&2
            exit 1
        fi
        root="$(printf '%s' "$found" | cut -f1)"
        plan_id="$(printf '%s' "$found" | cut -f2)"
        dir="$root/.planning/$plan_id"
        if [ "$CMD" = "path" ]; then
            printf '%s\n' "$dir"
            exit 0
        fi
        echo "Session : $SID"
        echo "Plan    : $plan_id — $(title_of "$dir/task_plan.md")"
        echo "Phases  : $(phase_summary "$dir/task_plan.md") complete"
        print_files "$dir"
        ;;

    list)
        plan_root="$PWD/.planning"
        if [ ! -d "$plan_root" ]; then
            echo "[planning-with-files] No .planning/ directory in $PWD."
            exit 0
        fi
        bound="$(pwf_bound_plan_id "$PWD" "$SID")"
        active="$(tr -d '\r\n[:space:]' < "$plan_root/.active_plan" 2>/dev/null)"
        limit=15
        [ "$ALL" -eq 1 ] && limit=100000
        ls -1t "$plan_root" 2>/dev/null | while IFS= read -r name; do
            [ -f "$plan_root/$name/task_plan.md" ] || continue
            pwf_valid_plan_id "$name" || continue
            printf '%s\n' "$name"
        done | head -n "$limit" | while IFS= read -r name; do
            mark=" "
            [ "$name" = "$bound" ] && mark="*"
            note=""
            [ "$name" = "$active" ] && note=" (last created)"
            printf '%s %-48s %6s  %s%s\n' "$mark" "$name" "$(phase_summary "$plan_root/$name/task_plan.md")" \
                "$(title_of "$plan_root/$name/task_plan.md")" "$note"
        done
        [ "$ALL" -eq 1 ] || echo "(newest 15; --all for everything; * = bound to this session)"
        ;;

    attach)
        if ! pwf_valid_plan_id "$ARG" || [ ! -f "$PWD/.planning/$ARG/task_plan.md" ]; then
            echo "[planning-with-files] Not a plan in $PWD/.planning: '${ARG}'" >&2
            echo "Available plans:" >&2
            sh "$0" list >&2
            exit 1
        fi
        dir="$PWD/.planning/$ARG"
        echo "PLAN_ROOT=$PWD/.planning"
        echo "PLAN_ID=$ARG"
        if [ -n "$SID" ]; then
            pwf_bind_session "$PWD" "$SID" "$ARG" || { echo "[planning-with-files] Failed to write binding." >&2; exit 1; }
            echo "[planning-with-files] This Claude session ($SID) is now bound to $ARG."
        else
            echo "[planning-with-files] No session id visible here; the PostToolUse hook binds the calling Claude session."
        fi
        echo "Canonical files — read & update ONLY these for this task:"
        print_files "$dir"
        echo "Phases: $(phase_summary "$dir/task_plan.md") complete"
        PY="$(command -v python3 || command -v python || true)"
        if [ -n "$PY" ] && [ -f "$SCRIPT_DIR/session-catchup.py" ]; then
            if [ -n "$SID" ]; then
                "$PY" "$SCRIPT_DIR/session-catchup.py" "$PWD" --plan-id "$ARG" --session-id "$SID"
            else
                "$PY" "$SCRIPT_DIR/session-catchup.py" "$PWD" --plan-id "$ARG"
            fi
        fi
        ;;

    detach)
        found="$(binding)"
        if [ -z "$found" ]; then
            echo "[planning-with-files] Nothing to detach: this session has no bound plan."
            exit 0
        fi
        root="$(printf '%s' "$found" | cut -f1)"
        plan_id="$(printf '%s' "$found" | cut -f2)"
        pwf_unbind_session "$root" "$SID"
        echo "PLAN_ROOT=$root/.planning"
        echo "PWF_DETACHED=$plan_id"
        echo "[planning-with-files] Session $SID detached from $plan_id."
        ;;

    catchup)
        found="$(binding)"
        [ -n "$found" ] || { echo "[planning-with-files] No plan bound to this session; nothing to catch up." ; exit 0; }
        root="$(printf '%s' "$found" | cut -f1)"
        plan_id="$(printf '%s' "$found" | cut -f2)"
        PY="$(command -v python3 || command -v python)"
        exec "$PY" "$SCRIPT_DIR/session-catchup.py" "$root" --plan-id "$plan_id" --session-id "$SID"
        ;;
esac
exit 0
