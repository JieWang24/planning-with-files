#!/usr/bin/env python3
"""PreToolUse (Bash).

* Denies a bare resolve-plan-dir.sh run: outside the hooks it is not
  session-aware and falls back to the project-wide .active_plan.
* Before init-session.sh / session-plan.sh runs, snapshots .active_plan so
  PostToolUse can still bind if the script's PLAN_ID line is not visible.
No per-command reminder: plan context arrives with each prompt instead.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    if not adapter.hooks_enabled(cwd, sid):
        return

    if adapter.is_bare_resolver_command(payload):
        path_cmd = adapter.script_path("session-plan.sh")
        adapter.emit_json({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "[planning-with-files] Refusing a bare resolve-plan-dir.sh run: without PLAN_ID it falls back to "
                    ".planning/.active_plan, which belongs to whichever session created a plan last. Use the canonical "
                    f"paths injected by the hooks, or `sh \"{path_cmd}\" path` for this session's plan dir "
                    "(override with PLAN_ID=<id> or PWF_ALLOW_BARE_RESOLVE=1)."
                ),
            },
            **({"systemMessage": line} if (line := adapter.hook_debug_line(cwd, sid, "PreToolUse", "denied bare resolver")) else {}),
        })
        return

    if adapter.invokes_plan_script(adapter.bash_command(payload)):
        adapter.update_state(sid, active_plan_before=adapter.project_active_plan_id(cwd))


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
