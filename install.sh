#!/usr/bin/env bash
#
# install.sh — install the planning-with-files skill + hooks for Claude Code.
#
# This is the local-customized "claude" branch. It installs:
#   - the skill        -> $CLAUDE_HOME/skills/planning-with-files/
#   - the hook adapters -> $CLAUDE_HOME/hooks/
# and (optionally) registers the planning hooks into one or more projects'
# .claude/settings.json (merged, idempotent) and sets .planning/.hooks_mode.
#
# Usage:
#   ./install.sh                         # global install only (skill + hooks)
#   ./install.sh --project /path/to/proj # also register that project (hooks_mode=on)
#   ./install.sh --project A --project B # register several projects
#   ./install.sh --project P --mode session   # register with .hooks_mode=session
#   ./install.sh --project P --mode skip      # register hooks but DON'T touch .hooks_mode
#   ./install.sh --no-global --project P      # only register the project, skip global copy
#
# Env:
#   CLAUDE_HOME   override the Claude config dir (default: ~/.claude)
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_NAME="planning-with-files"

DO_GLOBAL=1
MODE="on"
PROJECTS=()

HOOK_FILES=(
  planning_hook_adapter.py
  session_start.py user_prompt_submit.py pre_tool_use.py post_tool_use.py stop.py permission_request.py
  session-start.sh user-prompt-submit.sh post-tool-use.sh pre-tool-use.sh stop.sh resolve-plan-dir.sh
)

log()  { printf '\033[0;36m[pwf]\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m[pwf] WARN:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[0;31m[pwf] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 is required (the hook adapters are Python)."

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECTS+=("${2:?--project needs a path}"); shift 2 ;;
    --mode)    MODE="${2:?--mode needs a value (on|off|session|skip)}"; shift 2 ;;
    --no-global) DO_GLOBAL=0; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

install_global() {
  log "Global install into $CLAUDE_HOME"
  mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/hooks"

  local dst="$CLAUDE_HOME/skills/$SKILL_NAME"
  if [ -d "$dst" ]; then
    local bak="$dst.bak.$(date +%Y%m%d-%H%M%S)"
    log "Backing up existing skill -> $bak"
    mv "$dst" "$bak"
  fi
  cp -R "$REPO_DIR/skills/$SKILL_NAME" "$dst"
  chmod +x "$dst"/scripts/*.sh 2>/dev/null || true

  local f
  for f in "${HOOK_FILES[@]}"; do
    cp "$REPO_DIR/hooks/$f" "$CLAUDE_HOME/hooks/$f"
  done
  chmod +x "$CLAUDE_HOME"/hooks/*.sh "$CLAUDE_HOME"/hooks/*.py 2>/dev/null || true

  log "Skill  -> $dst"
  log "Hooks  -> $CLAUDE_HOME/hooks/ (${#HOOK_FILES[@]} files)"
}

register_project() {
  local proj="$1" mode="$2"
  [ -d "$proj" ] || die "project path does not exist: $proj"
  proj="$(cd "$proj" && pwd)"
  mkdir -p "$proj/.claude"

  REPO_DIR="$REPO_DIR" python3 - "$proj/.claude/settings.json" <<'PY'
import json, os, sys

target = sys.argv[1]
template = os.path.join(os.environ["REPO_DIR"], "project-template", ".claude", "settings.json")

with open(template, encoding="utf-8") as fh:
    tmpl = json.load(fh)

settings = {}
if os.path.exists(target):
    try:
        with open(target, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, OSError):
        settings = {}
if not isinstance(settings, dict):
    settings = {}

hooks = settings.setdefault("hooks", {})
OURS = (
    "planning-with-files",
    "session_start.py", "user_prompt_submit.py", "pre_tool_use.py",
    "post_tool_use.py", "stop.py", "permission_request.py",
)

def is_ours(group):
    for h in group.get("hooks", []):
        cmd = h.get("command", "")
        if any(tok in cmd for tok in OURS):
            return True
    return False

for event, groups in tmpl.get("hooks", {}).items():
    existing = [g for g in hooks.get(event, []) if not is_ours(g)]  # drop our prior entries
    hooks[event] = existing + groups                                 # re-add fresh

with open(target, "w", encoding="utf-8") as fh:
    json.dump(settings, fh, ensure_ascii=False, indent=2)
    fh.write("\n")

print("  merged hooks ->", target)
PY

  case "$mode" in
    skip) : ;;
    on|off|session)
      mkdir -p "$proj/.planning"
      printf '%s\n' "$mode" > "$proj/.planning/.hooks_mode"
      log "  .planning/.hooks_mode = $mode"
      ;;
    *) die "invalid --mode: $mode (use on|off|session|skip)" ;;
  esac
  log "Registered project: $proj"
}

[ "$DO_GLOBAL" -eq 1 ] && install_global

for p in "${PROJECTS[@]:-}"; do
  [ -n "$p" ] && register_project "$p" "$MODE"
done

log "Done."
if [ "${#PROJECTS[@]}" -eq 0 ]; then
  cat <<EOF

Next: register a project so Claude Code loads the planning hooks there:
    ./install.sh --no-global --project /path/to/your/project

On first launch in that project, Claude Code will ask you to APPROVE the hooks
(security gate) — accept them. See docs/claude-setup.md for full instructions.
EOF
fi
