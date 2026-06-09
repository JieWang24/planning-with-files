#!/usr/bin/env bash
# Smoke test for planning hook debug mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PROJECT_DIR="${1:-$(mktemp -d /tmp/pwf-hook-debug.XXXXXX)}"
SESSION_ID="019e0000-0000-7000-8000-000000000101"

mkdir -p "$PROJECT_DIR"

fail() {
    echo "[FAIL] $*" >&2
    exit 1
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

echo "[1/8] Register hooks and create a session-bound plan"
"$PYTHON_BIN" "${REPO_ROOT}/tools/register-planning-hooks.py" "$PROJECT_DIR" >/tmp/pwf-debug-register.out
(
    cd "$PROJECT_DIR"
    CODEX_THREAD_ID="$SESSION_ID" sh "${REPO_ROOT}/skills/planning-with-files/scripts/init-session.sh" --plan-dir "Debug Hook Smoke" >/tmp/pwf-debug-init.out
)
PLAN_ID="$(cat "${PROJECT_DIR}/.planning/.active_plan")"
[ -n "$PLAN_ID" ] || fail "active plan is empty"

echo "[2/8] Enable project debug mode"
"$PYTHON_BIN" "${REPO_ROOT}/tools/planning-hooks-debug.py" on "$PROJECT_DIR" >/tmp/pwf-debug-mode.out
LOG="${PROJECT_DIR}/.planning/debug/hook-events.jsonl"
rm -f "$LOG"

echo "[3/8] Simulate SessionStart"
printf '{"cwd":"%s"}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/session_start.py" >/tmp/pwf-debug-session-start.out
require_grep "SessionStart triggered" /tmp/pwf-debug-session-start.out

echo "[4/8] Simulate UserPromptSubmit"
printf '{"cwd":"%s","prompt":"continue"}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/user_prompt_submit.py" >/tmp/pwf-debug-user-prompt.out
require_grep "UserPromptSubmit triggered" /tmp/pwf-debug-user-prompt.out
require_grep "hookSpecificOutput" /tmp/pwf-debug-user-prompt.out

echo "[5/8] Simulate PreToolUse"
printf '{"cwd":"%s","tool_name":"Bash","tool_input":{"cmd":"sed -n 1,20p README.md"}}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/pre_tool_use.py" >/tmp/pwf-debug-pre-tool.out
require_grep "PreToolUse triggered" /tmp/pwf-debug-pre-tool.out

echo "[6/8] Simulate PostToolUse"
printf '{"cwd":"%s","tool_name":"Bash","tool_input":{"cmd":"sed -n 1,20p README.md"}}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/post_tool_use.py" >/tmp/pwf-debug-post-tool.out
require_grep "PostToolUse triggered" /tmp/pwf-debug-post-tool.out

echo "[7/8] Simulate PermissionRequest"
printf '{"cwd":"%s","tool_name":"Bash"}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/permission_request.py" >/tmp/pwf-debug-permission.out
require_grep "PermissionRequest triggered" /tmp/pwf-debug-permission.out

echo "[8/8] Simulate Stop"
printf '{"cwd":"%s"}' "$PROJECT_DIR" |
    CODEX_THREAD_ID="$SESSION_ID" "$PYTHON_BIN" "${REPO_ROOT}/hooks/stop.py" >/tmp/pwf-debug-stop.out
require_grep "Stop triggered" /tmp/pwf-debug-stop.out

require_grep '"hook":"SessionStart"' "$LOG"
require_grep '"hook":"UserPromptSubmit"' "$LOG"
require_grep '"hook":"PreToolUse"' "$LOG"
require_grep '"hook":"PostToolUse"' "$LOG"
require_grep '"hook":"PermissionRequest"' "$LOG"
require_grep '"hook":"Stop"' "$LOG"

echo "[OK] planning hook debug smoke test passed"
echo "Project: $PROJECT_DIR"
echo "Plan:    ${PROJECT_DIR}/.planning/${PLAN_ID}"
echo "Log:     $LOG"
