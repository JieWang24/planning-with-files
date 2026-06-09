#!/usr/bin/env python3
"""Toggle planning-with-files hook debug for a project (default OFF).

Writes/clears `<project>/.planning/.hooks_debug`. When enabled, every planning
hook appends a JSONL event to `<project>/.planning/debug/hook-events.jsonl` and
surfaces a one-line `systemMessage` describing what it did. You can also enable
per-shell with `PWF_HOOK_DEBUG=on` (env wins over the file).

Usage:
    python3 planning-hooks-debug.py status [project_dir]
    python3 planning-hooks-debug.py on     [project_dir]
    python3 planning-hooks-debug.py off    [project_dir]
"""
from __future__ import annotations

import sys
from pathlib import Path


VALID_VALUES = {"on": "on", "off": "off", "status": "status"}


def debug_path(project_dir: Path) -> Path:
    return project_dir.expanduser().resolve() / ".planning" / ".hooks_debug"


def log_path(project_dir: Path) -> Path:
    return project_dir.expanduser().resolve() / ".planning" / "debug" / "hook-events.jsonl"


def show(project_dir: Path) -> None:
    path = debug_path(project_dir)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip() or "(empty)"
    else:
        value = "off"
    root = project_dir.expanduser().resolve()
    print(f"{root}: planning hooks debug = {value}")
    print(f"log = {log_path(project_dir)}")


def set_debug(project_dir: Path, value: str) -> None:
    normalized = VALID_VALUES.get(value.strip().lower())
    if normalized is None or normalized == "status":
        raise ValueError("debug mode must be one of: on, off")
    path = debug_path(project_dir)
    if normalized == "off":
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{normalized}\n", encoding="utf-8")
    print(f"{project_dir.expanduser().resolve()}: planning hooks debug set to {normalized}")
    print(f"log = {log_path(project_dir)}")


def main(argv: list[str]) -> int:
    value = argv[1] if len(argv) > 1 else "status"
    project_dir = Path(argv[2]) if len(argv) > 2 else Path.cwd()
    if value == "status":
        show(project_dir)
        return 0
    set_debug(project_dir, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
