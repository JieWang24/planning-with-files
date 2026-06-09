#!/usr/bin/env python3
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.cwd_from_payload(payload)
    session_id = adapter.session_id_from_payload(payload)

    if not adapter.is_session_attached(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "PreToolUse", "not attached; no action"))
        return

    # Hard guard: block a bare `resolve-plan-dir.sh` run (no PLAN_ID). In a plain
    # shell the resolver isn't session-aware and falls back to .active_plan — the
    # wrong plan when several exist. The agent should use the hook-injected
    # canonical paths or the PLAN_ID printed by init-session instead.
    if adapter.is_bare_resolver_command(payload):
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "[planning-with-files] Refusing a bare resolve-plan-dir.sh run: "
                    "without PLAN_ID it falls back to .planning/.active_plan (the wrong "
                    "plan when several exist). Use the canonical plan paths the hooks "
                    "inject, or the PLAN_ID printed by init-session, or pass an explicit "
                    "PLAN_ID=<id> (override with PWF_ALLOW_BARE_RESOLVE=1)."
                ),
            }
        }
        dbg = adapter.hook_debug_line(root, session_id, "PreToolUse", "blocking bare resolve-plan-dir.sh")
        if dbg:
            out["systemMessage"] = dbg
        adapter.emit_json(out)
        return

    if not adapter.effective_plan_present(root, session_id):
        adapter.emit_debug(adapter.hook_debug_line(root, session_id, "PreToolUse", "no plan resolved; no reminder"))
        return

    # Light reminder before a Bash command that may change project state.
    stdout, _ = adapter.run_shell_script("pre-tool-use.sh", root, session_id)
    dbg = adapter.hook_debug_line(root, session_id, "PreToolUse", "pre-bash reminder")
    if stdout:
        adapter.emit_context("PreToolUse", stdout, dbg)
    else:
        adapter.emit_debug(dbg)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
