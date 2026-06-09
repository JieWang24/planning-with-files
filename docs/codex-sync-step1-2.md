# Codex Sync Step 1 + Step 2

This document records the Codex `main` implementation of the Claude-side `2.43.0-claude.3` anti cross-plan-read update.

The goal is to reduce cases where a Codex session is correctly bound to one session plan, but the agent manually reads `.planning/.active_plan`, another `.planning/<dir>/`, or a legacy root `./task_plan.md`.

## Status

Implemented for Codex `main`:

- Step 1: hook-rendered context now names the canonical plan files for this session.
- Step 2: the Codex skill guidance now creates and reads directory-based plans under `.planning/<id>/`.
- Legacy root `./task_plan.md` remains read-only fallback for old projects.
- `.planning/.active_plan` remains as the project pointer and `init-session` to `PostToolUse` handoff file.
- Session-plan binding remains the hook authority for Codex session context.

## Step 1: Canonical Path Injection

The Codex renderer is:

```text
hooks/user-prompt-submit.sh
```

`SessionStart` reuses the same renderer through:

```text
hooks/session-start.sh
```

When a plan is resolved, the renderer now outputs:

```text
[planning-with-files] CANONICAL PLAN FILES for THIS session — read & update ONLY these:
  task_plan : <path>
  findings  : <path>
  progress  : <path>
```

In directory-plan mode, it also outputs:

```text
[planning-with-files] This session is bound to plan dir: <plan-dir>
[planning-with-files] Do NOT read or edit .planning/.active_plan, a root-level ./task_plan.md, or any other .planning/<dir>/ — those belong to other plans/sessions. Use ONLY the files listed above.
```

The Python Codex adapter wraps this stdout as:

```json
{"systemMessage": "..."}
```

That wrapper is Codex-specific. The shell renderer text is intentionally aligned with the Claude-side wording.

## Step 2: Directory-Based Skill Guidance

Codex does not ship the Claude plugin `commands/` slash-command directory on `main`. Therefore the equivalent Codex entrypoint is the skill guidance:

```text
skills/planning-with-files/SKILL.md
```

The skill now instructs agents to:

1. Use hook-injected canonical file paths when present.
2. Create new plans with:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

3. Work inside `.planning/<id>/`.
4. Avoid creating root-level `task_plan.md` for new tasks.
5. Avoid using `.planning/.active_plan` as current session context.

## What Did Not Change

The following remain intentionally unchanged:

- `init-session.sh` still supports legacy root mode when called without a title and without `--plan-dir`.
- `resolve-plan-dir.sh` still has fallback order `$PLAN_ID`, `.planning/.active_plan`, newest plan dir, then empty output.
- `.planning/.active_plan` is still written by `init-session.sh` and read by `PostToolUse` during session binding.
- Existing root-level legacy plans remain readable as fallback.

## Codex-Specific Behavior

Codex project hooks are registered through:

```text
<project>/.codex/hooks.json
```

The installed hook adapters live under:

```text
~/.codex/hooks/
```

For hook-driven context, the Python adapter injects:

```text
PLAN_ID=<session-plan-id>
```

before calling the shell renderer. That means `resolve-plan-dir.sh` resolves the session plan through `$PLAN_ID` during hook rendering.

If an agent manually runs `resolve-plan-dir.sh` in an ordinary Bash command without `PLAN_ID`, it may fallback to `.planning/.active_plan`. That is why the injected text now names the exact canonical files and warns against manual cross-plan reads.

## Verification

Renderer three-state smoke:

1. Directory plan: outputs canonical paths, bound plan dir, and anti cross-plan-read warning.
2. Legacy root plan: outputs canonical root file paths, without bound-dir warning.
3. No plan: outputs nothing and exits 0.

End-to-end smoke:

1. Temporary `CODEX_HOME`.
2. Register a temporary project.
3. Run `init-session.sh --plan-dir "Default Mode Smoke Test"`.
4. Simulate `PostToolUse` and verify `.planning/sessions/<session-id>.active_plan`.
5. Simulate `UserPromptSubmit` and verify canonical file output.
