#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PLANNING_HOOKS: dict[str, list[dict[str, Any]]] = {
    "PermissionRequest": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/permission_request.py 2>/dev/null || python3 "$HOME/.codex/hooks/permission_request.py" 2>/dev/null || true',
                    "type": "command",
                }
            ]
        }
    ],
    "PostToolUse": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/post_tool_use.py 2>/dev/null || python3 "$HOME/.codex/hooks/post_tool_use.py" 2>/dev/null || true',
                    "statusMessage": "Checking planning task creation",
                    "type": "command",
                }
            ],
            "matcher": "Bash",
        }
    ],
    "PreToolUse": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/pre_tool_use.py 2>/dev/null || python3 "$HOME/.codex/hooks/pre_tool_use.py" 2>/dev/null || true',
                    "statusMessage": "Checking planning task creation",
                    "type": "command",
                }
            ],
            "matcher": "Bash",
        }
    ],
    "SessionStart": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/session_start.py 2>/dev/null || python3 "$HOME/.codex/hooks/session_start.py" 2>/dev/null || true',
                    "statusMessage": "Loading planning context",
                    "type": "command",
                }
            ],
            "matcher": "startup|resume",
        }
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/stop.py 2>/dev/null || python3 "$HOME/.codex/hooks/stop.py" 2>/dev/null || true',
                    "timeout": 30,
                    "type": "command",
                }
            ]
        }
    ],
    "UserPromptSubmit": [
        {
            "hooks": [
                {
                    "command": 'python3 .codex/hooks/user_prompt_submit.py 2>/dev/null || python3 "$HOME/.codex/hooks/user_prompt_submit.py" 2>/dev/null || true',
                    "type": "command",
                }
            ]
        }
    ],
}


def hook_key(entry: dict[str, Any]) -> tuple[str, str]:
    matcher = str(entry.get("matcher", ""))
    commands: list[str] = []
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict):
            commands.append(str(hook.get("command", "")))
    return matcher, "\n".join(commands)


def is_legacy_shell_planning_entry(entry: dict[str, Any]) -> bool:
    for hook in entry.get("hooks", []):
        if not isinstance(hook, dict):
            continue
        command = str(hook.get("command", ""))
        if "session-start.sh" in command or "user-prompt-submit.sh" in command:
            return True
    return False


def is_planning_python_entry(entry: dict[str, Any]) -> bool:
    for hook in entry.get("hooks", []):
        if not isinstance(hook, dict):
            continue
        command = str(hook.get("command", ""))
        has_planning_hook_path = "/planning_" in command or ".codex/hooks/" in command
        has_planning_hook_script = (
            "pre_tool_use.py" in command
            or "post_tool_use.py" in command
            or "session_start.py" in command
            or "user_prompt_submit.py" in command
            or "stop.py" in command
            or "permission_request.py" in command
        )
        if has_planning_hook_path and has_planning_hook_script:
            return True
    return False


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path}: hooks must be a JSON object")
    return data


def ensure_default_hooks_mode(project_dir: Path) -> None:
    mode_path = project_dir / ".planning" / ".hooks_mode"
    if mode_path.exists():
        return
    mode_path.parent.mkdir(parents=True, exist_ok=True)
    mode_path.write_text("on\n", encoding="utf-8")


def register(project_dir: Path) -> Path:
    project_dir = project_dir.expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    codex_dir = project_dir / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    hooks_path = codex_dir / "hooks.json"
    data = load_config(hooks_path)
    hooks = data.setdefault("hooks", {})

    for event_name, entries in PLANNING_HOOKS.items():
        event_entries = hooks.setdefault(event_name, [])
        if not isinstance(event_entries, list):
            raise ValueError(f"{hooks_path}: hooks.{event_name} must be a list")
        if event_name in {
            "PermissionRequest",
            "PostToolUse",
            "PreToolUse",
            "SessionStart",
            "Stop",
            "UserPromptSubmit",
        }:
            event_entries[:] = [
                entry
                for entry in event_entries
                if not (
                    isinstance(entry, dict)
                    and (
                        is_legacy_shell_planning_entry(entry)
                        or is_planning_python_entry(entry)
                    )
                )
            ]
        existing_keys = {
            hook_key(entry)
            for entry in event_entries
            if isinstance(entry, dict)
        }
        for entry in entries:
            if hook_key(entry) not in existing_keys:
                event_entries.append(entry)

    with hooks_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    ensure_default_hooks_mode(project_dir)
    return hooks_path


def main(argv: list[str]) -> int:
    targets = argv[1:] or ["."]

    for arg in targets:
        hooks_path = register(Path(arg))
        print(f"registered planning hooks: {hooks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
