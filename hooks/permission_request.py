#!/usr/bin/env python3
"""PermissionRequest.

Read-only: when Claude Code is about to ask for permission in a bound main
session, show the user which plan (and phase) this session is working on.
Never makes a permission decision.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    if adapter.is_subagent(payload) or not adapter.hooks_enabled(cwd, sid):
        return
    plan = adapter.session_plan(cwd, sid)
    if plan is None:
        return
    phase = adapter.current_phase(plan.task_plan)
    message = f"[planning-with-files] Session plan: {adapter.plan_title(plan.task_plan)} ({plan.label})"
    if phase:
        message += f" — current phase: {phase}"
    adapter.emit("PermissionRequest", system_message=message,
                 debug_line=adapter.hook_debug_line(cwd, sid, "PermissionRequest", "plan reminder", plan))


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
