#!/usr/bin/env python3
"""PermissionRequest adapter for planning-with-files (Claude Code port).

Fires when Claude Code asks the user to permit a tool call. We surface a short
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
        return

    plan_id = adapter.ensure_session_plan(root, session_id)
    if not plan_id:
        return

    plan = root / ".planning" / plan_id / "task_plan.md"
    if not plan.exists():
        return

    adapter.emit_json({
        "systemMessage": (
            "[planning-with-files] Active plan detected. Review the current phase "
            "in task_plan.md before approving the tool request."
        )
    })


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
