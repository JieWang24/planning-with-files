#!/usr/bin/env python3
"""End-to-end smoke test for the Claude Code session model (2.44.0-claude).

Runs the real hook scripts and shell scripts against throwaway projects with a
throwaway HOME / plugin-data dir, so nothing on the machine is touched.

    python3 tools/smoke_test_session_model.py [--keep]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / "hooks"
SCRIPTS = REPO / "scripts"

S1 = "11111111-1111-4111-8111-111111111111"
S2 = "22222222-2222-4222-8222-222222222222"
S3 = "33333333-3333-4333-8333-333333333333"
S4 = "44444444-4444-4444-8444-444444444444"
S5 = "55555555-5555-4555-8555-555555555555"

FAILURES: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    print(("  ok   " if condition else "  FAIL ") + label)
    if not condition:
        FAILURES.append(label)
        if detail:
            print("       " + detail.replace("\n", "\n       ")[:1500])


class Env:
    def __init__(self, base: Path):
        self.base = base
        self.home = base / "home"
        self.data = base / "plugin-data"
        self.home.mkdir()
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "CLAUDE_PLUGIN_DATA": str(self.data / "planning-with-files-planning-with-files"),
            "CLAUDE_PID": "4242",
            "LANG": "en_US.UTF-8",
        }

    def hook(self, name: str, payload: dict, **extra_env: str) -> dict:
        env = dict(self.env, **extra_env)
        result = subprocess.run(
            [sys.executable, str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True, env=env,
        )
        out = result.stdout.strip()
        if result.stderr.strip():
            print("       stderr: " + result.stderr.strip()[:500])
        return json.loads(out) if out else {}

    def sh(self, cwd: Path, *args: str, **extra_env: str) -> subprocess.CompletedProcess:
        env = dict(self.env, **extra_env)
        return subprocess.run(list(args), cwd=str(cwd), capture_output=True, text=True, env=env)


def ctx(out: dict) -> str:
    return (out.get("hookSpecificOutput") or {}).get("additionalContext", "")


def make_plan(root: Path, plan_id: str, title: str, statuses: list[str]) -> None:
    directory = root / ".planning" / plan_id
    directory.mkdir(parents=True)
    body = [f"# Task Plan: {title}", "", "## Current Phase", "Phase 1", ""]
    for index, status in enumerate(statuses, 1):
        body += [f"### Phase {index}: Step {index}", f"- **Status:** {status}", ""]
    (directory / "task_plan.md").write_text("\n".join(body), encoding="utf-8")
    (directory / "findings.md").write_text("# Findings\n", encoding="utf-8")
    (directory / "progress.md").write_text("# Progress\n", encoding="utf-8")


def main() -> int:
    keep = "--keep" in sys.argv
    base = Path(tempfile.mkdtemp(prefix="pwf-smoke-"))
    env = Env(base)
    proj = base / "proj"
    proj.mkdir()
    make_plan(proj, "2026-01-01-other-task", "Other session task", ["complete", "in_progress"])
    make_plan(proj, "2026-01-02-older-task", "Older task", ["complete", "complete"])
    (proj / ".planning" / ".active_plan").write_text("2026-01-01-other-task\n")
    (proj / ".planning" / ".hooks_mode").write_text("on\n")
    common = {"cwd": str(proj)}

    print("[1] Unbound session never sees the project's .active_plan")
    out = env.hook("session_start.py", {**common, "session_id": S1, "source": "startup"})
    check("BEGIN PLAN DATA" not in ctx(out), "SessionStart injects no plan data")
    check("not bound to a plan" in ctx(out), "SessionStart gives the unbound hint")
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "hello"})
    check(out == {}, "UserPromptSubmit silent", json.dumps(out))
    out = env.hook("stop.py", {**common, "session_id": S1, "stop_hook_active": False})
    check(out == {}, "Stop silent", json.dumps(out))
    out = env.hook("permission_request.py", {**common, "session_id": S1, "tool_name": "Bash"})
    check(out == {}, "PermissionRequest silent")

    print("[2] init-session.sh binds atomically via CLAUDE_CODE_SESSION_ID")
    res = env.sh(proj, "bash", str(SCRIPTS / "init-session.sh"), "--plan-dir", "Feature Work", CLAUDE_CODE_SESSION_ID=S1)
    plan_ids = [line.split("=", 1)[1] for line in res.stdout.splitlines() if line.startswith("PLAN_ID=")]
    check(res.returncode == 0 and len(plan_ids) == 1, "init-session prints one PLAN_ID", res.stdout + res.stderr)
    new_id = plan_ids[0] if plan_ids else ""
    binding = proj / ".planning" / "sessions" / f"{S1}.active_plan"
    check(binding.is_file() and binding.read_text().strip() == new_id, "binding file written")
    check((proj / ".planning" / "sessions" / f"{S1}.attached").is_file(), ".attached sentinel written")
    check("# Task Plan: Feature Work" in (proj / ".planning" / new_id / "task_plan.md").read_text(), "title in heading")

    payload = {**common, "session_id": S1, "tool_name": "Bash",
               "tool_input": {"command": f"sh {SCRIPTS}/init-session.sh --plan-dir 'Feature Work'"},
               "tool_response": {"stdout": res.stdout, "stderr": ""}}
    out = env.hook("post_tool_use.py", payload)
    check("bound to" not in json.dumps(out), "PostToolUse: already bound → no duplicate message", json.dumps(out))

    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "continue"})
    text = ctx(out)
    check("BEGIN PLAN DATA" in text and new_id in text and "other-task" not in text.split("===END PLAN DATA===")[0],
          "UserPromptSubmit injects the bound plan only", text)
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "next"})
    check("unchanged since last injection" in ctx(out) and "BEGIN PLAN DATA" not in ctx(out),
          "second prompt gets the compact pointer", ctx(out))
    progress = proj / ".planning" / new_id / "progress.md"
    progress.write_text("# Progress\n- did a thing\n")
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "again"})
    check("BEGIN PLAN DATA" in ctx(out), "plan change → full injection again")

    print("[3] PostToolUse binds from the PLAN_ID line when the script saw no session id")
    res = env.sh(proj, "bash", str(SCRIPTS / "init-session.sh"), "--plan-dir", "Second Task")
    out = env.hook("post_tool_use.py", {**common, "session_id": S2, "tool_name": "Bash",
                                        "tool_input": {"command": f"bash {SCRIPTS}/init-session.sh --plan-dir 'Second Task'"},
                                        "tool_response": {"stdout": res.stdout, "stderr": ""}})
    second_id = [l.split("=", 1)[1] for l in res.stdout.splitlines() if l.startswith("PLAN_ID=")][0]
    check((proj / ".planning" / "sessions" / f"{S2}.active_plan").read_text().strip() == second_id,
          "S2 bound from stdout", json.dumps(out))
    check("CANONICAL PLAN FILES" in ctx(out), "bind emits canonical paths to the model")

    print("[4] Reading the script (cat/grep) never binds")
    script_text = (SCRIPTS / "init-session.sh").read_text()
    env.hook("pre_tool_use.py", {**common, "session_id": S3, "tool_name": "Bash",
                                 "tool_input": {"command": f"cat {SCRIPTS}/init-session.sh"}})
    env.hook("post_tool_use.py", {**common, "session_id": S3, "tool_name": "Bash",
                                  "tool_input": {"command": f"cat {SCRIPTS}/init-session.sh"},
                                  "tool_response": {"stdout": script_text, "stderr": ""}})
    check(not (proj / ".planning" / "sessions" / f"{S3}.active_plan").exists(), "S3 stays unbound")

    print("[5] 临时任务 suppresses hooks until the next normal prompt / Stop")
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "临时任务：查一下天气"})
    check(out == {}, "temporary prompt silent")
    out = env.hook("permission_request.py", {**common, "session_id": S1, "tool_name": "Bash"})
    check(out == {}, "other hooks silent while temporary")
    env.hook("stop.py", {**common, "session_id": S1})
    out = env.hook("permission_request.py", {**common, "session_id": S1, "tool_name": "Bash"})
    check("Session plan" in out.get("systemMessage", ""), "Stop cleared the temporary marker")

    print("[6] resume/fork with a new session id inherits the binding from the transcript")
    transcript = env.home / "t" / f"{S4}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(
        json.dumps({"type": "user", "sessionId": S1}, separators=(",", ":")) + "\n"
        + json.dumps({"type": "user", "sessionId": S4}, separators=(",", ":")) + "\n"
    )
    out = env.hook("session_start.py", {**common, "session_id": S4, "source": "resume", "transcript_path": str(transcript)})
    check((proj / ".planning" / "sessions" / f"{S4}.active_plan").read_text().strip() == new_id
          and "inherited" in ctx(out), "S4 inherited S1's plan", ctx(out)[:400])

    S8 = "88888888-8888-4888-8888-888888888888"
    S9 = "99999999-9999-4999-8999-999999999999"
    fork_dir = env.home / "fork"
    fork_dir.mkdir()
    msgs = [f"aaaaaaaa-0000-4000-8000-00000000000{i}" for i in range(4)]

    def lines(session: str, uuids: list[str]) -> str:
        return "".join(json.dumps({"type": "user", "uuid": u, "sessionId": session}, separators=(",", ":")) + "\n" for u in uuids)

    (fork_dir / f"{S1}.jsonl").write_text(lines(S1, msgs))
    (fork_dir / f"{S3}.jsonl").write_text(lines(S3, ["bbbbbbbb-0000-4000-8000-000000000000"]))
    (fork_dir / f"{S8}.jsonl").write_text(lines(S8, msgs + ["cccccccc-0000-4000-8000-000000000000"]))
    out = env.hook("session_start.py", {**common, "session_id": S8, "source": "fork", "transcript_path": str(fork_dir / f"{S8}.jsonl")})
    check((proj / ".planning" / "sessions" / f"{S8}.active_plan").read_text().strip() == new_id
          and "inherited" in ctx(out), "fork with rewritten sessionIds inherits via shared message uuids", ctx(out)[:300])
    (fork_dir / f"{S9}.jsonl").write_text("")
    out = env.hook("session_start.py", {**common, "session_id": S9, "source": "fork", "transcript_path": str(fork_dir / f"{S9}.jsonl")})
    check(ctx(out) == "", "fork before transcript is written: no hint, retry pending")
    (fork_dir / f"{S9}.jsonl").write_text(lines(S9, msgs[:2]))
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S9, "prompt": "go", "transcript_path": str(fork_dir / f"{S9}.jsonl")})
    check((proj / ".planning" / "sessions" / f"{S9}.active_plan").read_text().strip() == new_id
          and "inherited" in ctx(out), "first prompt retries lineage and inherits", ctx(out)[:300])

    print("[7] /clear carries the binding over (SessionEnd → SessionStart)")
    env.hook("session_end.py", {**common, "session_id": S1, "reason": "clear"})
    out = env.hook("session_start.py", {**common, "session_id": S5, "source": "clear"})
    check((proj / ".planning" / "sessions" / f"{S5}.active_plan").read_text().strip() == new_id
          and "carried over" in ctx(out), "S5 took over S1's plan after /clear", ctx(out)[:400])

    S6 = "66666666-6666-4666-8666-666666666666"
    S7 = "77777777-7777-4777-8777-777777777777"
    env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "attach", "2026-01-02-older-task", PWF_SESSION_ID=S6)
    out = env.hook("session_start.py", {**common, "session_id": S7, "source": "clear"})
    check("BEGIN PLAN DATA" not in ctx(out), "clear before SessionEnd: nothing yet")
    env.hook("session_end.py", {**common, "session_id": S6, "reason": "clear"})
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S7, "prompt": "go on"})
    check((proj / ".planning" / "sessions" / f"{S7}.active_plan").read_text().strip() == "2026-01-02-older-task"
          and "carried over" in ctx(out), "first prompt picks up the late handoff", ctx(out)[:300])

    print("[8] compact re-injects with a re-read note")
    out = env.hook("session_start.py", {**common, "session_id": S1, "source": "compact"})
    check("just compacted" in ctx(out) and "BEGIN PLAN DATA" in ctx(out), "compact note + plan")

    print("[9] Stop sync mode asks for a progress entry once")
    time.sleep(1.1)
    edit = {**common, "session_id": S1, "tool_name": "Edit", "tool_input": {"file_path": str(proj / "src.py")},
            "tool_response": {}}
    env.hook("post_tool_use.py", edit)
    out = env.hook("stop.py", {**common, "session_id": S1, "stop_hook_active": False})
    check("Before finishing" in ctx(out) and "decision" not in out, "non-error Stop feedback", json.dumps(out))
    out = env.hook("stop.py", {**common, "session_id": S1, "stop_hook_active": True})
    check(ctx(out) == "", "stop_hook_active → no second feedback")
    env.hook("post_tool_use.py", edit)
    time.sleep(1.1)
    progress.write_text("# Progress\n- logged\n")
    out = env.hook("stop.py", {**common, "session_id": S1, "stop_hook_active": False})
    check(ctx(out) == "", "progress updated → quiet stop", json.dumps(out))

    print("[10] Stop continue mode (opt-in)")
    out = env.hook("stop.py", {**common, "session_id": S1}, PWF_STOP_MODE="continue")
    check("incomplete" in ctx(out), "continue mode pushes remaining phases", json.dumps(out))
    out = env.hook("stop.py", {**common, "session_id": S1, "background_tasks": [{"id": "x"}]}, PWF_STOP_MODE="continue")
    check(ctx(out) == "", "continue mode waits for background tasks")

    print("[11] PostToolUse nudge: main thread only, once per window")
    sub = dict(edit, agent_id="agent-1")
    outs = [env.hook("post_tool_use.py", sub) for _ in range(6)]
    check(all(ctx(o) == "" for o in outs), "subagent never nudged")
    progress.write_text("# Progress\n- reset window\n")
    time.sleep(1.1)
    outs = [env.hook("post_tool_use.py", edit) for _ in range(7)]
    nudges = [o for o in outs if "since" in ctx(o)]
    check(len(nudges) == 1, "exactly one nudge in the window", str(len(nudges)))

    print("[12] Bare resolve-plan-dir.sh is denied")
    out = env.hook("pre_tool_use.py", {**common, "session_id": S1, "tool_name": "Bash",
                                       "tool_input": {"command": f"sh {SCRIPTS}/resolve-plan-dir.sh"}})
    check(out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", "deny")

    print("[13] session-plan.sh show / list / attach / detach")
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "show", PWF_SESSION_ID=S1)
    check(res.returncode == 0 and new_id in res.stdout, "show", res.stdout + res.stderr)
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "path", PWF_SESSION_ID=S1)
    check(res.stdout.strip() == str((proj / ".planning" / new_id).resolve()), "path", res.stdout)
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "list", PWF_SESSION_ID=S1)
    check(f"* {new_id}" in res.stdout and "PLAN_ID=" not in res.stdout, "list marks the bound plan", res.stdout)
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "attach", "2026-01-02-older-task", PWF_SESSION_ID=S3)
    check((proj / ".planning" / "sessions" / f"{S3}.active_plan").read_text().strip() == "2026-01-02-older-task"
          and (proj / ".planning" / ".active_plan").read_text().strip() != "2026-01-02-older-task",
          "attach binds without touching .active_plan", res.stdout + res.stderr)
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "attach", "nope", PWF_SESSION_ID=S3)
    check(res.returncode == 1, "attach rejects unknown plan")
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "detach", PWF_SESSION_ID=S3)
    out = env.hook("post_tool_use.py", {**common, "session_id": S3, "tool_name": "Bash",
                                        "tool_input": {"command": f"sh {SCRIPTS}/session-plan.sh detach"},
                                        "tool_response": {"stdout": res.stdout, "stderr": ""}})
    check(not (proj / ".planning" / "sessions" / f"{S3}.active_plan").exists(), "detach removes binding", res.stdout)
    res = env.sh(proj, "sh", str(SCRIPTS / "session-plan.sh"), "show", PWF_SESSION_ID=S3)
    check(res.returncode == 1, "show on unbound session exits 1")

    print("[14] attest / check-complete use the session's plan")
    res = env.sh(proj, "sh", str(SCRIPTS / "attest-plan.sh"), PWF_SESSION_ID=S2)
    check((proj / ".planning" / second_id / ".attestation").is_file()
          and not (proj / ".planning" / "2026-01-01-other-task" / ".attestation").exists(), "attest bound plan", res.stdout + res.stderr)
    res = env.sh(proj, "sh", str(SCRIPTS / "attest-plan.sh"), PWF_SESSION_ID=S3)
    check(res.returncode == 1 and "No plan is bound" in res.stderr, "attest refuses when unbound", res.stderr)
    res = env.sh(proj, "bash", str(SCRIPTS / "check-complete.sh"), PWF_SESSION_ID=S3)
    check("No plan is bound" in res.stdout, "check-complete reports unbound", res.stdout)
    (proj / ".planning" / second_id / "task_plan.md").write_text("# tampered\n")
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S2, "prompt": "go"})
    check("PLAN TAMPERED" in ctx(out), "tamper check blocks injection")

    print("[15] hooks_mode off silences everything")
    (proj / ".planning" / ".hooks_mode").write_text("off\n")
    out = env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "go"})
    check(out == {}, "off → silent")
    (proj / ".planning" / ".hooks_mode").write_text("on\n")

    print("[16] Phase counting formats")
    sys.path.insert(0, str(HOOKS))
    import planning_hook_adapter as adapter  # noqa: E402
    samples = {
        "## Phase 1\n**Status:** completed\n## Phase 2\n**Status:** in progress\n": (1, 2),
        "### 阶段 1\n- **状态：** 已完成\n### 阶段 2\n- **状态：** pending\n### 阶段 3\n": (1, 3),
        "| Phase | Status |\n|---|---|\n| A | done |\n| B | 进行中 |\n": (1, 2),
        "### Phase 1\n- **Status:** complete for runs 1-3\n": (1, 1),
    }
    for text, expected in samples.items():
        path = base / "sample.md"
        path.write_text(text, encoding="utf-8")
        check(adapter.phase_counts(path) == expected, f"phase_counts {expected}", str(adapter.phase_counts(path)))

    print("[17] Legacy root-level plan (no .planning/) still works")
    legacy = base / "legacy"
    legacy.mkdir()
    (legacy / "task_plan.md").write_text("# Legacy plan\n### Phase 1\n- **Status:** pending\n")
    out = env.hook("user_prompt_submit.py", {"cwd": str(legacy), "session_id": S1, "prompt": "go"})
    check("Legacy root-level plan" in ctx(out), "legacy injected")

    print("[18] SessionStart exports PWF_SESSION_ID through CLAUDE_ENV_FILE")
    env_file = base / "claude-env.sh"
    env.hook("session_start.py", {**common, "session_id": S2, "source": "startup"}, CLAUDE_ENV_FILE=str(env_file))
    check(f"export PWF_SESSION_ID={S2}" in env_file.read_text(), "env file written")

    print("[19] Plan-scoped catchup ignores sessions bound to other plans")
    projects = env.home / ".claude" / "projects" / __import__("re").sub(r"[^A-Za-z0-9]", "-", str(proj.resolve()))
    projects.mkdir(parents=True)
    filler = "x" * 2500

    def transcript_lines(texts: list[str]) -> str:
        return "".join(json.dumps({"type": "user", "message": {"content": t}}) + "\n" for t in texts)

    (projects / f"{S5}.jsonl").write_text(transcript_lines([f"work on feature plan details {filler}"]))
    (projects / f"{S2}.jsonl").write_text(transcript_lines([f"unrelated second task chatter {filler}"]))
    res = env.sh(proj, sys.executable, str(SCRIPTS / "session-catchup.py"), str(proj), "--plan-id", new_id, "--session-id", S1)
    check("feature plan details" in res.stdout and "unrelated second task" not in res.stdout,
          "catchup only shows sessions on the same plan", res.stdout + res.stderr)

    print("[20] A foreign CLAUDE_PLUGIN_DATA is ignored for private state")
    foreign = base / "codex-openai-codex"
    env.hook("user_prompt_submit.py", {**common, "session_id": S1, "prompt": "临时任务 x"}, CLAUDE_PLUGIN_DATA=str(foreign))
    check(not foreign.exists() and (env.home / ".claude" / "planning-with-files-state" / "sessions" / f"{S1}.json").is_file(),
          "state falls back to ~/.claude/planning-with-files-state")

    print("[21] Skill script copies are identical to scripts/")
    for skill in ("planning-with-files", "planning-with-files-zh"):
        for script in sorted(SCRIPTS.iterdir()):
            copy = REPO / "skills" / skill / "scripts" / script.name
            if script.name == "check-continue.sh":
                continue
            check(copy.is_file() and copy.read_bytes() == script.read_bytes(), f"{skill}/scripts/{script.name}")

    if keep:
        print(f"\nkept: {base}")
    else:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{'ALL PASSED' if not FAILURES else f'{len(FAILURES)} FAILED'}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
