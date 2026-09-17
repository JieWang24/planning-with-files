#!/usr/bin/env python3
"""UserPromptSubmit.

* `临时任务` in the prompt silences every planning hook for this session until
  the next normal prompt (or Stop).
* Bound session: inject the plan; if nothing changed since the last injection,
  inject a two-line pointer instead of repeating the whole plan.
* Unbound session: silent (retries resume lineage inheritance once).
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    if adapter.has_temporary_task_keyword(payload):
        adapter.set_temporary_disable(sid)
        adapter.emit("UserPromptSubmit", debug_line=adapter.hook_debug_line(cwd, sid, "UserPromptSubmit", "临时任务: suppressed"))
        return
    adapter.clear_temporary_disable(sid)

    if not adapter.hooks_enabled(cwd, sid):
        adapter.emit("UserPromptSubmit", debug_line=adapter.hook_debug_line(cwd, sid, "UserPromptSubmit", "hooks off"))
        return

    plan = adapter.locate_bound_plan(cwd, sid)
    notes: list[str] = []
    extra = ""
    state = adapter.load_state(sid) if plan is None else {}
    if plan is None and state.get("pending_lineage"):
        inherited = adapter.retry_pending_lineage(cwd, sid, payload)
        if inherited:
            plan, old_sid = inherited
            notes.append(f"Plan binding inherited from earlier session {old_sid[:8]} (resume).")
    if plan is None and state.get("pending_clear"):
        adapter.update_state(sid, pending_clear=None)
        handed = adapter.consume_clear_handoff(cwd, sid)
        if handed:
            plan, old_sid = handed
            notes.append(
                f"Plan binding carried over from the session before /clear ({old_sid[:8]}). "
                "If the user is starting an unrelated task, create a new plan instead."
            )
            extra = adapter.run_catchup(plan, sid)
    if plan is None:
        plan = adapter.legacy_plan(cwd)
    if plan is None:
        adapter.emit("UserPromptSubmit", debug_line=adapter.hook_debug_line(cwd, sid, "UserPromptSubmit", "unbound: silent"))
        return

    if not notes and adapter.already_injected(plan, sid):
        text = adapter.render_compact(plan)
        note = "plan unchanged: pointer"
    else:
        text = adapter.render_full(plan, notes)
        if extra:
            text = f"{text}\n{extra}"
        adapter.remember_injection(plan, sid)
        note = "injected plan"
    adapter.emit("UserPromptSubmit", context=text, debug_line=adapter.hook_debug_line(cwd, sid, "UserPromptSubmit", note, plan))


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
