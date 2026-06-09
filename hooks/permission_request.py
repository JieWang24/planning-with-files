#!/usr/bin/env python3
"""Codex PermissionRequest adapter for planning-with-files (v2.38.0).

Fires when Codex asks the user to permit a tool call. We surface a short
reminder that an active plan exists so the user reviews task_plan.md before
approving. Read-only; never blocks the request; always exits cleanly.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "PermissionRequest", "not attached; no reminder")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    plan_id = adapter.ensure_session_plan(root, session_id)
    if not plan_id:
        debug_line = adapter.hook_debug_line(root, session_id, "PermissionRequest", "no session plan; no reminder")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    plan = root / ".planning" / plan_id / "task_plan.md"
    if not plan.exists():
        debug_line = adapter.hook_debug_line(root, session_id, "PermissionRequest", "session plan missing task_plan.md")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    debug_line = adapter.hook_debug_line(root, session_id, "PermissionRequest", "approval reminder")
    adapter.emit_json({
        "systemMessage": adapter.with_debug_prefix(
            debug_line,
            (
                "[planning-with-files] Active plan detected. Review the current phase "
                "in task_plan.md before approving the tool request."
            ),
        )
    })


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
