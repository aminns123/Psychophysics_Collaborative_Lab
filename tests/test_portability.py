from __future__ import annotations

import json
from pathlib import Path

import pytest

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.data.workspace import (
    load_workspace_state,
    request_from_workspace_state,
    save_workspace_state,
)


def test_workspace_state_does_not_persist_machine_data_root(tmp_path):
    request = SetupRequest(
        participant_id="S001",
        session_mode="new",
        experiment_id="contrast_sensitivity",
        monitor_profile_id="legacy_reference_display",
        experiment_values={"example": 1},
        data_root=r"C:\Users\ExampleUser\Desktop\PsyCoLabData",
    )

    path = save_workspace_state(tmp_path, request, status="configured")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["data_root"] == "."
    assert payload["last_request"]["data_root"] is None
    restored = request_from_workspace_state(load_workspace_state(tmp_path))
    assert restored is not None
    assert restored.data_root is None


def test_shared_runtime_files_do_not_contain_author_specific_path_literals():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "src",
        root / "Events",
        root / "Experiments",
        root / "Functions",
        root / "Interface",
        root / "scripts",
        root / "configs",
    ]
    needles = (
        "AlexanderMinns",
        "Alexander Minns",
        "C:\\Users\\",
        "C:/Users/",
        "Physics/PhD/GitHub",
        "Physics\\PhD\\GitHub",
    )

    hits: list[str] = []
    for directory in scan_roots:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".json", ".toml", ".bat", ".txt"}:
                continue
            if ".venv" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for needle in needles:
                if needle in text:
                    hits.append(f"{path.relative_to(root)} contains {needle!r}")

    assert hits == []


@pytest.mark.parametrize("name", ["tmp/archive-audit/dependency.whl", "temp/probe.py",
                                 ".idea/workspace.xml", "local_psychophysics_data/S001/trials.tsv",
                                 "run.log", "state.json.tmp", ".venv.incompatible-old/file.py"])
def test_portability_checker_rejects_tracked_temporary_data_and_runtime_files(monkeypatch, name):
    from scripts import portability_check

    monkeypatch.setattr(portability_check, "tracked_files", lambda: [name])
    monkeypatch.setattr(portability_check, "text_files", lambda: [])
    assert portability_check.main() == 1
