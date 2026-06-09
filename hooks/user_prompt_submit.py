#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.has_temporary_task_keyword(payload):
        adapter.set_temporary_disable(root, session_id)
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "temporary-task keyword; suppressed for this session"))
        return

    adapter.clear_temporary_disable(root, session_id)

    if not adapter.is_session_attached(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "not attached; no context"))
        return

    if not adapter.effective_plan_present(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "no plan resolved; no context"))
        return

    stdout, stderr = adapter.run_shell_script("user-prompt-submit.sh", root, session_id)
    message = "\n".join(part for part in (stdout, stderr) if part)
    dbg = adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "rendered session context")
    if message:
        adapter.emit_context("UserPromptSubmit", message, dbg)
    else:
        adapter.emit_debug(dbg)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
