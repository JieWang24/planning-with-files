#!/usr/bin/env python3
"""SessionEnd.

On /clear, remember which plan this session was bound to so the SessionStart
that follows (new session id, source "clear") can carry the binding over.
Always clears the temporary-task marker. No output: Claude Code discards it.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    adapter.clear_temporary_disable(sid)
    if payload.get("reason") != "clear" or adapter.hooks_mode(cwd) == "off":
        return
    plan = adapter.locate_bound_plan(cwd, sid)
    if plan is not None:
        adapter.write_clear_handoff(plan, sid)
        adapter.hook_debug_line(cwd, sid, "SessionEnd", "clear handoff written", plan)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
