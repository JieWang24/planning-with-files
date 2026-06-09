# planning-with-files for Codex

This repository packages the local Codex customization of `planning-with-files` so it can be moved to another machine without losing behavior.

The `main` branch is the Codex default branch. The `claude` branch is kept separately for the Claude Code plugin version.

## What This Package Contains

| Path | Purpose |
| --- | --- |
| `skills/planning-with-files/` | The Codex skill installed at `~/.codex/skills/planning-with-files`. Includes `SKILL.md`, scripts, templates, and references. |
| `hooks/` | Codex hook adapters and shell renderers installed at `~/.codex/hooks`. |
| `hooks/hooks.json` | Project hook template matching the registrar output. |
| `tools/register-planning-hooks.py` | Registers project-level `.codex/hooks.json` entries. |
| `tools/planning-hooks-mode.py` | Sets or reads `.planning/.hooks_mode`. |
| `tools/planning-hooks-debug.py` | Sets or reads project-level planning hook debug output. |
| `tools/smoke-test-codex-session-binding.sh` | End-to-end empty-project smoke test for session-plan binding. |
| `tools/smoke-test-hook-debug.sh` | Simulates all planning hook events and verifies debug logging. |
| `install.sh` | Installs the portable package into `~/.codex` and optionally registers projects. |
| `docs/codex-setup.md` | Detailed install, migration, behavior, and troubleshooting guide. |
| `docs/functional-spec.md` | Full behavior contract for installation, registration, hooks, modes, and session binding. |
| `docs/codex-sync-step1-2.md` | Codex implementation note for anti cross-plan reads and stable session binding. |

## Quick Install On A New Machine

```bash
git clone <this-repo-url> planning-with-files
cd planning-with-files
git checkout main
./install.sh
```

Then register each project where you want planning hooks:

```bash
python3 ~/.codex/tools/register-planning-hooks.py /path/to/project
```

Or do both during installation:

```bash
./install.sh --register /path/to/project --mode on
```

Use `on` for the default script-first behavior described below.
The registrar creates `.planning/.hooks_mode` with `on` when the file does not already exist.

## Runtime Model

This fork intentionally uses project-level Codex hooks rather than global hooks.

New planning tasks must be created through:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

The script creates:

```text
.planning/<plan-id>/task_plan.md
.planning/<plan-id>/findings.md
.planning/<plan-id>/progress.md
.planning/.active_plan
```

It also prints `PLAN_ID=<plan-id>`. Immediately after creation, use that id and work only inside `.planning/<PLAN_ID>/`.

When `CODEX_THREAD_ID` or `PWF_SESSION_ID` is available, `init-session.sh` immediately binds the current Codex session to the new plan:

```text
.planning/sessions/<session-id>.active_plan
.planning/sessions/<session-id>.attached
```

`PostToolUse` then validates or backfills the binding after the Bash command. It no longer reports a session binding when no stable session id exists.

`SessionStart`, `UserPromptSubmit`, `Stop`, and `PermissionRequest` read only the session plan. They do not fall back to `.planning/.active_plan` when no session plan exists.

When a session plan exists, hook output names the canonical files for this session:

```text
[planning-with-files] CANONICAL PLAN FILES for THIS session — read & update ONLY these:
  task_plan : <path>
  findings  : <path>
  progress  : <path>
```

Read and update only those files. Do not read `.planning/.active_plan`, a root-level `./task_plan.md`, or another `.planning/<dir>/` as current task context.

Do not run `resolve-plan-dir.sh` yourself as a session resolver in ordinary Bash. It is session-aware inside hooks because the Python adapter injects `PLAN_ID`; bare shell calls can fall back to `.planning/.active_plan`.

## Hook Behavior Summary

| Hook | Current behavior |
| --- | --- |
| `SessionStart` | If the current session has a session plan, render that plan context. Otherwise stay silent. |
| `UserPromptSubmit` | If prompt contains `临时任务`, temporarily disables planning hooks for that turn. Otherwise renders session-plan context plus canonical file paths when bound. |
| `PreToolUse` | Bash-only. Records the active plan before `init-session` and blocks bare `resolve-plan-dir.sh` / `.ps1` calls without `PLAN_ID`. |
| `PostToolUse` | If Bash command created a plan with `init-session`, validates or backfills session binding. Otherwise, if session plan exists, reminds the agent to update the canonical `progress.md` and phase status paths. |
| `Stop` | Checks only the session plan for completion. Blocks incomplete tasks unless Codex reports the stop hook is already active. |
| `PermissionRequest` | If session plan exists, reminds the user to review current phase before approving. |

## Hook Modes

Per project, mode is stored in:

```text
.planning/.hooks_mode
```

Supported values:

| Mode | Meaning |
| --- | --- |
| `on` | Planning hooks run for the project. Recommended default for this script-first workflow. |
| `off` | Planning hooks are disabled for the project. |
| `session` | Hooks run only when `.planning/sessions/<session-id>.attached` exists. `init-session.sh --plan-dir` creates it when a stable session id is available. Use mainly for manual opt-in experiments. |

Manage the mode with:

```bash
python3 ~/.codex/tools/planning-hooks-mode.py status /path/to/project
python3 ~/.codex/tools/planning-hooks-mode.py on /path/to/project
python3 ~/.codex/tools/planning-hooks-mode.py off /path/to/project
python3 ~/.codex/tools/planning-hooks-mode.py session /path/to/project
```

## Temporary Tasks

If a prompt contains `临时任务`, `UserPromptSubmit` creates a per-session temporary-off marker. Planning hooks stay silent for that turn and clear on `Stop`.

Use this for one-off questions or simple commands that should not activate planning.

## Debug Mode

Debug mode is project-local and opt-in. It is useful when you want to prove which hooks fired, even when their normal behavior is silent.

```bash
python3 ~/.codex/tools/planning-hooks-debug.py on /path/to/project
python3 ~/.codex/tools/planning-hooks-debug.py status /path/to/project
python3 ~/.codex/tools/planning-hooks-debug.py off /path/to/project
```

When enabled, each planning hook appends one JSON line to:

```text
<project>/.planning/debug/hook-events.jsonl
```

Hooks also emit a short `[planning-with-files debug] ...` line when Codex allows that hook to return visible context. `UserPromptSubmit` may still appear as injected context rather than a UI warning, so the JSONL log is the source of truth.

## Migration Checklist

1. Clone this repository on the new machine.
2. Check out `main`.
3. Run `./install.sh`.
4. Register project hooks with `register-planning-hooks.py`.
5. Confirm project mode is `on`.
6. Start a new Codex session.
7. Create a test plan with `init-session.sh --plan-dir "Migration Smoke Test"`.
8. Confirm `.planning/sessions/<session-id>.active_plan` points to the new plan.
9. Confirm subsequent prompts render the session plan, not the project `.active_plan`.
10. Run `~/.codex/tools/smoke-test-codex-session-binding.sh` or the repository copy before trusting a migrated machine.
11. Run `~/.codex/tools/smoke-test-hook-debug.sh` to verify all six planning hook adapters can emit debug records.

See [docs/codex-setup.md](docs/codex-setup.md) for setup, [docs/functional-spec.md](docs/functional-spec.md) for the full runtime contract, and [docs/codex-sync-step1-2.md](docs/codex-sync-step1-2.md) for the anti cross-plan-read/session-binding sync note.
