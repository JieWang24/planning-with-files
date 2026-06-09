# File Inventory

This inventory records what should be present on a migrated machine.

## Skill

Installed to:

```text
~/.codex/skills/planning-with-files/
```

Repository source:

```text
skills/planning-with-files/
```

Important files:

| File | Purpose |
| --- | --- |
| `SKILL.md` | Main trigger and workflow contract. Includes script-first task creation rule. |
| `scripts/init-session.sh` | Canonical new task creator for macOS/Linux. |
| `scripts/init-session.ps1` | Canonical new task creator for PowerShell. |
| `scripts/check-complete.sh` | Completion checker used by stop-style workflows. |
| `scripts/session-catchup.py` | Session recovery helper. |
| `scripts/resolve-plan-dir.sh` | Plan directory resolver. |
| `templates/*.md` | Default task, findings, and progress templates. |
| `references/*.md` | Longer reference material. |

## Hooks

Installed to:

```text
~/.codex/hooks/
```

Repository source:

```text
hooks/
```

Important files:

| File | Purpose |
| --- | --- |
| `planning_hook_adapter.py` | Shared Codex payload parser, mode gate, session-plan resolver, and shell runner. |
| `session_start.py` | Codex `SessionStart` adapter. |
| `user_prompt_submit.py` | Codex `UserPromptSubmit` adapter. |
| `pre_tool_use.py` | Codex `PreToolUse` adapter, currently plan-creation detection only. |
| `post_tool_use.py` | Codex `PostToolUse` adapter, binds sessions after `init-session` and reminds after normal Bash. |
| `stop.py` | Codex `Stop` adapter. |
| `permission_request.py` | Codex `PermissionRequest` adapter. |
| `resolve-plan-dir.sh` | Shell resolver used by hook renderers. |
| `user-prompt-submit.sh` | Renders plan context. |
| `post-tool-use.sh` | Renders progress-update reminder. |
| `stop.sh` | Counts phase completion, including table-style plans. |
| `hooks.json` | Project hook template matching `register-planning-hooks.py`. |

## Tools

Installed to:

```text
~/.codex/tools/
```

Repository source:

```text
tools/
```

| File | Purpose |
| --- | --- |
| `register-planning-hooks.py` | Writes project-level `.codex/hooks.json` and initializes `.planning/.hooks_mode` to `on` when missing. |
| `planning-hooks-mode.py` | Reads or sets `.planning/.hooks_mode`. |

## Project State

## Documentation

| File | Purpose |
| --- | --- |
| `docs/codex-setup.md` | Installation, migration, behavior, and troubleshooting guide. |
| `docs/functional-spec.md` | Full Codex runtime behavior contract. |
| `docs/codex-sync-step1-2.md` | Implementation note for canonical plan paths and directory-plan guidance synced from the Claude branch. |

## Project State

These files are generated in each project and are not stored in this repository:

```text
.codex/hooks.json
.planning/.hooks_mode
.planning/.active_plan
.planning/<plan-id>/
.planning/sessions/<session-id>.active_plan
.planning/sessions/<session-id>.temporary-off
```

Project state should remain project-local.
