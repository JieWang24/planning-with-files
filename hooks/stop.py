#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.is_temporarily_disabled(root, session_id):
        adapter.clear_temporary_disable(root, session_id)
        return

    if not adapter.is_session_attached(root, session_id):
        return

    if not adapter.ensure_session_plan(root, session_id):
        return

    stdout, _ = adapter.run_shell_script("stop.sh", root, session_id)
    result = adapter.parse_json(stdout)

    message = result.get("followup_message")
    if not isinstance(message, str) or not message:
        return

    if "ALL PHASES COMPLETE" in message:
        adapter.emit_json({"systemMessage": message})
        return

    if bool(payload.get("stop_hook_active")):
        adapter.emit_json({"systemMessage": message})
        return

    adapter.emit_json({"decision": "block", "reason": message})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
