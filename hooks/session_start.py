#!/usr/bin/env python3
"""SessionStart (startup | resume | clear | compact | fork).

* Exports PWF_SESSION_ID for later Bash commands via CLAUDE_ENV_FILE.
* Bound session: inject the plan (compact source adds a re-read note).
* resume/fork with a new session id: inherit the binding from the earlier
  session ids recorded in the transcript.
* clear: take over the plan the pre-/clear session was bound to, plus a
  plan-scoped catchup of what that session did.
* Unbound session in a project with plans: a short hint, never plan content.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)
    source = str(payload.get("source") or "startup")

    adapter.export_session_env(sid)
    if source == "startup":
        adapter.gc_state()

    if not adapter.hooks_enabled(cwd, sid):
        adapter.emit("SessionStart", debug_line=adapter.hook_debug_line(cwd, sid, "SessionStart", f"{source}: hooks off"))
        return

    notes: list[str] = []
    extra = ""
    plan = adapter.locate_bound_plan(cwd, sid)

    if plan is None and source in ("resume", "fork"):
        inherited = adapter.inherit_from_lineage(cwd, sid, payload)
        if inherited:
            plan, old_sid = inherited
            notes.append(f"Plan binding inherited from earlier session {old_sid[:8]} ({source}).")
        else:
            adapter.update_state(sid, pending_lineage=True)

    if plan is None and source == "clear":
        handed = adapter.consume_clear_handoff(cwd, sid)
        if handed:
            plan, old_sid = handed
            notes.append(
                f"Plan binding carried over from the session before /clear ({old_sid[:8]}). "
                "If the user is starting an unrelated task, create a new plan instead."
            )
            extra = adapter.run_catchup(plan, sid)
        else:
            # SessionEnd of the cleared session may not have run yet.
            adapter.update_state(sid, pending_clear=True)

    if plan is None:
        plan = adapter.legacy_plan(cwd)

    if plan is not None:
        if source == "compact":
            notes.append(
                "Context was just compacted: re-read the canonical plan files below before continuing, "
                "and make sure progress.md reflects the latest work."
            )
        text = adapter.render_full(plan, notes)
        if extra:
            text = f"{text}\n{extra}"
        adapter.remember_injection(plan, sid)
        debug_line = adapter.hook_debug_line(cwd, sid, "SessionStart", f"{source}: injected plan", plan)
        adapter.emit("SessionStart", context=text, debug_line=debug_line)
        return

    hint = "" if source == "compact" else adapter.unbound_hint(cwd)
    debug_line = adapter.hook_debug_line(cwd, sid, "SessionStart", f"{source}: unbound")
    adapter.emit("SessionStart", context=hint, debug_line=debug_line)


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
