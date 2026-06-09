#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.has_temporary_task_keyword(payload):
        adapter.set_temporary_disable(root, session_id)
        debug_line = adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "temporary task keyword; planning suppressed")
        if debug_line:
            adapter.emit_user_prompt_context(debug_line)
        return

    adapter.clear_temporary_disable(root, session_id)

    if not adapter.is_session_attached(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "not attached; no context")
        if debug_line:
            adapter.emit_user_prompt_context(debug_line)
        return

    if not adapter.ensure_session_plan(root, session_id):
        debug_line = adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "no session plan; no context")
        if debug_line:
            adapter.emit_user_prompt_context(debug_line)
        return

    stdout, stderr = adapter.run_shell_script("user-prompt-submit.sh", root, session_id)
    message = "\n".join(part for part in (stdout, stderr) if part)
    debug_line = adapter.hook_debug_line(root, session_id, "UserPromptSubmit", "rendered session context")
    if message:
        adapter.emit_user_prompt_context(adapter.with_debug_prefix(debug_line, message))
    elif debug_line:
        adapter.emit_user_prompt_context(debug_line)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
