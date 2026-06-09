---
name: planning-with-files
description: Implements Manus-style file-based planning to organize and track progress on complex tasks. Creates task_plan.md, findings.md, and progress.md. Use when asked to plan out, break down, or organize a multi-step project, research task, or any work requiring 5+ tool calls. Supports automatic session recovery after /clear.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "2.44.0-codex.0"

---

# Planning with Files

Work like Manus: Use persistent markdown files as your "working memory on disk."

## FIRST: Restore This Session's Context (v2.44.0-codex.0)

**Before doing anything else**, use THIS session's canonical plan files. The planning hooks inject their exact paths at SessionStart and on each prompt:

```text
[planning-with-files] CANONICAL PLAN FILES for THIS session — read & update ONLY these:
  task_plan : <path>
  findings  : <path>
  progress  : <path>
```

1. Read those injected paths (`task_plan.md`, `progress.md`, `findings.md`). They are session-aware because the hook adapter sets `PLAN_ID` before rendering them.
   - **Do NOT run `resolve-plan-dir.sh` yourself.** In a plain shell it has no `PLAN_ID` and falls back to `.planning/.active_plan`, which is the wrong plan when several exist.
   - **Read ONLY those files. Do NOT read `.planning/.active_plan`, root-level `./task_plan.md`, or any other `.planning/<dir>/`; those belong to other sessions or legacy fallback.**
   - If no canonical paths were injected and you must recover manually, read a legacy root `./task_plan.md` only if it exists; otherwise create a plan with Quick Start below.

Then check for unsynced context from a previous session:

```bash
# Linux/macOS (auto-detects python3 or python)
SKILL_ROOT="${CODEX_SKILL_ROOT:-$HOME/.codex/skills/planning-with-files}"
$(command -v python3 || command -v python) "$SKILL_ROOT/scripts/session-catchup.py" "$(pwd)"
```

```powershell
# Windows PowerShell
python "$env:USERPROFILE\.codex\skills\planning-with-files\scripts\session-catchup.py" (Get-Location)
```

If catchup report shows unsynced context:
1. Run `git diff --stat` to see actual code changes
2. Read current planning files
3. Update planning files based on catchup + git diff
4. Then proceed with task

## Important: Where Files Go

- **Templates** are in `~/.codex/skills/planning-with-files/templates/`
- **Your planning files** go in a dedicated plan directory under your project: `.planning/<YYYY-MM-DD>-<slug>/`

| Location | What Goes There |
|----------|-----------------|
| Skill directory (`~/.codex/skills/planning-with-files/`) | Templates, scripts, reference docs |
| `<project>/.planning/<id>/` | `task_plan.md`, `findings.md`, `progress.md` for this session's plan |

## Quick Start

Before ANY complex task:

1. **Create the plan directory** — Run `~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"` from the project root. This creates `.planning/<id>/{task_plan.md,findings.md,progress.md}`, prints `PLAN_ID=<id>`, updates `.planning/.active_plan`, and atomically binds the current Codex session when `CODEX_THREAD_ID` or `PWF_SESSION_ID` is available.
2. **Use the printed `PLAN_ID`** — Work only inside `.planning/<PLAN_ID>/` immediately after creation. Do NOT run `resolve-plan-dir.sh` yourself; plain shell has no hook-injected `PLAN_ID` and can fall back to the wrong `.active_plan`. On later turns, use the hook-injected canonical paths.
3. **Re-read plan before decisions** — Refreshes goals in attention window.
4. **Update after each phase** — Mark complete, log errors.

> **Note:** Planning files live in `.planning/<id>/`, not the project root and not the skill installation folder. Do not create a root-level `task_plan.md`.

## Script-First Task Creation Contract

New planning tasks MUST be created through the bundled initialization script:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh --plan-dir "Task Title"
```

Do not manually create `.planning/<plan-id>/`, `task_plan.md`, `findings.md`, or `progress.md` for a new task. The script is the canonical creation boundary: it creates the files, records `.planning/.active_plan`, writes `.planning/sessions/<session-id>.active_plan` when a stable Codex session id is available, and leaves `PostToolUse` as a safety net.

New Codex sessions do not treat the project `.planning/.active_plan` as current context. A session receives planning context only after it has a session binding created by the script above, or when an existing `.planning/sessions/<session-id>.active_plan` already exists for that session.

The stable session id is resolved from `PWF_SESSION_ID`, `CODEX_THREAD_ID`, transcript UUID, or other stable conversation/session fields. `turn_id` is ignored by default because Codex can create multiple turn ids inside one conversation.

When continuing an existing task, use the canonical file paths injected by the hooks. Do not manually run `resolve-plan-dir.sh` in a normal Bash command as a session resolver; without hook-injected `PLAN_ID`, it can read the project default instead of this session's plan.

## The Core Pattern

```
Context Window = RAM (volatile, limited)
Filesystem = Disk (persistent, unlimited)

→ Anything important gets written to disk.
```

## File Purposes

| File | Purpose | When to Update |
|------|---------|----------------|
| `task_plan.md` | Phases, progress, decisions | After each phase |
| `findings.md` | Research, discoveries | After ANY discovery |
| `progress.md` | Session log, test results | Throughout session |

## Critical Rules

### 1. Create Plan First
Never start a complex task without a plan. Create it as `.planning/<id>/task_plan.md` via `init-session.sh --plan-dir`, not as a root-level file. Non-negotiable.

### 2. The 2-Action Rule
> "After every 2 view/browser/search operations, IMMEDIATELY save key findings to text files."

This prevents visual/multimodal information from being lost.

### 3. Read Before Decide
Before major decisions, read the plan file. This keeps goals in your attention window.

### 4. Update After Act
After completing any phase:
- Mark phase status: `in_progress` → `complete`
- Log any errors encountered
- Note files created/modified

### 5. Log ALL Errors
Every error goes in the plan file. This builds knowledge and prevents repetition.

```markdown
## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| FileNotFoundError | 1 | Created default config |
| API timeout | 2 | Added retry logic |
```

### 6. Never Repeat Failures
```
if action_failed:
    next_action != same_action
```
Track what you tried. Mutate the approach.

## The 3-Strike Error Protocol

```
ATTEMPT 1: Diagnose & Fix
  → Read error carefully
  → Identify root cause
  → Apply targeted fix

ATTEMPT 2: Alternative Approach
  → Same error? Try different method
  → Different tool? Different library?
  → NEVER repeat exact same failing action

ATTEMPT 3: Broader Rethink
  → Question assumptions
  → Search for solutions
  → Consider updating the plan

AFTER 3 FAILURES: Escalate to User
  → Explain what you tried
  → Share the specific error
  → Ask for guidance
```

## Read vs Write Decision Matrix

| Situation | Action | Reason |
|-----------|--------|--------|
| Just wrote a file | DON'T read | Content still in context |
| Viewed image/PDF | Write findings NOW | Multimodal → text before lost |
| Browser returned data | Write to file | Screenshots don't persist |
| Starting new phase | Read plan/findings | Re-orient if context stale |
| Error occurred | Read relevant file | Need current state to fix |
| Resuming after gap | Read all planning files | Recover state |

## The 5-Question Reboot Test

If you can answer these, your context management is solid:

| Question | Answer Source |
|----------|---------------|
| Where am I? | Current phase in task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Goal statement in plan |
| What have I learned? | findings.md |
| What have I done? | progress.md |

## When to Use This Pattern

**Use for:**
- Multi-step tasks (3+ steps)
- Research tasks
- Building/creating projects
- Tasks spanning many tool calls
- Anything requiring organization

**Skip for:**
- Simple questions
- Single-file edits
- Quick lookups

## Templates

Copy these templates to start:

- [templates/task_plan.md](templates/task_plan.md) — Phase tracking
- [templates/findings.md](templates/findings.md) — Research storage
- [templates/progress.md](templates/progress.md) — Session logging

## Scripts

Helper scripts for automation:

- `scripts/init-session.sh` — Initialize all planning files
- `scripts/resolve-plan-dir.sh` — Resolve a plan directory for hook/internal use. Checks `$PLAN_ID` first, then `.planning/.active_plan`, then newest plan dir, then legacy root mode. Do not use it manually as a session resolver unless you explicitly provide the correct `PLAN_ID`.
- `scripts/check-complete.sh` — Verify all phases complete
- `scripts/session-catchup.py` — Recover context from previous session (v2.2.0)

## Codex Local Customizations

- **Project-level hooks** — Runtime hooks are registered through project `.codex/hooks.json`, not this `SKILL.md` frontmatter.
- **Per-session plan binding** — Each Codex session can bind to its own `.planning/sessions/<session-id>.active_plan`. Hook context reads that session plan and injects canonical plan file paths.
- **Atomic init-session binding** — `init-session.sh --plan-dir` writes the session plan immediately when `CODEX_THREAD_ID` or `PWF_SESSION_ID` is present; `PostToolUse` only validates or backfills binding.
- **Canonical path injection** — When hooks inject a plan, read and update only the listed `task_plan`, `findings`, and `progress` files. Do not read or edit `.planning/.active_plan`, root-level `./task_plan.md`, or another `.planning/<dir>/`.
- **Resolver boundary** — `resolve-plan-dir.sh` is session-aware only inside hooks because the Python adapter injects `PLAN_ID`. In ordinary Bash, do not run it without an explicit `PLAN_ID`.
- **PreToolUse guard** — Bare `resolve-plan-dir.sh` calls are blocked while planning hooks are active. Use hook-injected paths or explicitly set `PLAN_ID`.
- **Temporary-task suppression** — If your prompt contains `临时任务`, planning hooks stay silent for that turn and clear on `Stop`.
- **Gating** — `.planning/.hooks_mode` (`on`, `off`, `session`) or `PWF_HOOKS` controls whether planning hooks fire. Default project registration writes `on`.
- **Debug mode** — `.planning/.hooks_debug=on` or `PWF_HOOK_DEBUG=1` makes each planning hook write `.planning/debug/hook-events.jsonl` and emit a short `[planning-with-files debug]` line when possible. Use `planning-hooks-debug.py` to toggle it.

## Advanced Topics

- **Manus Principles:** See [references/reference.md](references/reference.md)
- **Real Examples:** See [references/examples.md](references/examples.md)

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Use TodoWrite for persistence | Create task_plan.md file |
| State goals once and forget | Re-read plan before decisions |
| Hide errors and retry silently | Log errors to plan file |
| Stuff everything in context | Store large content in files |
| Start executing immediately | Create plan file FIRST |
| Repeat failed actions | Track attempts, mutate approach |
| Create files in skill directory | Create files in your project |
| Create root-level `task_plan.md` for a new task | Run `scripts/init-session.sh --plan-dir "Task Title"` |
| Manually create a new `.planning/<plan-id>/` task | Run `scripts/init-session.sh --plan-dir "Task Title"` |
| Read `.planning/.active_plan` as the current task | Use the hook-injected canonical files for this session |
| Run `resolve-plan-dir.sh` manually to find this session's task | Use hook-injected canonical files, or use the `PLAN_ID` printed by `init-session.sh --plan-dir` |
| Read another `.planning/<dir>/` because it looks recent | Stay inside the canonical plan dir listed by the hook |
