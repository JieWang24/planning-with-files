#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


VALID_VALUES = {
    "on": "on",
    "off": "off",
    "status": "status",
}


def debug_path(project_dir: Path) -> Path:
    return project_dir.expanduser().resolve() / ".planning" / ".hooks_debug"


def show(project_dir: Path) -> None:
    path = debug_path(project_dir)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip() or "(empty)"
    else:
        value = "off"
    print(f"{project_dir.expanduser().resolve()}: planning hooks debug = {value}")
    print(f"log = {path.parent / 'debug' / 'hook-events.jsonl'}")


def set_debug(project_dir: Path, value: str) -> None:
    normalized = VALID_VALUES.get(value.strip().lower())
    if normalized is None or normalized == "status":
        raise ValueError("debug mode must be one of: on, off")
    path = debug_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{normalized}\n", encoding="utf-8")
    print(f"{project_dir.expanduser().resolve()}: planning hooks debug set to {normalized}")
    print(f"log = {path.parent / 'debug' / 'hook-events.jsonl'}")


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
