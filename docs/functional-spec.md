# Functional Specification

This document is the detailed behavior contract for the Codex `planning-with-files` package on the `main` branch.

It describes the local customized implementation as it is meant to run after installation into `~/.codex`.

## Scope

This package provides four things:

1. A Codex skill installed at `~/.codex/skills/planning-with-files`.
2. Planning hook adapters installed at `~/.codex/hooks`.
3. Registration and mode tools installed at `~/.codex/tools`.
4. Documentation and migration checks stored in this repository.

The package does not store project task state. Each project owns its own `.planning/` directory and `.codex/hooks.json`.

## Branch Contract

Use `main` for Codex App and Codex CLI.

The `claude` branch is a separate Claude Code implementation. It has related planning concepts, but its settings format, hook behavior, and installation paths are not the same as this Codex branch.

## Installed File Layout

After running `./install.sh`, the target machine should contain:

```text
~/.codex/skills/planning-with-files/
~/.codex/hooks/
~/.codex/tools/register-planning-hooks.py
~/.codex/tools/planning-hooks-mode.py
```

The installer uses `rsync --delete` only for `~/.codex/skills/planning-with-files/`, because that directory is package-owned.

The installer overlays package files into `~/.codex/hooks/` and `~/.codex/tools/` without deleting unrelated files. This keeps migration safe on machines that already have non-planning Codex hooks or tools.

## Project File Layout

Registering a project creates or updates:

```text
<project>/.codex/hooks.json
<project>/.planning/.hooks_mode
```

Creating a planning task creates:

```text
<project>/.planning/<plan-id>/task_plan.md
<project>/.planning/<plan-id>/findings.md
<project>/.planning/<plan-id>/progress.md
<project>/.planning/.active_plan
```

Binding a Codex session creates:

```text
<project>/.planning/sessions/<session-id>.active_plan
```

Temporary task suppression creates and later clears:

```text
<project>/.planning/sessions/<session-id>.temporary-off
```

When no session id is available, the temporary marker falls back to:

```text
<project>/.planning/.temporary-off
```

## Core Invariants

New planning tasks are script-first. A new task must be created by:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

or on PowerShell:

```powershell
~/.codex/skills/planning-with-files/scripts/init-session.ps1 "Task Title"
```

Do not manually create `.planning/<plan-id>/` for a new task.

Hooks use the session plan, not the project active plan, as the current context source.

`.planning/.active_plan` is only a project-level pointer. It is used by `PostToolUse` immediately after `init-session` finishes, so the current session can be bound to the new plan.

After binding, hook context comes from:

```text
.planning/sessions/<session-id>.active_plan
```

If a session has no session plan, the Python adapters stay silent for `SessionStart`, `UserPromptSubmit`, `Stop`, and `PermissionRequest`.

When hook context is injected, it explicitly names the canonical files for that session:

```text
[planning-with-files] CANONICAL PLAN FILES for THIS session — read & update ONLY these:
  task_plan : <path>
  findings  : <path>
  progress  : <path>
```

Agents should read and update only those paths. In directory-plan mode, the injected text also forbids reading or editing `.planning/.active_plan`, root-level `./task_plan.md`, or any other `.planning/<dir>/` as current session context.

All hook adapters fail open. Hook errors are swallowed by `main_guard`, so a planning hook failure should not break ordinary Codex tool usage.

## Skill Contract

The skill entrypoint is:

```text
skills/planning-with-files/SKILL.md
```

The skill explains when to use file-based planning, requires script-first task creation with `--plan-dir`, and instructs agents to use hook-injected canonical file paths for the current session.

The skill frontmatter intentionally does not declare active hooks. Runtime hooks are registered at the project level through `.codex/hooks.json`. This avoids stale root-level `task_plan.md` behavior and keeps all hook execution under the customized session-plan flow.

## Installation Flow

Run:

```bash
./install.sh
```

The script:

1. Resolves the repository directory.
2. Uses `CODEX_HOME` if set, otherwise `$HOME/.codex`.
3. Requires `python3` and `rsync`.
4. Creates `skills`, `hooks`, and `tools` directories under `CODEX_HOME`.
5. Syncs `skills/planning-with-files/` exactly into `CODEX_HOME`.
6. Overlays `hooks/` and `tools/` into `CODEX_HOME`.
7. Marks bundled scripts executable.
8. Optionally registers project hooks for every `--register <project>` argument.
9. Optionally sets a project mode with `--mode on`, `--mode off`, or `--mode session`.

Example:

```bash
CODEX_HOME=/tmp/codex-test ./install.sh --register /tmp/project --mode on
```

## Project Registration Flow

Run:

```bash
python3 ~/.codex/tools/register-planning-hooks.py /path/to/project
```

The registrar:

1. Resolves the project path.
2. Creates `<project>/.codex/` if needed.
3. Loads or creates `<project>/.codex/hooks.json`.
4. Ensures `hooks` is a JSON object.
5. Removes old planning hook entries for all package-owned events.
6. Adds the current planning hook entries.
7. Writes formatted JSON.
8. Creates `<project>/.planning/.hooks_mode` with `on` if it does not already exist.

The registrar replaces only planning hook entries it can identify. It preserves unrelated hooks registered in the same project.

The project hook template is also stored at:

```text
hooks/hooks.json
```

That template should match the registrar output for a fresh project.

## Hook Manifest

The generated manifest registers these Codex hook events:

| Event | Matcher | Command |
| --- | --- | --- |
| `PermissionRequest` | none | `permission_request.py` |
| `PostToolUse` | `Bash` | `post_tool_use.py` |
| `PreToolUse` | `Bash` | `pre_tool_use.py` |
| `SessionStart` | `startup|resume` | `session_start.py` |
| `Stop` | none | `stop.py` |
| `UserPromptSubmit` | none | `user_prompt_submit.py` |

Each command first tries a project-local copy:

```text
python3 .codex/hooks/<hook>.py
```

Then it falls back to:

```text
python3 "$HOME/.codex/hooks/<hook>.py"
```

This allows a project to override a hook locally without changing the global installed package.

## Mode Gate

Planning hooks can be controlled per project by:

```text
.planning/.hooks_mode
```

Supported modes:

| Mode | Behavior |
| --- | --- |
| `on` | Planning hook adapters are allowed to run. A session still needs a session plan before context is rendered. |
| `off` | Planning hook adapters stay silent for the project. |
| `session` | Hook adapters run only when `.planning/sessions/<session-id>.attached` exists. |

The environment variable `PWF_HOOKS` overrides the project file:

| `PWF_HOOKS` value | Behavior |
| --- | --- |
| `on`, `1`, `true`, `yes`, `enable`, `enabled` | Force hooks on. |
| `off`, `0`, `false`, `no`, `disable`, `disabled` | Force hooks off. |

If neither `PWF_HOOKS` nor `.planning/.hooks_mode` exists, the adapter enters legacy compatibility mode:

1. If `.planning/sessions/` does not exist, the session is considered attached.
2. If `.planning/sessions/` exists and there is no session id, hooks stay silent.
3. If `.planning/sessions/` exists and there is a session id, hooks run only if `<session-id>.attached` exists.

New registrations create `.hooks_mode=on`, so normal migrated projects do not rely on legacy compatibility mode.

## Session Identity

The shared adapter resolves a session id in this order:

1. Parse the last UUID from the `transcript_path` filename.
2. Use `thread_id`.
3. Use `conversation_id`.
4. Use `session_id`.
5. Use `turn_id`.
6. Use `PWF_SESSION_ID`.

The transcript UUID is preferred because it is stable for a Codex session. Turn-level ids are avoided when the transcript path is available.

## Plan Creation Flow

Run from the project root:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

The script:

1. Parses `--template`, `--plan-dir`, and the task title.
2. Enters slug mode when a title is provided or `--plan-dir` is used.
3. Slugifies the title.
4. Creates a unique plan id like `2026-06-08-task-title`.
5. Creates `.planning/<plan-id>/`.
6. Writes `task_plan.md`, `findings.md`, and `progress.md`.
7. Updates `.planning/.active_plan` with the new plan id.
8. Prints the plan id and a terminal `PLAN_ID` hint.

After the Bash command completes, Codex runs `PostToolUse`.

`post_tool_use.py` checks whether the command text contains:

```text
init-session.sh
init-session.ps1
```

If it does, the adapter:

1. Reads `.planning/.active_plan`.
2. Verifies `.planning/<plan-id>/task_plan.md` exists.
3. Writes `.planning/sessions/<session-id>.active_plan`.
4. Emits:

```text
[planning-with-files] Session plan bound to: <plan-id>
```

This is the only automatic binding path for new tasks.

## Session Plan Resolution

For Python adapters, the current plan is:

```text
.planning/sessions/<session-id>.active_plan
```

The adapter validates that the referenced plan contains:

```text
.planning/<plan-id>/task_plan.md
```

When a shell hook renderer needs a plan directory, Python injects:

```text
PLAN_ID=<plan-id>
```

Then `hooks/resolve-plan-dir.sh` resolves in this order:

1. `$PLAN_ID`
2. `.planning/.active_plan`
3. newest `.planning/<plan-id>/`

For hook-driven context, step 1 is the intended path. The fallback paths exist for manual debugging and legacy shell usage.

The resolver is not session-aware in ordinary Bash unless the caller explicitly sets `PLAN_ID`. Agent-facing instructions must not tell agents to run it bare as a current-session resolver.

## Hook Adapter Behavior

### `session_start.py`

Event: `SessionStart`.

Flow:

1. Load Codex JSON payload from stdin.
2. Resolve project root and session id.
3. Check mode gate.
4. Require an existing session plan.
5. Run `session-start.sh`.
6. Emit shell output as `systemMessage`.

`session-start.sh` runs `session-catchup.py` and then delegates to `user-prompt-submit.sh`.

If there is no session plan, the hook stays silent. It does not bind to `.planning/.active_plan`.

### `user_prompt_submit.py`

Event: `UserPromptSubmit`.

Flow:

1. Load payload.
2. If any payload text contains `临时任务`, create a temporary-off marker and return.
3. Otherwise clear any temporary-off marker from a previous turn.
4. Check mode gate.
5. Require an existing session plan.
6. Run `user-prompt-submit.sh`.
7. Emit plan context as `systemMessage`.

Rendered context includes:

1. A planning header.
2. The first 50 lines of `task_plan.md`.
3. The last 20 lines of `progress.md`.
4. `===BEGIN PLAN DATA===` / `===END PLAN DATA===` framing so plan content is treated as data.
5. Canonical `task_plan`, `findings`, and `progress` paths for this session.
6. In directory-plan mode, a warning not to read or edit `.planning/.active_plan`, root-level `./task_plan.md`, or any other `.planning/<dir>/`.
7. If a plan attestation exists, `Plan-SHA256`; if the hash mismatches, plan injection is blocked with a tamper warning.

### `pre_tool_use.py`

Event: `PreToolUse`.

Matcher: `Bash`.

Flow:

1. Load payload.
2. Check mode gate.
3. Return unless the Bash command contains `init-session.sh` or `init-session.ps1`.
4. Emit no normal reminder output.

This hook is intentionally quiet. It exists so the creation flow can be detected consistently around Bash commands without dumping full planning files before every command.

The shell renderer `pre-tool-use.sh` still contains the short reminder form:

```text
[planning-with-files] Active plan: <title> (<task_plan_path>)
Re-read <task_plan_path> / <findings_path> if this Bash command changes project state. Do not read other plans.
```

The current Python adapter does not call that renderer for normal commands.

### `post_tool_use.py`

Event: `PostToolUse`.

Matcher: `Bash`.

Flow for plan creation:

1. Check mode gate.
2. If command contains `init-session.sh` or `init-session.ps1`, bind this session to `.planning/.active_plan`.
3. Emit a session binding message if the plan changed.

Flow for ordinary Bash:

1. Check mode gate.
2. Require an existing session plan.
3. Run `post-tool-use.sh`.
4. Emit its reminder.

Reminder:

```text
[planning-with-files] Update progress.md with what you just did. If a phase is now complete, update task_plan.md status.
[codex-scholar] For KB edits, route project-owned ideas/specs to Designs/ before Experiments/, Results/, or paper claims.
```

If there is no session plan, ordinary Bash commands get no planning reminder.

### `stop.py`

Event: `Stop`.

Flow:

1. If temporary-off marker exists, clear it and return.
2. Check mode gate.
3. Require an existing session plan.
4. Run `stop.sh`.
5. Parse JSON from `stop.sh`.
6. If all phases are complete, emit `systemMessage`.
7. If incomplete and Codex reports `stop_hook_active`, emit `systemMessage`.
8. If incomplete and this is the first stop pass, emit `decision=block`.

This preserves the planning contract without causing recursive stop-hook deadlock.

`stop.sh` supports:

1. Official section plans using `### Phase` and `**Status:** complete`.
2. Bracket status forms such as `[complete]`, `[in_progress]`, and `[pending]`.
3. Table-style phase plans where the second column is a status.

Recognized table status aliases include English and Chinese forms:

```text
complete, completed, done, 完成, 已完成
in_progress, working, 进行中
pending, todo, not_started, 未开始, 待办, 待处理
```

### `permission_request.py`

Event: `PermissionRequest`.

Flow:

1. Check mode gate.
2. Require an existing session plan.
3. Verify `task_plan.md` exists.
4. Emit a short user-facing reminder.

This hook never blocks approval.

## Temporary Task Flow

If the user prompt contains:

```text
临时任务
```

then `UserPromptSubmit` writes a temporary-off marker and returns without rendering planning context.

While the marker exists:

1. `is_session_attached()` returns false.
2. Planning hook adapters stay silent.
3. Other unrelated hooks are not affected.

At `Stop`, `stop.py` clears the temporary marker and returns without checking the plan.

The next non-temporary prompt returns to normal behavior.

## Parallel Session Flow

The project can contain many task plans:

```text
.planning/task-a/
.planning/task-b/
.planning/task-c/
```

The project active pointer can only contain one value:

```text
.planning/.active_plan
```

That pointer is not enough for parallel Codex sessions.

Each Codex session therefore uses its own binding:

```text
.planning/sessions/<session-a>.active_plan -> task-a
.planning/sessions/<session-b>.active_plan -> task-b
```

When session A asks questions, hooks read session A's plan.

When session B asks questions, hooks read session B's plan.

If `.planning/.active_plan` later changes, existing session bindings do not change unless that same session runs `init-session` and triggers `PostToolUse` binding.

## Existing Task Continuation

For normal agent work, continue from the hook-injected canonical file paths. For manual debugging only, a human can inspect a known session-bound task by explicitly providing its plan id:

```bash
PLAN_ID="$(cat .planning/sessions/<session-id>.active_plan)"
PLAN_DIR="$(PLAN_ID="$PLAN_ID" sh ~/.codex/hooks/resolve-plan-dir.sh)"
sed -n '1,120p' "$PLAN_DIR/task_plan.md"
sed -n '1,160p' "$PLAN_DIR/findings.md"
tail -80 "$PLAN_DIR/progress.md"
```

Do not rely on `.planning/.active_plan` as the current task in a multi-session project.

Do not run `resolve-plan-dir.sh` bare as a session resolver. Without `PLAN_ID`, it can fall back to the project default.

## Completion Semantics

A plan is complete when every detected phase is complete.

For official section plans, `stop.sh` uses:

```text
### Phase
**Status:** complete
```

For table plans, it reads pipe-table rows and normalizes the second column as status.

If no complete phase structure can be detected, the stop hook returns incomplete.

## Migration Equivalence Rules

A migrated machine is equivalent when all of these are true:

1. `~/.codex/skills/planning-with-files/SKILL.md` matches `skills/planning-with-files/SKILL.md`.
2. `~/.codex/hooks/*.py` and `~/.codex/hooks/*.sh` match `hooks/`, except repository-only `hooks/hooks.json`.
3. `~/.codex/tools/register-planning-hooks.py` matches `tools/register-planning-hooks.py`.
4. `~/.codex/tools/planning-hooks-mode.py` matches `tools/planning-hooks-mode.py`.
5. A fresh registered project gets `.planning/.hooks_mode=on`.
6. A fresh registered project's `.codex/hooks.json` matches `hooks/hooks.json`.
7. Running `init-session.sh --plan-dir "Smoke Test"` creates `.planning/<plan-id>/`.
8. Simulated `PostToolUse` for that Bash command writes `.planning/sessions/<session-id>.active_plan`.
9. Simulated `UserPromptSubmit` with that session id emits the session plan context plus canonical file paths and anti cross-plan-read warning.
10. Bare `resolve-plan-dir.sh` may return the project default, while `PLAN_ID=<session-plan-id> resolve-plan-dir.sh` returns the session plan.
11. Simulated `UserPromptSubmit` containing `临时任务` suppresses planning output for that turn.

## Verification Checklist

Run from this repository:

```bash
python3 -m json.tool hooks/hooks.json >/dev/null
```

```bash
bash -n install.sh
for f in hooks/*.sh skills/planning-with-files/scripts/*.sh; do
  bash -n "$f"
done
```

```bash
python3 - <<'PY'
from pathlib import Path
import ast
root = Path('.')
for path in sorted(root.glob('hooks/*.py')) + sorted(root.glob('tools/*.py')) + sorted((root / 'skills/planning-with-files/scripts').glob('*.py')):
    ast.parse(path.read_text())
    print('OK', path)
PY
```

Check live drift:

```bash
diff -qr -x __pycache__ -x '*.pyc' -x '*.bak*' -x hooks.json ~/.codex/hooks hooks
diff -qr -x __pycache__ -x '*.pyc' -x .DS_Store ~/.codex/skills/planning-with-files skills/planning-with-files
diff -q ~/.codex/tools/register-planning-hooks.py tools/register-planning-hooks.py
diff -q ~/.codex/tools/planning-hooks-mode.py tools/planning-hooks-mode.py
```

Smoke test with a temporary Codex home:

```bash
tmp_home="$(mktemp -d)"
tmp_project="$(mktemp -d)"
sid="019e6fff-2222-7333-8444-abcdefabcdef"

CODEX_HOME="$tmp_home" ./install.sh --register "$tmp_project"
cd "$tmp_project"
"$tmp_home/skills/planning-with-files/scripts/init-session.sh" --plan-dir "Default Mode Smoke Test"

printf '{"cwd":"%s","transcript_path":"/tmp/rollout-%s.jsonl","tool_name":"Bash","tool_input":{"cmd":"%s/skills/planning-with-files/scripts/init-session.sh --plan-dir Default Mode Smoke Test"}}\n' \
  "$tmp_project" "$sid" "$tmp_home" |
  python3 "$tmp_home/hooks/post_tool_use.py"

cat "$tmp_project/.planning/.hooks_mode"
cat "$tmp_project/.planning/sessions/$sid.active_plan"
```

Expected:

```text
on
2026-...-default-mode-smoke-test
```

## Known Boundaries

The hook system cannot force an agent to avoid manual reads if it opens `.planning/.active_plan` or runs `resolve-plan-dir.sh` bare. Project instructions should explicitly say to use hook-injected canonical files or the `PLAN_ID` printed by `init-session.sh --plan-dir`.

`PreToolUse` is intentionally quiet for normal Bash commands. The active reminder is currently emitted by `PostToolUse` after Bash when a session plan exists.

`session` mode is a manual opt-in mode. It is not the normal default and requires `.planning/sessions/<session-id>.attached`.

PowerShell scripts are bundled for Windows task creation and checking. The Codex project hook registration in this branch is written around Python and shell commands, matching the current macOS/Linux Codex workflow.
