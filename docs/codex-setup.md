# Codex Setup And Migration Guide

This document explains how to reproduce the local `planning-with-files` setup on another machine.

## Branches

- `main`: Codex version. This is the default branch for Codex App and Codex CLI migration.
- `claude`: Claude Code plugin version. It has related logic, but different hook contracts and installation paths.

Use `main` for Codex.

## Install Files Into `~/.codex`

From this repository:

```bash
./install.sh
```

This installs:

```text
~/.codex/skills/planning-with-files/
~/.codex/hooks/
~/.codex/tools/register-planning-hooks.py
~/.codex/tools/planning-hooks-mode.py
```

The installer keeps the skill directory exact with `rsync --delete`, then overlays this package's hook and tool files into `~/.codex/hooks` and `~/.codex/tools` without deleting unrelated files.

Override the target home when testing:

```bash
CODEX_HOME=/tmp/codex-test ./install.sh
```

## Register A Project

Hooks are project-level. Register a project with:

```bash
python3 ~/.codex/tools/register-planning-hooks.py /path/to/project
```

The registrar writes:

```text
/path/to/project/.codex/hooks.json
/path/to/project/.planning/.hooks_mode
```

The generated `hooks.json` matches `hooks/hooks.json` in this repository.
If `.planning/.hooks_mode` does not already exist, the registrar writes `on`.

Use one command during install:

```bash
./install.sh --register /path/to/project --mode on
```

## Modes

Use `on` for normal behavior. In this mode, hooks are active, but context is rendered only after the session has its own `.planning/sessions/<session-id>.active_plan`.

Use `off` when a project should not run planning hooks.

Use `session` only for manual opt-in experiments. `init-session.sh --plan-dir` writes both `<session-id>.active_plan` and `<session-id>.attached` when a stable session id is available, so a newly created task can attach itself. If no stable session id is available, `session` mode stays silent.

## Creating A New Plan

Always create new plans through the skill script:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

Do not manually create `.planning/<plan-id>/` for new tasks.

The script creates:

```text
.planning/<plan-id>/task_plan.md
.planning/<plan-id>/findings.md
.planning/<plan-id>/progress.md
.planning/.active_plan
```

It also prints `PLAN_ID=<plan-id>`. Immediately after creation, use that id and work only inside `.planning/<PLAN_ID>/`.

When `CODEX_THREAD_ID` or `PWF_SESSION_ID` is available, the script immediately binds the current Codex session:

```text
.planning/sessions/<stable-session-id>.active_plan
.planning/sessions/<stable-session-id>.attached
```

After the Bash tool call finishes, `PostToolUse` sees `init-session.sh` in the command text and validates or backfills the same binding. It does not report success if no stable session id exists.

The stable session id is resolved from `PWF_SESSION_ID`, `CODEX_THREAD_ID`, transcript UUID, and other stable conversation/session fields. `turn_id` is ignored by default because Codex can produce multiple turn ids inside one conversation; set `PWF_ALLOW_TURN_ID_SESSION=1` only for legacy debugging.

## Reading The Current Plan

Hooks read the session plan, not the project active plan.

The Python adapter resolves the session plan:

```text
.planning/sessions/<session-id>.active_plan
```

Then it injects:

```text
PLAN_ID=<plan-id>
```

into the shell hook subprocess.

`hooks/resolve-plan-dir.sh` resolves in this order:

1. `$PLAN_ID`
2. `.planning/.active_plan`
3. newest `.planning/<plan-id>/`

For hook-driven context, step 1 is always used when a session plan exists. If no session plan exists, the Python adapter returns before calling shell hooks, so the shell fallback to `.active_plan` is not used by `SessionStart`, `UserPromptSubmit`, `Stop`, or `PermissionRequest`.

Do not run `resolve-plan-dir.sh` bare in ordinary agent Bash as a session resolver. Bare shell has no hook-injected `PLAN_ID`, so the resolver can fall back to `.planning/.active_plan` and read another session's plan.

For manual debugging only, explicitly provide the session plan id:

```bash
PLAN_ID="$(cat .planning/sessions/<session-id>.active_plan)"
PLAN_DIR="$(PLAN_ID="$PLAN_ID" sh ~/.codex/hooks/resolve-plan-dir.sh)"
```

## Hook Details

### SessionStart

Runs only when a session plan already exists. It calls `session-start.sh`, which runs `session-catchup.py` and then renders the same context as `UserPromptSubmit`.

### UserPromptSubmit

If the prompt includes `临时任务`, it creates a session-scoped temporary-off marker and returns without context.

If a session plan exists, it renders:

- the first 50 lines of `task_plan.md`;
- the last 20 lines of `progress.md`;
- canonical `task_plan`, `findings`, and `progress` file paths for this session;
- a warning not to read `.planning/.active_plan`, root-level `./task_plan.md`, or another `.planning/<dir>/` as current session context.

If no session plan exists, it stays silent.

### PreToolUse

Registered only for Bash.

For `init-session.sh` / `init-session.ps1`, it records the previous project active plan so `PostToolUse` can confirm whether a new plan was created.

It also blocks bare resolver calls such as:

```bash
sh ~/.codex/hooks/resolve-plan-dir.sh
```

unless the command explicitly sets `PLAN_ID` or `PWF_ALLOW_BARE_RESOLVE=1`.

It does not print normal planning reminders.

### PostToolUse

Registered only for Bash.

If the command contains `init-session.sh` or `init-session.ps1`, it validates or backfills the current session binding after the script completes.

If the command is not a plan-creation command and a session plan exists, it prints:

```text
[planning-with-files] Session plan: <plan-dir>
[planning-with-files] Update <plan-dir>/progress.md with what you just did. If a phase is now complete, update <plan-dir>/task_plan.md status.
```

If no session plan exists, it stays silent.

### Stop

Checks only the session plan. It supports both official `### Phase` status blocks and table-style phase status rows.

Completed plan:

```text
[planning-with-files] ALL PHASES COMPLETE
```

Incomplete plan:

```text
[planning-with-files] Task incomplete
```

### PermissionRequest

If a session plan exists, it reminds the user to review the current phase before approving.

## Temporary Tasks

Prompt prefix or phrase:

```text
临时任务
```

turns planning hooks off for that session turn. The marker is stored under `.planning/sessions/` when a session id is available. `Stop` clears it.

This affects only planning-with-files hooks, not other hooks.

## Verification Commands

Check installed Python syntax:

```bash
python3 - <<'PY'
from pathlib import Path
import ast
for p in Path.home().joinpath('.codex/hooks').glob('*.py'):
    ast.parse(p.read_text())
    print('OK', p)
for p in Path.home().joinpath('.codex/tools').glob('*.py'):
    ast.parse(p.read_text())
    print('OK', p)
PY
```

Check project hook JSON:

```bash
python3 -m json.tool /path/to/project/.codex/hooks.json >/dev/null
```

Check mode:

```bash
python3 ~/.codex/tools/planning-hooks-mode.py status /path/to/project
```

Run the empty-project session-binding smoke test:

```bash
~/.codex/tools/smoke-test-codex-session-binding.sh
```

Create a smoke plan:

```bash
cd /path/to/project
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Migration Smoke Test"
```

Then inspect:

```bash
cat .planning/.active_plan
find .planning/sessions -maxdepth 1 -name '*.active_plan' -print -exec cat {} \;
```

## Troubleshooting

### Hooks do not run after registration

Confirm the project was opened from the same root where `.codex/hooks.json` exists.

Confirm mode:

```bash
cat .planning/.hooks_mode
```

For normal behavior, use:

```bash
python3 ~/.codex/tools/planning-hooks-mode.py on .
```

### A new session has no planning context

This is expected until the session is bound. Run:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

or continue in a session that already has `.planning/sessions/<session-id>.active_plan`.

### There are old session plan files with unexpected ids

Older versions could create session files from turn-level ids. They are historical leftovers. Current hook context prefers stable ids from `PWF_SESSION_ID`, `CODEX_THREAD_ID`, transcript UUID, and other conversation/session fields. `turn_id` is ignored unless `PWF_ALLOW_TURN_ID_SESSION=1` is set.

### The agent reads `.planning/.active_plan` or bare `resolve-plan-dir.sh` manually

The hook path does not do this once session binding exists. `PreToolUse` blocks a known bare resolver Bash call while planning hooks are active, but an agent can still manually read `.planning/.active_plan` or inspect another directory. Project instructions should say:

```text
Use the hook-injected canonical plan files for this session. Do not read .planning/.active_plan, another .planning/<dir>/, or run resolve-plan-dir.sh bare as a session resolver.
```

## Updating This Repository From A Live Machine

When changing the live local setup, sync these paths back into the repository:

```text
~/.codex/skills/planning-with-files/ -> skills/planning-with-files/
~/.codex/hooks/                      -> hooks/
~/.codex/tools/register-planning-hooks.py
~/.codex/tools/planning-hooks-mode.py
```

Do not copy `__pycache__/`, `.DS_Store`, backup files, or project-local `.planning/` state.
