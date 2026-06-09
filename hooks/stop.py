#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.is_temporarily_disabled(root, session_id):
        adapter.clear_temporary_disable(root, session_id)
        debug_line = adapter.hook_debug_line(root, session_id, "Stop", "temporary marker cleared; stop suppressed")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    if not adapter.is_session_attached(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "Stop", "not attached; no completion check")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    if not adapter.ensure_session_plan(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "Stop", "no session plan; no completion check")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    stdout, _ = adapter.run_shell_script("stop.sh", root, session_id)
    result = adapter.parse_json(stdout)

    message = result.get("followup_message")
    if not isinstance(message, str) or not message:
        debug_line = adapter.hook_debug_line(root, session_id, "Stop", "stop renderer returned no followup")
        if debug_line:
            adapter.emit_json({"systemMessage": debug_line})
        return

    debug_note = "all phases complete" if "ALL PHASES COMPLETE" in message else "task incomplete"
    debug_line = adapter.hook_debug_line(root, session_id, "Stop", debug_note)
    message = adapter.with_debug_prefix(debug_line, message)

    if "ALL PHASES COMPLETE" in message:
        adapter.emit_json({"systemMessage": message})
        return

    if bool(payload.get("stop_hook_active")):
        adapter.emit_json({"systemMessage": message})
        return

    adapter.emit_json({"decision": "block", "reason": message})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
