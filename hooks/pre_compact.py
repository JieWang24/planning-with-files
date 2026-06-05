#!/usr/bin/env python3
"""PreCompact adapter for planning-with-files (Claude Code).

Fires before context compaction (/compact or auto-compact). Reminds the agent
to flush in-context progress to progress.md before compaction completes, and
notes that the planning files remain on disk and will be re-read afterwards.
Never blocks compaction; always exits cleanly.
"""
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

    stdout, _ = adapter.run_shell_script("pre-compact.sh", root, session_id)
    if stdout:
        adapter.emit_context("PreCompact", stdout)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
