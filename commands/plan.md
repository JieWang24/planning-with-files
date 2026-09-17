---
description: "Start Manus-style file-based planning. Creates an isolated plan under .planning/<id>/ and binds THIS session to it."
---

Invoke the planning-with-files:planning-with-files skill and follow it exactly as presented to you.

Every Claude Code session works on exactly one plan — the one bound to it. The project's `.planning/.active_plan` is only "the plan some session created last" and is never this session's plan.

1. If the user wants to continue an existing plan instead of starting a new one, bind it and stop here:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" list
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" attach <PLAN_ID>
   ```

2. Otherwise create a new plan (pick a short, descriptive task name):

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/init-session.sh" --plan-dir "<task name>"
   ```

   This creates `.planning/<YYYY-MM-DD>-<slug>/{task_plan.md,findings.md,progress.md}`, binds this session to it, and prints `PLAN_ID=<id>` plus the canonical file paths.
3. Work ONLY inside that plan — read and update the three canonical files it printed. On later turns the hooks inject the same paths.

Do NOT create or edit a root-level `task_plan.md`, and do NOT read `.planning/.active_plan` or other plan directories — they belong to other sessions. Do NOT run `resolve-plan-dir.sh` yourself; use `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" path` if a script needs this session's plan dir.

Then guide the user through the planning workflow.
