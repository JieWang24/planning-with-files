#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "PreToolUse", "not attached; no action")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    if adapter.is_bare_resolver_command(payload):
        debug_line = adapter.hook_debug_line(root, session_id, "PreToolUse", "blocking bare resolver")
        adapter.emit_json(
            {
                "decision": "block",
                "reason": adapter.with_debug_prefix(
                    debug_line,
                    (
                        "[planning-with-files] Refusing bare resolve-plan-dir call. "
                        "Use the session-bound plan paths injected by hooks, or set PLAN_ID explicitly."
                    ),
                ),
            }
        )
        return

    if not adapter.is_plan_creation_command(payload):
        debug_line = adapter.hook_debug_line(root, session_id, "PreToolUse", "ordinary bash; allowed")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    adapter.record_project_active_before_tool(root, session_id)
    debug_line = adapter.hook_debug_line(root, session_id, "PreToolUse", "recorded active plan before init-session")
    if debug_line:
        adapter.emit_json({"systemMessage": debug_line})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
