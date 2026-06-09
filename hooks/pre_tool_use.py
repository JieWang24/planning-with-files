#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        return

    if adapter.is_bare_resolver_command(payload):
        adapter.emit_json(
            {
                "decision": "block",
                "reason": (
                    "[planning-with-files] Refusing bare resolve-plan-dir call. "
                    "Use the session-bound plan paths injected by hooks, or set PLAN_ID explicitly."
                ),
            }
        )
        return

    if not adapter.is_plan_creation_command(payload):
        return

    adapter.record_project_active_before_tool(root, session_id)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
