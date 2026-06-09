# Codex Sync Design: Prevent Cross-Plan Reads (Step 1 + Step 2 + Step 3)

This document records the Codex `main` implementation of the Claude-side `2.43.0-claude.4` anti cross-plan-read update.

It applies to the Codex runtime installed under `~/.codex/...` and project hook manifests under `<project>/.codex/hooks.json`.

## 0. Background And Goal

The failure mode is:

1. A Codex session is correctly bound to one session plan.
2. Hook-injected context is correct.
3. The agent later reads `.planning/.active_plan`, another `.planning/<dir>/`, or a root-level `./task_plan.md`.
4. The agent continues under the wrong plan.

The root cause is that hooks control what context is injected, but they do not automatically control what files the agent later reads with Bash/Read/Glob.

The fix is intentionally scoped:

- Keep `.planning/.active_plan`.
- Keep the resolver fallback chain for compatibility.
- Keep legacy root `./task_plan.md` as read-only fallback.
- Do not delete existing plans or change `.planning/` data layout.
- Change injected text and agent-facing guidance so current-session work uses only canonical paths.

## 1. Step 1: Renderer Names Canonical Paths

The Codex renderer is:

```text
hooks/user-prompt-submit.sh
```

`SessionStart` reuses the same renderer through:

```text
hooks/session-start.sh
```

When a plan is resolved, the renderer outputs:

```text
[planning-with-files] CANONICAL PLAN FILES for THIS session — read & update ONLY these:
  task_plan : <path>
  findings  : <path>
  progress  : <path>
```

In directory-plan mode, the renderer also outputs one of two source labels:

```text
[planning-with-files] This session is BOUND to plan dir: <plan-dir>
```

or:

```text
[planning-with-files] No session binding — RESOLVED via project default to plan dir: <plan-dir>
```

Then it warns:

```text
[planning-with-files] Do NOT read or edit .planning/.active_plan, a root-level ./task_plan.md, or any other .planning/<dir>/ — those belong to other plans/sessions. Use ONLY the files listed above.
```

For Codex, the Python adapter wraps the renderer output as:

```json
{"systemMessage": "..."}
```

This wrapper differs from Claude Code, but the shell renderer text is intentionally aligned with the Claude-side behavior.

## 2. Step 2: Directory-Based Entry Guidance

Codex `main` does not ship Claude plugin slash commands such as `commands/plan.md`. Therefore the Codex equivalent entrypoint is the skill guidance:

```text
skills/planning-with-files/SKILL.md
```

New tasks should be created with:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

This creates:

```text
.planning/<id>/task_plan.md
.planning/<id>/findings.md
.planning/<id>/progress.md
```

and prints:

```text
PLAN_ID=<id>
```

Immediately after creation, work only inside:

```text
.planning/<PLAN_ID>/
```

On later turns, use the hook-injected canonical file paths.

Do not create root-level `task_plan.md` for new tasks. Do not read `.planning/.active_plan` or other plan directories as current-session context.

## 3. Step 3: Resolver Is Not Session-Aware In Plain Shell

`resolve-plan-dir.sh` checks:

1. `$PLAN_ID`
2. `.planning/.active_plan`
3. newest `.planning/<dir>/`
4. legacy root mode / empty output

The important correction is:

```text
PLAN_ID is injected only by the Python hook adapter before it calls shell renderers.
```

Therefore:

- Inside hooks, `resolve-plan-dir.sh` is session-aware because the adapter injects `PLAN_ID=<session-plan-id>`.
- In ordinary agent Bash, `resolve-plan-dir.sh` is not session-aware unless the command explicitly provides the correct `PLAN_ID`.
- If the agent runs the resolver bare in a multi-plan project, it can fall back to `.planning/.active_plan` and pick the wrong plan.

Agent-facing guidance must therefore say:

1. Continuing an existing plan: use hook-injected canonical file paths.
2. Creating a new plan: use the `PLAN_ID=<id>` printed by `init-session.sh --plan-dir`.
3. Do not run `resolve-plan-dir.sh` yourself as a current-session resolver in ordinary Bash.

The resolver remains unchanged for compatibility and internal hook use.

## 4. PreToolUse Renderer Fix

The Codex pre-tool shell renderer is:

```text
hooks/pre-tool-use.sh
```

If it is used, it now prints resolved file paths:

```text
[planning-with-files] Active plan: <title> (<task_plan_path>)
Re-read <task_plan_path> / <findings_path> if this Bash command changes project state. Do not read other plans.
```

It no longer tells the agent to read bare `task_plan.md/findings.md`.

Current Codex `pre_tool_use.py` remains intentionally quiet for ordinary Bash commands; this shell renderer fix is for parity and future activation, not a change in normal PreToolUse behavior.

## 5. What Did Not Change

The following remain intentionally unchanged:

- `init-session.sh` still supports legacy root mode when called without a title and without `--plan-dir`.
- `resolve-plan-dir.sh` still has the fallback order `$PLAN_ID`, `.planning/.active_plan`, newest plan dir, then empty output.
- `.planning/.active_plan` is still written by `init-session.sh` and read by `PostToolUse` during session binding.
- Existing root-level legacy plans remain readable as fallback.
- `.planning/` data remains shared across Claude and Codex; no Codex-only plan directory format was introduced.

## 6. Parity Checklist

- [x] Renderer outputs canonical `task_plan`, `findings`, and `progress` paths.
- [x] Renderer distinguishes `BOUND` from `RESOLVED via project default`.
- [x] Renderer warns not to read `.planning/.active_plan`, root-level `./task_plan.md`, or another `.planning/<dir>/`.
- [x] Skill guidance creates new tasks with `init-session.sh --plan-dir`.
- [x] Skill guidance uses printed `PLAN_ID=<id>` immediately after creation.
- [x] Skill guidance forbids bare manual `resolve-plan-dir.sh` as a session resolver.
- [x] `pre-tool-use.sh` uses resolved file paths instead of bare filenames.
- [x] Legacy root fallback remains read-only compatibility.
- [x] Verification includes the known failure case: bare resolver returns project default while hook-injected `PLAN_ID` returns the session plan.

## 7. Verification

Renderer three-state smoke:

1. Directory plan with `PLAN_ID`: outputs canonical paths, `BOUND`, and anti cross-plan-read warning.
2. Directory plan without `PLAN_ID`: outputs canonical paths, `RESOLVED via project default`, and anti cross-plan-read warning.
3. Legacy root plan: outputs canonical root file paths without bound/default plan-dir warning.
4. No plan: outputs nothing and exits 0.

End-to-end smoke:

1. Temporary `CODEX_HOME`.
2. Register a temporary project.
3. Run `init-session.sh --plan-dir "Session A Plan"` and bind session A.
4. Run `init-session.sh --plan-dir "Session B Plan"` and bind session B.
5. Confirm project `.active_plan` points to B.
6. Confirm session A `UserPromptSubmit` still injects A's canonical files and not B's.
7. Confirm no root-level `task_plan.md` is created.

Known failure demonstration:

```bash
sh ~/.codex/hooks/resolve-plan-dir.sh
```

may return the project default. This is expected and is why agent guidance forbids using it bare as a session resolver.

Correct hook-style resolution requires explicit `PLAN_ID`:

```bash
PLAN_ID="<session-plan-id>" sh ~/.codex/hooks/resolve-plan-dir.sh
```
