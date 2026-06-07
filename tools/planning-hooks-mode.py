#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


VALID_MODES = {
    "on": "on",
    "off": "off",
    "session": "session",
    "status": "status",
}


def mode_path(project_dir: Path) -> Path:
    return project_dir.expanduser().resolve() / ".planning" / ".hooks_mode"


def show(project_dir: Path) -> None:
    path = mode_path(project_dir)
    if path.exists():
        mode = path.read_text(encoding="utf-8").strip() or "(empty)"
    else:
        mode = "legacy"
    print(f"{project_dir.expanduser().resolve()}: planning hooks mode = {mode}")


def set_mode(project_dir: Path, mode: str) -> None:
    normalized = VALID_MODES.get(mode.strip().lower())
    if normalized is None or normalized == "status":
        raise ValueError("mode must be one of: on, off, session")
    path = mode_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{normalized}\n", encoding="utf-8")
    print(f"{project_dir.expanduser().resolve()}: planning hooks mode set to {normalized}")


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "status"
    project_dir = Path(argv[2]) if len(argv) > 2 else Path.cwd()
    if mode == "status":
        show(project_dir)
        return 0
    set_mode(project_dir, mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
