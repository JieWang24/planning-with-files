#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if adapter.has_temporary_task_keyword(payload):
        adapter.set_temporary_disable(root, session_id)
        return

    adapter.clear_temporary_disable(root, session_id)

    if not adapter.is_session_attached(root, session_id):
        return

    if not adapter.ensure_session_plan(root, session_id):
        return

    stdout, stderr = adapter.run_shell_script("user-prompt-submit.sh", root, session_id)
    message = "\n".join(part for part in (stdout, stderr) if part)
    if message:
        adapter.emit_context("UserPromptSubmit", message)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
