from __future__ import annotations

import re
from pathlib import Path

from .identifiers import validate_path_component

_PARTICIPANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def validate_participant_id(participant_id: str) -> str:
    value = validate_path_component(participant_id, label="Participant ID").lstrip(" ")
    validate_path_component(value, label="Participant ID")
    if not value:
        raise ValueError("Participant ID is required.")
    if not _PARTICIPANT_RE.fullmatch(value):
        raise ValueError(
            "Participant ID may contain letters, numbers, '.', '_' and '-', "
            "must start with a letter/number, and must be at most 64 characters."
        )
    return value


def list_participants(data_root: Path) -> tuple[str, ...]:
    if not data_root.exists():
        return ()
    participants = []
    for path in data_root.iterdir():
        if not path.is_dir() or path.is_symlink():
            continue
        try:
            valid = validate_participant_id(path.name)
        except ValueError:
            continue
        if valid == path.name:
            participants.append(valid)
    return tuple(sorted(participants))


def participant_directory(data_root: Path, participant_id: str, *, create: bool = False) -> Path:
    participant = validate_participant_id(participant_id)
    directory = data_root / participant
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory
