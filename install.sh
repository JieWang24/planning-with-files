#!/usr/bin/env bash
#
# install.sh — scripted GLOBAL install of the planning-with-files Claude fork.
#
# Two ways to install this fork:
#
#   1. Plugin route (recommended, official-aligned) — from a Claude Code session:
#         /plugin marketplace add /absolute/path/to/this/clone
#         /plugin install planning-with-files@planning-with-files
#      Claude manages everything; ${CLAUDE_PLUGIN_ROOT} is set and
#      hooks/hooks.json fires natively. Works from any branch of a local clone.
#
#   2. This script (global, no plugin system) — installs into ~/.claude:
#         skills/planning-with-files[/-zh]   (auto-discovered skill)
#         commands/*.md                       (auto-discovered /plan, /status, ...)
#         settings.json hooks                 (derived from hooks/hooks.json,
#                                              reliable — not SKILL.md frontmatter)
#
# Use ONE route, not both (they would double-fire the hooks).
#
# Usage:
#   ./install.sh                 # global install into ~/.claude
#   ./install.sh --no-hooks      # install skill + commands only (no settings.json hooks)
#   CLAUDE_HOME=/x ./install.sh  # override the Claude config dir (default: ~/.claude)
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_HOME/skills/planning-with-files"
WANT_HOOKS=1

log()  { printf '\033[0;36m[pwf]\033[0m %s\n' "$*"; }
die()  { printf '\033[0;31m[pwf] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 is required (the hook adapters are Python)."

while [ $# -gt 0 ]; do
  case "$1" in
    --no-hooks) WANT_HOOKS=0; shift ;;
    -h|--help) sed -n '2,33p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/commands"

# 1) Skill (English) + bundled hooks/scripts/templates
if [ -d "$SKILL_DIR" ]; then
  bak="$SKILL_DIR.bak.$(date +%Y%m%d-%H%M%S)"
  log "Backing up existing skill -> $bak"
  mv "$SKILL_DIR" "$bak"
fi
cp -R "$REPO_DIR/skills/planning-with-files" "$SKILL_DIR"
cp -R "$REPO_DIR/hooks" "$SKILL_DIR/hooks"
chmod +x "$SKILL_DIR"/hooks/*.sh "$SKILL_DIR"/hooks/*.py "$SKILL_DIR"/scripts/*.sh 2>/dev/null || true
log "Skill    -> $SKILL_DIR (+ bundled hooks/)"

# 2) Simplified-Chinese skill
rm -rf "$CLAUDE_HOME/skills/planning-with-files-zh"
cp -R "$REPO_DIR/skills/planning-with-files-zh" "$CLAUDE_HOME/skills/planning-with-files-zh"
log "Skill-zh -> $CLAUDE_HOME/skills/planning-with-files-zh"

# 3) Slash commands
cp "$REPO_DIR"/commands/*.md "$CLAUDE_HOME/commands/"
log "Commands -> $CLAUDE_HOME/commands/ (/plan, /start, /status, /plan-attest, /plan-goal, /plan-loop, /plan-zh)"

# 4) Hooks into settings.json (derived from hooks/hooks.json; ${CLAUDE_PLUGIN_ROOT} -> skill dir)
if [ "$WANT_HOOKS" -eq 1 ]; then
  REPO_DIR="$REPO_DIR" SKILL_DIR="$SKILL_DIR" python3 - "$CLAUDE_HOME/settings.json" <<'PY'
import json, os, sys

settings_path = sys.argv[1]
repo = os.environ["REPO_DIR"]
skill_dir = os.environ["SKILL_DIR"]

with open(os.path.join(repo, "hooks", "hooks.json"), encoding="utf-8") as fh:
    plugin_hooks = json.load(fh)["hooks"]

# Rewrite ${CLAUDE_PLUGIN_ROOT} -> the installed skill dir (which now holds hooks/).
def rewrite(obj):
    if isinstance(obj, str):
        return obj.replace("${CLAUDE_PLUGIN_ROOT}", skill_dir)
    if isinstance(obj, list):
        return [rewrite(x) for x in obj]
    if isinstance(obj, dict):
        return {k: rewrite(v) for k, v in obj.items()}
    return obj
plugin_hooks = rewrite(plugin_hooks)

settings = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, OSError):
        settings = {}
if not isinstance(settings, dict):
    settings = {}

hooks = settings.setdefault("hooks", {})

def is_ours(group):
    for h in group.get("hooks", []):
        if "planning-with-files" in h.get("command", ""):
            return True
    return False

for event, groups in plugin_hooks.items():
    kept = [g for g in hooks.get(event, []) if not is_ours(g)]  # drop our prior entries (idempotent)
    hooks[event] = kept + groups

with open(settings_path, "w", encoding="utf-8") as fh:
    json.dump(settings, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print("  merged hooks ->", settings_path)
PY
  log "Hooks    -> $CLAUDE_HOME/settings.json (reliable, derived from hooks/hooks.json)"
else
  log "Hooks    -> skipped (--no-hooks). Skill + commands only."
fi

log "Done. Restart Claude Code (or open a new session) to load the skill, commands, and hooks."
cat <<EOF

Per-project gating (optional): in any project,
    mkdir -p .planning && echo on > .planning/.hooks_mode    # on | off | session
Type \`临时任务 ...\` in a prompt to silence planning hooks for that one turn.
See docs/claude-setup.md for the full guide.
EOF
