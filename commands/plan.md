---
description: "Start Manus-style file-based planning. Creates an isolated per-session plan under .planning/<id>/ for complex tasks."
---

Invoke the planning-with-files:planning-with-files skill and follow it exactly as presented to you.

Create the plan as a DEDICATED plan directory so this session is isolated from other sessions/plans — do NOT create root-level planning files.

1. Pick a short slug for the task (e.g. "auth-refactor", "data-pipeline").
2. Create the plan directory and bind this session to it:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/init-session.sh" --plan-dir "<task name>"
   ```

   This creates `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}` from the templates, auto-binds the current session to it, and prints a `PLAN_ID=<id>` line. Note that id.
3. Work ONLY inside that plan — read and update `.planning/<PLAN_ID>/task_plan.md`, `.planning/<PLAN_ID>/findings.md`, `.planning/<PLAN_ID>/progress.md`.

Do NOT create or edit a root-level `task_plan.md`, and do NOT read `.planning/.active_plan` or other plan directories — they belong to other sessions. **Do NOT run `resolve-plan-dir.sh` yourself** — in a plain shell it has no `PLAN_ID` and falls back to `.active_plan` (the wrong plan when several exist). On later turns, use the canonical plan-file paths the planning hooks inject.

Then guide the user through the planning workflow.
