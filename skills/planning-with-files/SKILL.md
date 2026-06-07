---
name: planning-with-files
description: Implements Manus-style file-based planning to organize and track progress on complex tasks. Creates task_plan.md, findings.md, and progress.md. Use when asked to plan out, break down, or organize a multi-step project, research task, or any work requiring 5+ tool calls. Supports automatic session recovery after /clear.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "2.43.0-codex.1"

---

# Planning with Files

Work like Manus: Use persistent markdown files as your "working memory on disk."

## FIRST: Check for Previous Session (v2.2.0)

**Before starting work**, check for unsynced context from a previous session:

```bash
# Linux/macOS (auto-detects python3 or python)
$(command -v python3 || command -v python) ~/.codex/skills/planning-with-files/scripts/session-catchup.py "$(pwd)"
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
- **Your planning files** go in **your project directory**

| Location | What Goes There |
|----------|-----------------|
| Skill directory (`~/.codex/skills/planning-with-files/`) | Templates, scripts, reference docs |
| Your project directory | `.planning/<plan-id>/task_plan.md`, `.planning/<plan-id>/findings.md`, `.planning/<plan-id>/progress.md` |

## Quick Start

Before ANY complex task:

1. **Create the task with the script** — Run `~/.codex/skills/planning-with-files/scripts/init-session.sh "Task Title"` from the project root.
2. **Use the generated files** — Work in the created `.planning/<plan-id>/task_plan.md`, `findings.md`, and `progress.md`.
3. **Re-read plan before decisions** — Refreshes goals in attention window.
4. **Update after each phase** — Mark complete, log errors.

> **Note:** Planning files go in your project root, not the skill installation folder.

## Script-First Task Creation Contract

New planning tasks MUST be created through the bundled initialization script:

```bash
~/.codex/skills/planning-with-files/scripts/init-session.sh "Task Title"
```

Do not manually create `.planning/<plan-id>/`, `task_plan.md`, `findings.md`, or `progress.md` for a new task. The script is the canonical creation boundary: it creates the files, records `.planning/.active_plan`, and gives project hooks one precise moment to bind the current Codex session to the new plan.

New Codex sessions do not automatically bind themselves to the project `.planning/.active_plan`. A session receives planning context only after it has been explicitly bound by running the creation script above, or when an existing `.planning/sessions/<session-id>.active_plan` already exists for that session.

When continuing an existing task, read the current task through the session-aware resolver, not by reading `.planning/.active_plan` directly:

```bash
PLAN_DIR="$(sh ~/.codex/hooks/resolve-plan-dir.sh)"
```

Then read `$PLAN_DIR/task_plan.md`, `$PLAN_DIR/findings.md`, and `$PLAN_DIR/progress.md`.

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
Never start a complex task without `task_plan.md`. Non-negotiable.

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
- `scripts/check-complete.sh` — Verify all phases complete
- `scripts/session-catchup.py` — Recover context from previous session (v2.2.0)

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
| Manually create a new `.planning/<plan-id>/` task | Run `scripts/init-session.sh "Task Title"` |
| Read `.planning/.active_plan` as the current task | Resolve the session plan through `resolve-plan-dir.sh` |
