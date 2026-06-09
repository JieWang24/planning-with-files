#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", "not attached; no action")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    if adapter.is_plan_creation_command(payload):
        before_id = adapter.session_active_plan_id(root, session_id)
        plan_id = adapter.rebind_session_if_project_active_changed(root, session_id)
        if not plan_id:
            active_id = adapter.project_active_plan_id(root)
            debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", "init-session seen but no session plan bound")
            if active_id and not session_id:
                adapter.emit_json(
                    {
                        "systemMessage": adapter.with_debug_prefix(
                            debug_line,
                            (
                                "[planning-with-files] Plan created, but no stable Codex session id was available; "
                                "session plan binding was skipped."
                            ),
                        )
                    }
                )
            elif debug_line:
                adapter.emit_json({"systemMessage": debug_line})
            return
        if plan_id != before_id:
            debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", f"session plan rebound to {plan_id}")
            adapter.emit_json(
                {
                    "systemMessage": adapter.with_debug_prefix(
                        debug_line,
                        f"[planning-with-files] Session plan bound to: {plan_id}",
                    )
                }
            )
        else:
            debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", "init-session binding already current")
            if debug_line:
                adapter.emit_json({"systemMessage": debug_line})
        return

    if not adapter.ensure_session_plan(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", "no session plan; no reminder")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    stdout, _ = adapter.run_shell_script("post-tool-use.sh", root, session_id)
    debug_line = adapter.hook_debug_line(root, session_id, "PostToolUse", "ordinary bash reminder")
    if stdout:
        adapter.emit_json({"systemMessage": adapter.with_debug_prefix(debug_line, stdout)})
    elif debug_line:
        adapter.emit_json({"systemMessage": debug_line})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
