#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "PostToolUse", "not attached; no action"))
        return

    if adapter.is_plan_creation_command(payload):
        before_id = adapter.session_active_plan_id(root, session_id)
        plan_id = adapter.rebind_session_to_project_active(root, session_id)
        dbg = adapter.hook_debug_line(root, session_id, "PostToolUse", f"init-session seen; session plan = {plan_id or 'none'}")
        if plan_id and plan_id != before_id:
            adapter.emit_json({"systemMessage": adapter.with_debug_prefix(dbg, f"[planning-with-files] Session plan bound to: {plan_id}")})
        else:
            adapter.emit_debug(dbg)
        return

    if not adapter.effective_plan_present(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "PostToolUse", "no plan resolved; no reminder"))
        return

    stdout, _ = adapter.run_shell_script("post-tool-use.sh", root, session_id)
    dbg = adapter.hook_debug_line(root, session_id, "PostToolUse", "progress reminder")
    if stdout:
        adapter.emit_context("PostToolUse", stdout, dbg)
    else:
        adapter.emit_debug(dbg)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
