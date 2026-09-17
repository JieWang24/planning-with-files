#!/usr/bin/env python3
"""Stop.

Bound sessions only. Feedback uses `hookSpecificOutput.additionalContext`
(non-error "Stop hook feedback"), respecting `stop_hook_active`.

Modes (`PWF_STOP_MODE` env or `.planning/.stop_mode`):
* sync (default) — if this turn edited files / ran a batch of commands but the
  plan files were not touched since, ask once for a progress entry.
* continue — legacy: while phases are incomplete (and nothing runs in the
  background), ask Claude to keep working on the remaining phases.
* off — no Stop behaviour.
A short user-visible status line is shown when the phase count changes.
"""
from __future__ import annotations

import planning_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    if adapter.is_temporarily_disabled(sid):
        adapter.clear_temporary_disable(sid)
        adapter.update_state(sid, activity=None)
        return
    if not adapter.hooks_enabled(cwd, sid):
        return
    plan = adapter.session_plan(cwd, sid)
    if plan is None:
        # Bind a resumed/forked session once its transcript is written; the
        # plan is injected with the next prompt.
        adapter.retry_pending_lineage(cwd, sid, payload)
        return
    mode = adapter.stop_mode(plan.root)
    if mode == "off":
        return

    state = adapter.load_state(sid)
    complete, total = adapter.phase_counts(plan.task_plan)
    status = f"{plan.label}:{complete}/{total}"
    status_message = ""
    previous = state.get("last_status")
    if total and previous and previous != status and previous.split(":")[0] == plan.label:
        if complete == total:
            status_message = f"[planning-with-files] {plan.label}: ALL PHASES COMPLETE ({complete}/{total})."
        else:
            status_message = f"[planning-with-files] {plan.label}: {complete}/{total} phases complete."
    state["last_status"] = status

    feedback = ""
    stop_active = bool(payload.get("stop_hook_active"))
    activity = state.get("activity") if isinstance(state.get("activity"), dict) else {}
    if activity.get("plan") != plan.label:
        activity = {}

    if mode == "sync" and activity:
        since = float(activity.get("since") or 0)
        busy = int(activity.get("edits") or 0) >= adapter.STOP_EDITS or int(activity.get("bash") or 0) >= adapter.STOP_BASH
        if busy and not adapter.plan_updated_since(plan, since) and not stop_active:
            feedback = (
                f"[planning-with-files] Before finishing: this turn made {activity.get('edits', 0)} file edit(s) and "
                f"{activity.get('bash', 0)} shell command(s) for plan {plan.label}, but {plan.progress} was not updated. "
                f"Append a short progress entry there (and update the phase status in {plan.task_plan} if a phase "
                "changed), then finish. Do not start new work."
            )
        else:
            state.pop("activity", None)
    elif mode == "continue" and total and complete < total and not stop_active and not payload.get("background_tasks"):
        feedback = (
            f"[planning-with-files] Plan {plan.label} is incomplete ({complete}/{total} phases complete). Update "
            f"{plan.progress}, then continue with the remaining phases in {plan.task_plan}."
        )

    adapter.save_state(sid, state)
    note = "feedback" if feedback else ("status" if status_message else "quiet")
    adapter.emit("Stop", context=feedback, system_message=status_message,
                 debug_line=adapter.hook_debug_line(cwd, sid, "Stop", f"{mode}: {note}", plan))


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
