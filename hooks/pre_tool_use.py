#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        return

    if not adapter.effective_plan_present(root, session_id):
        return

    # Light reminder before a Bash command that may change project state.
    stdout, _ = adapter.run_shell_script("pre-tool-use.sh", root, session_id)
    if stdout:
        adapter.emit_context("PreToolUse", stdout)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
