#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HOOK_DIR = Path(__file__).resolve().parent
TEMPORARY_TASK_KEYWORDS = ("临时任务",)
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
BASH_TOOL_NAMES = {
    "bash",
    "shell",
    "exec_command",
    "functions.exec_command",
}
PLAN_CREATION_SCRIPT_NAMES = ("init-session.sh", "init-session.ps1")
RESOLVER_INVOKE_RE = re.compile(
    r"(?:^|[;&|`$(]\s*)"
    r"(?:env\s+(?:\S+=\S+\s+)*)?"
    r"(?:sh|bash|zsh|pwsh|powershell)\b[^\n;|&]*resolve-plan-dir\.(?:sh|ps1)\b"
    r"|(?:^|[;&|`$(]\s*)(?:\.{0,2}/|~|\$HOME|/)[^\s;|&]*resolve-plan-dir\.(?:sh|ps1)\b",
    re.MULTILINE,
)


def load_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def cwd_from_payload(payload: dict[str, Any]) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd)
    return Path.cwd()


def _session_id_from_transcript_path(payload: dict[str, Any]) -> str:
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return ""
    matches = UUID_RE.findall(Path(transcript_path).name)
    return matches[-1] if matches else ""


def session_id_from_payload(payload: dict[str, Any]) -> str | None:
    transcript_sid = _session_id_from_transcript_path(payload)
    if transcript_sid:
        return transcript_sid
    for key in ("thread_id", "conversation_id", "session_id", "turn_id"):
        sid = payload.get(key)
        if isinstance(sid, str) and sid:
            return sid
    env_sid = os.environ.get("PWF_SESSION_ID", "")
    return env_sid if env_sid else None


def tool_name_from_payload(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            nested = value.get("name")
            if isinstance(nested, str) and nested:
                return nested
    return ""


def _normalized_tool_name(payload: dict[str, Any]) -> str:
    return tool_name_from_payload(payload).strip().lower()


def is_bash_tool(payload: dict[str, Any]) -> bool:
    return _normalized_tool_name(payload) in BASH_TOOL_NAMES


def command_text_from_payload(payload: dict[str, Any]) -> str:
    candidates: list[str] = []
    for key in ("command", "cmd"):
        value = payload.get(key)
        if isinstance(value, str):
            candidates.append(value)
    for key in ("tool_input", "input", "arguments", "args"):
        value = payload.get(key)
        candidates.extend(_collect_strings(value))
    return "\n".join(candidates)


def is_plan_creation_command(payload: dict[str, Any]) -> bool:
    if not is_bash_tool(payload):
        return False
    command_text = command_text_from_payload(payload)
    return any(script_name in command_text for script_name in PLAN_CREATION_SCRIPT_NAMES)


def is_bare_resolver_command(payload: dict[str, Any]) -> bool:
    """True if a Bash command runs resolve-plan-dir.sh without a PLAN_ID.

    The resolver is session-aware ONLY when PLAN_ID is set (the hook adapter
    injects it). An agent running it in a plain shell has no PLAN_ID and falls
    back to .planning/.active_plan — the wrong plan when several exist. Escape
    hatches: pass an explicit PLAN_ID=<id>/$PLAN_ID, or PWF_ALLOW_BARE_RESOLVE=1.
    """
    if not is_bash_tool(payload):
        return False
    command_text = command_text_from_payload(payload)
    if not RESOLVER_INVOKE_RE.search(command_text):
        return False
    if "PWF_ALLOW_BARE_RESOLVE=1" in command_text:
        return False
    return "PLAN_ID=" not in command_text and "$PLAN_ID" not in command_text


def _normalize_mode(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _mode_from_project(root: Path) -> str:
    mode_file = root / ".planning" / ".hooks_mode"
    if not mode_file.exists():
        return ""
    try:
        return _normalize_mode(mode_file.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _is_sentinel_attached(root: Path, session_id: str | None) -> bool:
    sessions_dir = root / ".planning" / "sessions"
    if not sessions_dir.exists():
        return False
    if not session_id:
        return False
    return (sessions_dir / f"{session_id}.attached").exists()


def _safe_plan_id(value: str) -> str:
    plan_id = value.strip()
    if not plan_id or "/" in plan_id or "\\" in plan_id or plan_id.startswith("."):
        return ""
    return plan_id


def _plan_dir(root: Path, plan_id: str) -> Path:
    return root / ".planning" / plan_id


def _read_plan_id(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return _safe_plan_id(path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _is_valid_plan(root: Path, plan_id: str) -> bool:
    if not plan_id:
        return False
    return (_plan_dir(root, plan_id) / "task_plan.md").exists()


def project_active_plan_id(root: Path) -> str:
    plan_id = _read_plan_id(root / ".planning" / ".active_plan")
    return plan_id if _is_valid_plan(root, plan_id) else ""


def _session_active_plan_path(root: Path, session_id: str | None) -> Path | None:
    if not session_id:
        return None
    return root / ".planning" / "sessions" / f"{session_id}.active_plan"


def session_active_plan_id(root: Path, session_id: str | None) -> str:
    path = _session_active_plan_path(root, session_id)
    if path is None:
        return ""
    plan_id = _read_plan_id(path)
    if _is_valid_plan(root, plan_id):
        return plan_id
    return ""


def bind_session_to_plan(root: Path, session_id: str | None, plan_id: str) -> bool:
    path = _session_active_plan_path(root, session_id)
    if path is None or not _is_valid_plan(root, plan_id):
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{plan_id}\n", encoding="utf-8")
    except OSError:
        return False
    return True


def _before_tool_active_plan_path(root: Path, session_id: str | None) -> Path | None:
    if not session_id:
        return None
    return root / ".planning" / "sessions" / f"{session_id}.before_tool_active_plan"


def record_project_active_before_tool(root: Path, session_id: str | None) -> None:
    path = _before_tool_active_plan_path(root, session_id)
    if path is None:
        return
    plan_id = project_active_plan_id(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{plan_id}\n", encoding="utf-8")
    except OSError:
        return


def rebind_session_if_project_active_changed(root: Path, session_id: str | None) -> str:
    path = _before_tool_active_plan_path(root, session_id)
    if path is None or not path.exists():
        return session_active_plan_id(root, session_id)
    before_id = _read_plan_id(path)
    current_id = project_active_plan_id(root)
    try:
        path.unlink()
    except OSError:
        pass
    if current_id and current_id != before_id:
        bind_session_to_plan(root, session_id, current_id)
        return current_id
    return session_active_plan_id(root, session_id)


def rebind_session_to_project_active(root: Path, session_id: str | None) -> str:
    plan_id = project_active_plan_id(root)
    if plan_id:
        bind_session_to_plan(root, session_id, plan_id)
    return plan_id


def ensure_session_plan(root: Path, session_id: str | None) -> str:
    return session_active_plan_id(root, session_id)


def _temp_disable_path(root: Path, session_id: str | None) -> Path:
    if session_id:
        return root / ".planning" / "sessions" / f"{session_id}.temporary-off"
    return root / ".planning" / ".temporary-off"


def is_temporarily_disabled(root: Path, session_id: str | None) -> bool:
    return _temp_disable_path(root, session_id).exists()


def set_temporary_disable(root: Path, session_id: str | None) -> None:
    marker = _temp_disable_path(root, session_id)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("temporary task\n", encoding="utf-8")
    except OSError:
        return


def clear_temporary_disable(root: Path, session_id: str | None) -> None:
    marker = _temp_disable_path(root, session_id)
    try:
        marker.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_collect_strings(item))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_collect_strings(item))
        return strings
    return []


def has_temporary_task_keyword(payload: dict[str, Any]) -> bool:
    text = "\n".join(_collect_strings(payload))
    return any(keyword in text for keyword in TEMPORARY_TASK_KEYWORDS)


def is_session_attached(root: Path, session_id: str | None) -> bool:
    """Return True if this session should receive plan context.

    Resolution order (first match wins):
      1. temporary-task suppression (`临时任务`) -> off for this session.
      2. PWF_HOOKS env var: on/off.
      3. .planning/.hooks_mode project file:
           on      -> always on
           off     -> always off
           session -> strict per-session isolation (requires a `.attached`
                      sentinel for this session_id)
      4. DEFAULT -> on. This matches the official plugin's out-of-the-box
         behaviour: whenever a plan resolves, inject it. Per-session binding
         (`sessions/<id>.active_plan`) is then an *override* for parallel
         isolation, not a gate — unbound sessions still get the project's
         active/newest plan. Set `.hooks_mode = session` if you want the
         strict "only explicitly-attached sessions get context" behaviour.
    """
    if is_temporarily_disabled(root, session_id):
        return False

    env_mode = _normalize_mode(os.environ.get("PWF_HOOKS", ""))
    if env_mode in {"1", "true", "yes", "on", "enable", "enabled"}:
        return True
    if env_mode in {"0", "false", "no", "off", "disable", "disabled"}:
        return False

    project_mode = _mode_from_project(root)
    if project_mode in {"1", "true", "yes", "on", "enable", "enabled"}:
        return True
    if project_mode in {"0", "false", "no", "off", "disable", "disabled"}:
        return False
    if project_mode in {"session", "session_only", "attached"}:
        return _is_sentinel_attached(root, session_id)

    return True  # default: official out-of-the-box behaviour


def _newest_plan_dir_id(root: Path) -> str:
    plan_root = root / ".planning"
    if not plan_root.is_dir():
        return ""
    newest = ""
    newest_mt = -1.0
    for entry in plan_root.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if not (entry / "task_plan.md").exists():
            continue
        try:
            mt = entry.stat().st_mtime
        except OSError:
            continue
        if mt > newest_mt:
            newest_mt = mt
            newest = entry.name
    return newest


def effective_plan_present(root: Path, session_id: str | None) -> bool:
    """True if any plan would resolve for this session.

    Mirrors resolve-plan-dir.sh + legacy fallback so the Python gate matches
    what the shell renderers will actually emit:
      session binding -> project .active_plan -> newest plan dir -> legacy
      ./task_plan.md.
    """
    if session_active_plan_id(root, session_id):
        return True
    if project_active_plan_id(root):
        return True
    if _newest_plan_dir_id(root):
        return True
    return (root / "task_plan.md").exists()


def emit_json(payload: dict[str, Any]) -> None:
    if not payload:
        return
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def emit_context(event_name: str, text: str) -> None:
    """Inject text into the model context using Claude Code's hook contract.

    Claude Code adds `hookSpecificOutput.additionalContext` to the conversation
    for SessionStart / UserPromptSubmit / PreToolUse / PostToolUse. This replaces
    the Codex `{"systemMessage": ...}` channel, which on Claude Code only renders
    a transient notice and is NOT fed back to the model.
    """
    if not text:
        return
    emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": text,
            }
        }
    )


def parse_json(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def run_shell_script(
    script_name: str,
    cwd: Path,
    session_id: str | None = None,
) -> tuple[str, str]:
    env = os.environ.copy()
    if session_id:
        env["PWF_SESSION_ID"] = session_id
    plan_id = session_active_plan_id(cwd, session_id)
    if plan_id:
        env["PLAN_ID"] = plan_id
    result = subprocess.run(
        ["sh", str(HOOK_DIR / script_name)],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip(), result.stderr.strip()


def main_guard(func) -> int:
    try:
        func()
    except Exception as exc:  # pragma: no cover
        print(f"[planning-with-files hook] {exc}", file=sys.stderr)
        return 0
    return 0
