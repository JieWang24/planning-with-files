#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        return

    if adapter.is_plan_creation_command(payload):
        before_id = adapter.session_active_plan_id(root, session_id)
        plan_id = adapter.rebind_session_if_project_active_changed(root, session_id)
        if not plan_id:
            active_id = adapter.project_active_plan_id(root)
            if active_id and not session_id:
                adapter.emit_json(
                    {
                        "systemMessage": (
                            "[planning-with-files] Plan created, but no stable Codex session id was available; "
                            "session plan binding was skipped."
                        )
                    }
                )
            return
        if plan_id != before_id:
            adapter.emit_json({"systemMessage": f"[planning-with-files] Session plan bound to: {plan_id}"})
        return

    if not adapter.ensure_session_plan(root, session_id):
        return

    stdout, _ = adapter.run_shell_script("post-tool-use.sh", root, session_id)
    if stdout:
        adapter.emit_json({"systemMessage": stdout})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
