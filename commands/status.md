---
description: "Show this session's planning status at a glance - bound plan, phases, progress, and any logged errors."
allowed-tools: "Read Bash"
---

Show a compact status summary of the plan bound to THIS session.

1. Run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" show`.
   - Exit code 1 (no plan bound): print the "No plan bound" block below and stop. Do NOT fall back to `.planning/.active_plan`, another plan directory, or a root-level `task_plan.md` in a project that has `.planning/`.
2. Read the `task_plan` path it printed and summarise it.

## What to Show

1. **Plan**: plan id and title
2. **Current Phase**: from "## Current Phase" (or "## 当前阶段")
3. **Phase Progress**: count phases and their status (pending/in_progress/complete)
4. **Phase List**: each phase with a status icon
5. **Errors**: number of rows in "## Errors Encountered" if present

## Status Icons

- `[ ]` or "pending" → ⏸️
- "in_progress" → 🔄
- `[x]` or "complete" → ✅
- "failed" or "blocked" → ❌

## Output Format

```
📋 Planning Status — <plan id>

Current: Phase {N} of {total} ({percent}%)
Status: {status_icon} {status_text}

  {icon} Phase 1: {name}
  {icon} Phase 2: {name} ← you are here
  ...

Errors logged: {count}
```

## If No Plan Is Bound

```
📋 No plan bound to this session

Start one with /plan, or continue an existing plan with /plan-attach.
```

Keep it brief: just enough to answer "where am I?".
