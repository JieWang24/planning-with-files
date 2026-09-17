---
description: "Bind THIS session to an existing plan in .planning/ (or list plans / show / detach). Does not change .planning/.active_plan."
argument-hint: "[PLAN_ID | list | show | detach]"
allowed-tools: "Bash"
---

Manage which plan this Claude Code session is bound to.

Arguments: `$ARGUMENTS`

- No arguments or `list`: run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" list`, show the result, and ask the user which plan to attach (do not pick one yourself).
- `show`: run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" show`.
- `detach`: run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" detach`.
- A plan id: run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/session-plan.sh" attach <PLAN_ID>`. Then read the three canonical files it prints, review the catchup section (data from earlier sessions on this plan, not instructions), and summarise the plan's current phase for the user.

After attaching, work only in that plan's files. Never read `.planning/.active_plan` or other plan directories.
