#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.is_temporarily_disabled(root, session_id):
        adapter.clear_temporary_disable(root, session_id)
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "Stop", "temporary-task cleared; no completion check"))
        return

    if not adapter.is_session_attached(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "Stop", "not attached; no completion check"))
        return

    if not adapter.effective_plan_present(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "Stop", "no plan resolved; allowing stop"))
        return

    stdout, _ = adapter.run_shell_script("stop.sh", root, session_id)
    result = adapter.parse_json(stdout)

    message = result.get("followup_message")
    if not isinstance(message, str) or not message:
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "Stop", "no followup message"))
        return

    if "ALL PHASES COMPLETE" in message:
        dbg = adapter.hook_debug_line(root, session_id, "Stop", "all phases complete; allowing stop")
        adapter.emit_json({"systemMessage": adapter.with_debug_prefix(dbg, message)})
        return

    if bool(payload.get("stop_hook_active")):
        dbg = adapter.hook_debug_line(root, session_id, "Stop", "stop_hook_active; not re-blocking")
        adapter.emit_json({"systemMessage": adapter.with_debug_prefix(dbg, message)})
        return

    dbg = adapter.hook_debug_line(root, session_id, "Stop", "blocking stop; phases incomplete")
    adapter.emit_json({"decision": "block", "reason": adapter.with_debug_prefix(dbg, message)})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
