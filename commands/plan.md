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

   This creates `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}` from the templates and auto-binds the current session to it.
3. Resolve the directory and work ONLY inside it:

   ```bash
   PLAN_DIR="$(sh "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-plan-dir.sh")"
   ```

   Read and update `$PLAN_DIR/task_plan.md`, `$PLAN_DIR/findings.md`, `$PLAN_DIR/progress.md`.

Do NOT create or edit a root-level `task_plan.md`, and do NOT read `.planning/.active_plan` or other plan directories — they belong to other sessions.

Then guide the user through the planning workflow.
