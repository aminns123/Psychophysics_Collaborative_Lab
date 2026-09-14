from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def copy_snapshot(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def response_owned_path(response_file: Path, suffix: str) -> Path:
    """Return a file next to the response file, uniquely tied to that run."""
    return response_file.with_name(f"{response_file.stem}{suffix}")
