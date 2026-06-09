#!/usr/bin/env bash
#
# Install the Codex planning-with-files package from this repository.
#
# This script installs the portable files into CODEX_HOME, but it does not
# globally enable hooks. Hooks are registered per project with the bundled
# register-planning-hooks.py helper.
#
# Usage:
#   ./install.sh
#   ./install.sh --register /path/to/project --mode on
#   CODEX_HOME=/tmp/codex ./install.sh --register "$PWD"
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
REGISTER_PROJECTS=()
PROJECT_MODE=""

log() { printf '[planning-with-files] %s\n' "$*"; }
die() { printf '[planning-with-files] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,18p' "$0"
}

command -v python3 >/dev/null 2>&1 || die "python3 is required"
command -v rsync >/dev/null 2>&1 || die "rsync is required"

while [ $# -gt 0 ]; do
  case "$1" in
    --register)
      [ $# -ge 2 ] || die "--register requires a project directory"
      REGISTER_PROJECTS+=("$2")
      shift 2
      ;;
    --mode)
      [ $# -ge 2 ] || die "--mode requires one of: on, off, session"
      PROJECT_MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

case "$PROJECT_MODE" in
  ""|on|off|session) ;;
  *) die "--mode must be one of: on, off, session" ;;
esac

mkdir -p "$CODEX_HOME/skills" "$CODEX_HOME/hooks" "$CODEX_HOME/tools"

rsync -a --delete "$REPO_DIR/skills/planning-with-files/" "$CODEX_HOME/skills/planning-with-files/"
rsync -a "$REPO_DIR/hooks/" "$CODEX_HOME/hooks/"
rsync -a "$REPO_DIR/tools/" "$CODEX_HOME/tools/"

chmod +x "$CODEX_HOME"/hooks/*.py "$CODEX_HOME"/hooks/*.sh 2>/dev/null || true
chmod +x "$CODEX_HOME"/tools/*.py "$CODEX_HOME"/tools/*.sh "$CODEX_HOME"/skills/planning-with-files/scripts/*.sh 2>/dev/null || true

log "installed skill -> $CODEX_HOME/skills/planning-with-files"
log "installed hooks -> $CODEX_HOME/hooks"
log "installed tools -> $CODEX_HOME/tools"

if [ "${#REGISTER_PROJECTS[@]}" -gt 0 ]; then
  for project in "${REGISTER_PROJECTS[@]}"; do
    python3 "$CODEX_HOME/tools/register-planning-hooks.py" "$project"
    if [ -n "$PROJECT_MODE" ]; then
      python3 "$CODEX_HOME/tools/planning-hooks-mode.py" "$PROJECT_MODE" "$project"
    fi
  done
else
  cat <<EOF

No project was registered. To enable hooks for a project:

  python3 "$CODEX_HOME/tools/register-planning-hooks.py" /path/to/project
  python3 "$CODEX_HOME/tools/planning-hooks-mode.py" on /path/to/project
  python3 "$CODEX_HOME/tools/planning-hooks-debug.py" on /path/to/project

Use mode "on" for automatic script-first planning behavior.
Use mode "off" to disable planning hooks in a project.
Use mode "session" only for manual opt-in experiments; init-session can create the attached sentinel when a stable session id exists.
Use debug "on" only while diagnosing hook trigger behavior.
EOF
fi

log "done"
