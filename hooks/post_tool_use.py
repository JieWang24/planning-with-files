#!/usr/bin/env python3
"""PostToolUse (Bash | Write | Edit | MultiEdit | NotebookEdit).

* After init-session.sh / session-plan.sh: bind (or unbind) THIS session from
  the script's own `PLAN_ID=` / `PWF_DETACHED=` output. Falls back to an
  .active_plan before/after comparison. Commands that merely mention the
  scripts (cat, grep, ...) print no such line and never bind.
* Otherwise, for a bound session: count edits / shell commands since the plan
  files were last touched and nudge once when the window gets large.
"""
from __future__ import annotations

from pathlib import Path

import planning_hook_adapter as adapter


def handle_plan_command(payload: dict, cwd: Path, sid: str | None) -> bool:
    command = adapter.bash_command(payload)
    if not command or not adapter.invokes_plan_script(command):
        return False
    stdout = adapter.bash_stdout(payload)
    before = adapter.load_state(sid).get("active_plan_before")
    adapter.update_state(sid, active_plan_before=None)

    roots = adapter.PLAN_ROOT_LINE_RE.findall(stdout)
    root = Path(roots[-1]).parent if roots else cwd

    detached = adapter.DETACHED_LINE_RE.findall(stdout)
    if detached:
        adapter.unbind_session(root, sid)
        adapter.emit("PostToolUse", system_message="[planning-with-files] Session plan detached.",
                     debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "detached"))
        return True

    ids = adapter.PLAN_ID_LINE_RE.findall(stdout)
    plan_id = ids[-1] if ids else ""
    if not plan_id and before is not None:
        current = adapter.project_active_plan_id(cwd)
        plan_id = current if current and current != before else ""
        root = cwd
    plan = adapter.plan_for(root, plan_id) if plan_id else None
    if plan is None:
        adapter.emit("PostToolUse", debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "plan script ran; nothing to bind"))
        return True

    previous = adapter.bound_plan_at(plan.root, sid)
    if previous and previous.plan_id == plan.plan_id:
        adapter.emit("PostToolUse", debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "binding already current", plan))
        return True
    if not adapter.bind_session(plan.root, sid, plan.plan_id):
        return True
    adapter.update_state(sid, activity=None)
    context = "\n".join(
        [f"[planning-with-files] This session is now bound to plan {plan.plan_id}."] + adapter.canonical_lines(plan)
    )
    adapter.remember_injection(plan, sid)
    adapter.emit(
        "PostToolUse",
        context=context,
        system_message=f"[planning-with-files] Session plan bound to: {plan.plan_id}",
        debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "bound", plan),
    )
    return True


def main() -> None:
    payload = adapter.load_payload()
    cwd = adapter.cwd_from_payload(payload)
    sid = adapter.session_id_from_payload(payload)

    if not adapter.hooks_enabled(cwd, sid):
        return
    if handle_plan_command(payload, cwd, sid):
        return

    plan = adapter.session_plan(cwd, sid)
    if plan is None:
        inherited = adapter.retry_pending_lineage(cwd, sid, payload)
        if inherited:
            plan, old_sid = inherited
            adapter.remember_injection(plan, sid)
            adapter.emit("PostToolUse",
                         context=adapter.render_full(plan, [f"Plan binding inherited from earlier session {old_sid[:8]} (resume/fork)."]),
                         debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "late lineage inheritance", plan))
        return
    reminder = adapter.record_activity(plan, sid, payload)
    if reminder:
        adapter.emit("PostToolUse", context=reminder, debug_line=adapter.hook_debug_line(cwd, sid, "PostToolUse", "progress nudge", plan))


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
