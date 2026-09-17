# shellcheck shell=sh
# planning-with-files: shared session helpers for the Claude Code scripts.
# Source it:  . "$SCRIPT_DIR/session-lib.sh"
#
# A Claude Code session is bound to exactly one plan through
#   <project>/.planning/sessions/<session-id>.active_plan   (plan id)
#   <project>/.planning/sessions/<session-id>.attached      (sentinel)
# The project-wide .planning/.active_plan is only "the plan created last" and is
# never used as a session's plan.

PWF_PLAN_ID_RE='^[A-Za-z0-9_][A-Za-z0-9._-]*$'

# Print a safe session id derived from $1 (UUID preferred), or nothing.
pwf_safe_session_id() {
    _pwf_raw="$1"
    [ -n "$_pwf_raw" ] || return 0
    _pwf_uuid="$(printf '%s' "$_pwf_raw" \
        | sed -nE 's/.*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*/\1/p' \
        | tail -n 1 | tr '[:upper:]' '[:lower:]')"
    if [ -n "$_pwf_uuid" ]; then
        printf '%s\n' "$_pwf_uuid"
        return 0
    fi
    case "$_pwf_raw" in
        *[!A-Za-z0-9_.-]*) return 0 ;;
    esac
    if [ "${#_pwf_raw}" -ge 8 ] && [ "${#_pwf_raw}" -le 160 ]; then
        printf '%s\n' "$_pwf_raw"
    fi
}

# Current Claude Code session id: PWF_SESSION_ID (exported by the SessionStart
# hook), then CLAUDE_CODE_SESSION_ID. Empty in a plain terminal.
pwf_session_id() {
    for _pwf_key in PWF_SESSION_ID CLAUDE_CODE_SESSION_ID; do
        eval "_pwf_val=\${$_pwf_key:-}"
        _pwf_sid="$(pwf_safe_session_id "$_pwf_val")"
        if [ -n "$_pwf_sid" ]; then
            printf '%s\n' "$_pwf_sid"
            return 0
        fi
    done
}

pwf_valid_plan_id() {
    [ -n "$1" ] && printf '%s' "$1" | grep -Eq "$PWF_PLAN_ID_RE"
}

# pwf_bound_plan_id <project_root> <session_id> -> plan id bound there, or nothing.
pwf_bound_plan_id() {
    _pwf_file="$1/.planning/sessions/$2.active_plan"
    [ -n "$2" ] && [ -f "$_pwf_file" ] || return 0
    _pwf_id="$(tr -d '\r\n[:space:]' < "$_pwf_file")"
    if pwf_valid_plan_id "$_pwf_id" && [ -f "$1/.planning/$_pwf_id/task_plan.md" ]; then
        printf '%s\n' "$_pwf_id"
    fi
}

# pwf_find_binding <start_dir> <session_id>
# Walk up from start_dir; print "<project_root>\t<plan_id>" for the first binding.
pwf_find_binding() {
    _pwf_dir="$(cd "$1" 2>/dev/null && pwd -P)" || return 0
    while :; do
        _pwf_id="$(pwf_bound_plan_id "$_pwf_dir" "$2")"
        if [ -n "$_pwf_id" ]; then
            printf '%s\t%s\n' "$_pwf_dir" "$_pwf_id"
            return 0
        fi
        [ "$_pwf_dir" = "/" ] && return 0
        _pwf_dir="$(dirname "$_pwf_dir")"
    done
}

# pwf_bind_session <project_root> <session_id> <plan_id>
pwf_bind_session() {
    mkdir -p "$1/.planning/sessions" || return 1
    printf '%s\n' "$3" > "$1/.planning/sessions/$2.active_plan" || return 1
    printf 'attached\n' > "$1/.planning/sessions/$2.attached"
}

# pwf_unbind_session <project_root> <session_id>
pwf_unbind_session() {
    rm -f "$1/.planning/sessions/$2.active_plan" "$1/.planning/sessions/$2.attached"
}

# pwf_session_plan_dir -> plan dir for this Claude session (exit 1 if a session
# id is known but nothing is bound; exit 2 if there is no session id at all).
pwf_session_plan_dir() {
    _pwf_sid="$(pwf_session_id)"
    [ -n "$_pwf_sid" ] || return 2
    _pwf_found="$(pwf_find_binding "$PWD" "$_pwf_sid")"
    [ -n "$_pwf_found" ] || return 1
    printf '%s/.planning/%s\n' "$(printf '%s' "$_pwf_found" | cut -f1)" "$(printf '%s' "$_pwf_found" | cut -f2)"
}
