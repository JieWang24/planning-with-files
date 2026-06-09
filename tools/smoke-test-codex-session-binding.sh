#!/usr/bin/env bash
# End-to-end smoke test for Codex session-bound planning.
#
# It verifies the empty-project path:
#   register hooks -> create plan -> bind current Codex session -> render hooks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PROJECT_DIR="${1:-$(mktemp -d /tmp/pwf-empty-smoke.XXXXXX)}"
THREAD_ID="019e0000-0000-7000-8000-000000000001"
TURN_ID="019e0000-0000-7000-8000-000000000002"
TRANSCRIPT_ID="019e0000-0000-7000-8000-000000000003"

mkdir -p "$PROJECT_DIR"

fail() {
    echo "[FAIL] $*" >&2
    exit 1
}

require_file() {
    [ -f "$1" ] || fail "missing file: $1"
}

require_absent() {
    [ ! -e "$1" ] || fail "unexpected file exists: $1"
}

require_grep() {
    local pattern="$1"
    local file="$2"
    grep -q "$pattern" "$file" || {
        echo "--- $file ---" >&2
        cat "$file" >&2
        fail "pattern not found: $pattern"
    }
}

echo "[1/7] Register hooks in empty project"
"$PYTHON_BIN" "${REPO_ROOT}/tools/register-planning-hooks.py" "$PROJECT_DIR" >/tmp/pwf-smoke-register.out
require_file "${PROJECT_DIR}/.codex/hooks.json"
require_file "${PROJECT_DIR}/.planning/.hooks_mode"

echo "[2/7] Create a plan and bind it atomically from init-session.sh"
(
    cd "$PROJECT_DIR"
    CODEX_THREAD_ID="$THREAD_ID" sh "${REPO_ROOT}/skills/planning-with-files/scripts/init-session.sh" --plan-dir "Empty Smoke Plan" >/tmp/pwf-smoke-init.out
)
PLAN_ID="$(cat "${PROJECT_DIR}/.planning/.active_plan")"
[ -n "$PLAN_ID" ] || fail ".planning/.active_plan is empty"
require_file "${PROJECT_DIR}/.planning/${PLAN_ID}/task_plan.md"
require_file "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.active_plan"
require_file "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.attached"
require_grep "$PLAN_ID" "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.active_plan"
require_grep "Session plan bound" /tmp/pwf-smoke-init.out

echo "[3/7] PostToolUse keeps the same session id and ignores conflicting turn_id"
cat > /tmp/pwf-smoke-post.json <<EOF
{"cwd":"${PROJECT_DIR}","tool_name":"Bash","tool_input":{"cmd":"sh ${REPO_ROOT}/skills/planning-with-files/scripts/init-session.sh --plan-dir Empty"},"turn_id":"${TURN_ID}"}
EOF
CODEX_THREAD_ID="$THREAD_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/post_tool_use.py" </tmp/pwf-smoke-post.json >/tmp/pwf-smoke-post.out
require_file "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.active_plan"
require_absent "${PROJECT_DIR}/.planning/sessions/${TURN_ID}.active_plan"

echo "[4/7] UserPromptSubmit emits compact additionalContext with bound plan dir"
cat > /tmp/pwf-smoke-user.json <<EOF
{"cwd":"${PROJECT_DIR}","prompt":"continue this planned task","turn_id":"${TURN_ID}"}
EOF
CODEX_THREAD_ID="$THREAD_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/user_prompt_submit.py" </tmp/pwf-smoke-user.json >/tmp/pwf-smoke-user.out
require_grep "hookSpecificOutput" /tmp/pwf-smoke-user.out
require_grep "${PROJECT_DIR}/.planning/${PLAN_ID}" /tmp/pwf-smoke-user.out
if grep -q "CANONICAL PLAN FILES" /tmp/pwf-smoke-user.out; then
    cat /tmp/pwf-smoke-user.out >&2
    fail "compact prompt context still includes canonical file list"
fi
require_absent "${PROJECT_DIR}/.planning/sessions/${TURN_ID}.active_plan"

echo "[5/7] transcript_path beats turn_id when no CODEX_THREAD_ID exists"
rm -rf "${PROJECT_DIR}/.planning/sessions"
cat > /tmp/pwf-smoke-transcript-post.json <<EOF
{"cwd":"${PROJECT_DIR}","transcript_path":"${PROJECT_DIR}/rollout-${TRANSCRIPT_ID}.jsonl","tool_name":"Bash","tool_input":{"cmd":"sh ${REPO_ROOT}/skills/planning-with-files/scripts/init-session.sh --plan-dir Empty"},"turn_id":"${TURN_ID}"}
EOF
env -u PWF_SESSION_ID -u CODEX_THREAD_ID -u CODEX_CONVERSATION_ID -u CODEX_SESSION_ID \
    "$PYTHON_BIN" "${REPO_ROOT}/hooks/post_tool_use.py" </tmp/pwf-smoke-transcript-post.json >/tmp/pwf-smoke-transcript-post.out
require_file "${PROJECT_DIR}/.planning/sessions/${TRANSCRIPT_ID}.active_plan"
require_absent "${PROJECT_DIR}/.planning/sessions/${TURN_ID}.active_plan"

echo "[6/7] No stable id no longer reports a false session bind"
rm -rf "${PROJECT_DIR}/.planning/sessions"
cat > /tmp/pwf-smoke-noid-post.json <<EOF
{"cwd":"${PROJECT_DIR}","tool_name":"Bash","tool_input":{"cmd":"sh ${REPO_ROOT}/skills/planning-with-files/scripts/init-session.sh --plan-dir Empty"}}
EOF
env -u PWF_SESSION_ID -u CODEX_THREAD_ID -u CODEX_CONVERSATION_ID -u CODEX_SESSION_ID \
    "$PYTHON_BIN" "${REPO_ROOT}/hooks/post_tool_use.py" </tmp/pwf-smoke-noid-post.json >/tmp/pwf-smoke-noid-post.out
if grep -q "Session plan bound to" /tmp/pwf-smoke-noid-post.out; then
    cat /tmp/pwf-smoke-noid-post.out >&2
    fail "false-positive session binding message"
fi
require_absent "${PROJECT_DIR}/.planning/sessions"

echo "[7/7] Guards work and stop reminder stays compact"
mkdir -p "${PROJECT_DIR}/.planning/sessions"
printf "%s\n" "$PLAN_ID" > "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.active_plan"
printf "attached\n" > "${PROJECT_DIR}/.planning/sessions/${THREAD_ID}.attached"
cat > /tmp/pwf-smoke-pre.json <<EOF
{"cwd":"${PROJECT_DIR}","tool_name":"Bash","tool_input":{"cmd":"sh ${REPO_ROOT}/hooks/resolve-plan-dir.sh"}}
EOF
CODEX_THREAD_ID="$THREAD_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/pre_tool_use.py" </tmp/pwf-smoke-pre.json >/tmp/pwf-smoke-pre.out
require_grep '"decision": "block"\|"decision":"block"' /tmp/pwf-smoke-pre.out

cat > /tmp/pwf-smoke-pre-read.json <<EOF
{"cwd":"${PROJECT_DIR}","tool_name":"Bash","tool_input":{"cmd":"sed -n '1,20p' ${REPO_ROOT}/hooks/resolve-plan-dir.sh"}}
EOF
CODEX_THREAD_ID="$THREAD_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/pre_tool_use.py" </tmp/pwf-smoke-pre-read.json >/tmp/pwf-smoke-pre-read.out
if grep -q '"decision": "block"\|"decision":"block"' /tmp/pwf-smoke-pre-read.out; then
    cat /tmp/pwf-smoke-pre-read.out >&2
    fail "read-only resolver inspection was blocked"
fi

cat > /tmp/pwf-smoke-stop.json <<EOF
{"cwd":"${PROJECT_DIR}"}
EOF
CODEX_THREAD_ID="$THREAD_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/stop.py" </tmp/pwf-smoke-stop.json >/tmp/pwf-smoke-stop.out
require_grep "task_plan.md" /tmp/pwf-smoke-stop.out
if grep -q "${PROJECT_DIR}/.planning/${PLAN_ID}/task_plan.md" /tmp/pwf-smoke-stop.out; then
    cat /tmp/pwf-smoke-stop.out >&2
    fail "stop reminder still includes absolute task_plan path"
fi

echo "[OK] planning-with-files Codex session binding smoke test passed"
echo "Project: $PROJECT_DIR"
echo "Plan:    ${PROJECT_DIR}/.planning/${PLAN_ID}"
