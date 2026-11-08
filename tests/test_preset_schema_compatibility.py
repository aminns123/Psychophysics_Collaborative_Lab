"""Issue #81: saved preset compatibility must not silently reinterpret newer schemas.

All fixtures live in pytest's temporary directory. No real laboratory presets
or participant data are read or modified.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
from threading import Barrier

import pytest

from psychophysics_lab.config.local import (
    load_presets, save_preset, update_preset, PRESET_SCHEMA_VERSION,
)


def _files(root: Path):
    """Check persisted JSON bytes and mtimes; lock files are coordination only."""
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*.json") if p.is_file()
    }


@pytest.mark.parametrize("unsupported", [2, 999, True, "1", None, 0])
def test_future_or_invalid_preset_version_is_not_loaded_or_edited(tmp_path, unsupported):
    directory = tmp_path / "presets" / "contrast_sensitivity"
    directory.mkdir(parents=True)
    original = directory / "older.json"
    original.write_text(json.dumps({
        "schema_version": unsupported,
        "experiment_id": "contrast_sensitivity",
        "values": {"n_down": 3},
    }), encoding="utf-8")
    before = _files(tmp_path)

    with pytest.warns(RuntimeWarning, match="unsupported schema_version"):
        assert "older" not in load_presets(tmp_path, "contrast_sensitivity")

    with pytest.raises(ValueError, match="missing or unsupported schema_version"):
        update_preset(tmp_path, "older", "contrast_sensitivity", {"n_down": 5})

    assert _files(tmp_path) == before
    assert not (directory / ".history").exists()


def test_unversioned_historical_preset_still_loads_without_being_migrated(tmp_path):
    directory = tmp_path / "presets" / "example_experiment"
    directory.mkdir(parents=True)
    original = directory / "legacy.json"
    original.write_text(json.dumps({
        "experiment_id": "example_experiment",
        "values": {"test_count": 3},
    }), encoding="utf-8")
    before = _files(tmp_path)

    with pytest.warns(RuntimeWarning, match="legacy unversioned"):
        assert load_presets(tmp_path, "example_experiment") == {
            "legacy": {"test_count": 3}
        }

    # Explicit Update cannot silently migrate an unversioned old file;
    # Save as a separate new preset instead.
    with pytest.raises(ValueError, match="missing or unsupported schema_version"):
        update_preset(tmp_path, "legacy", "example_experiment", {"test_count": 5})

    assert _files(tmp_path) == before


def test_current_preset_load_and_explicit_update_preserve_backup(tmp_path):
    assert PRESET_SCHEMA_VERSION == 1
    path = save_preset(tmp_path, "today", "example_experiment", {"test_count": 4})
    assert load_presets(tmp_path, "example_experiment")["today"] == {"test_count": 4}
    before = path.read_bytes()
    assert json.loads(before)["schema_version"] == 1

    update_preset(tmp_path, "today", "example_experiment", {"test_count": 6})
    assert load_presets(tmp_path, "example_experiment")["today"] == {"test_count": 6}
    copies = list((path.parent / ".history").glob("today_*.json"))
    assert len(copies) == 1
    assert json.loads(copies[0].read_text(encoding="utf-8")) == json.loads(before)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_other_experiment_or_malformed_json_is_not_reinterpreted(tmp_path):
    directory = tmp_path / "presets" / "example_experiment"
    directory.mkdir(parents=True)
    (directory / "wrong.json").write_text(
        '{"schema_version":1,"experiment_id":"contrast_sensitivity","values":{"n_down":2}}',
        encoding="utf-8",
    )
    (directory / "malformed.json").write_text('{",', encoding="utf-8")
    before = _files(tmp_path)
    assert load_presets(tmp_path, "example_experiment") == {}
    assert _files(tmp_path) == before


@pytest.mark.parametrize("existing", ["current", "future", "malformed", "case-only", "directory"])
def test_save_new_preset_never_replaces_an_occupied_name(tmp_path, existing):
    experiment = "contrast_sensitivity"
    directory = tmp_path / "presets" / experiment
    directory.mkdir(parents=True)
    original = directory / ("Held.json" if existing == "case-only" else "held.json")
    if existing == "directory":
        original.mkdir()
        (original / "retained.json").write_bytes(b'{"keep":true}')
    elif existing == "malformed":
        original.write_bytes(b'{"schema_version":')
    else:
        original.write_text(json.dumps({
            "schema_version": 999 if existing == "future" else 1,
            "experiment_id": experiment, "values": {"n_down": 3},
        }), encoding="utf-8")
    if existing == "case-only" and not (directory / "held.json").exists():
        pytest.skip("This filesystem distinguishes uppercase and lowercase filenames.")

    before = _files(tmp_path)
    with pytest.raises(ValueError, match="already exists. Choose a new preset name"):
        save_preset(tmp_path, "held", experiment, {"n_down": 5})
    assert _files(tmp_path) == before
    assert list(directory.iterdir()) == [original]


def test_save_new_preset_refuses_unsafe_name_or_linked_directory(tmp_path):
    config = tmp_path / "config"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "retained.json").write_bytes(b'{"keep":true}')
    before = _files(tmp_path)
    with pytest.raises(ValueError, match="invalid filename"):
        save_preset(config, "../outside", "example_experiment", {})
    assert _files(tmp_path) == before and not config.exists()

    config.mkdir()
    linked = config / "presets"
    if os.name == "nt":
        junction = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(linked), str(outside)], capture_output=True,
        )
        assert junction.returncode == 0, junction.stderr
    else:
        linked.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="escapes local configuration"):
            save_preset(config, "held", "example_experiment", {})
        assert _files(outside) == {"retained.json": before["outside/retained.json"]}
        assert list(outside.iterdir()) == [outside / "retained.json"]
    finally:
        if os.name == "nt":
            linked.rmdir()


@pytest.mark.parametrize("dangling", [False, True])
def test_save_new_preset_preserves_existing_symlink(tmp_path, dangling):
    experiment = "example_experiment"
    directory = tmp_path / "presets" / experiment
    directory.mkdir(parents=True)
    target = directory / "target.json"
    if not dangling:
        target.write_bytes(b'{"keep":true}')
    original = directory / "held.json"
    try:
        original.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"File symlinks unavailable: {exc}")
    original_target = original.readlink()
    with pytest.raises(ValueError, match="already exists. Choose a new preset name"):
        save_preset(tmp_path, "held", experiment, {})
    assert original.is_symlink() and original.readlink() == original_target
    if dangling:
        assert not target.exists()
    else:
        assert target.read_bytes() == b'{"keep":true}'
    assert not list(directory.glob("*.tmp"))


def test_concurrent_save_new_preset_publishes_exactly_one_complete_file(tmp_path, monkeypatch):
    experiment = "example_experiment"
    operation = "rename" if os.name == "nt" else "link"
    publish = getattr(os, operation)
    ready_to_publish = Barrier(2)

    def race(source, destination):
        ready_to_publish.wait(timeout=10)
        return publish(source, destination)

    def attempt(value):
        try:
            return save_preset(tmp_path, "shared", experiment, {"test_count": value}), value
        except ValueError as exc:
            assert "already exists. Choose a new preset name" in str(exc)
            return None, value

    with monkeypatch.context() as patch:
        patch.setattr(os, operation, race)
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, [4, 7]))
    [(winner, value)] = [(path, value) for path, value in results if path is not None]
    assert list(winner.parent.iterdir()) == [winner]
    assert load_presets(tmp_path, experiment) == {"shared": {"test_count": value}}


@pytest.mark.parametrize("failure", ["fsync", "publish"])
def test_failed_new_preset_save_leaves_no_partial_document(tmp_path, monkeypatch, failure):
    experiment = "example_experiment"
    original = save_preset(tmp_path, "keep", experiment, {"test_count": 4})
    before = _files(tmp_path)
    operation = "rename" if os.name == "nt" else "link"

    def fail(*args):
        raise OSError("injected failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync" if failure == "fsync" else operation, fail)
        with pytest.raises(OSError, match="Check the preset folder and try again"):
            save_preset(tmp_path, "new", experiment, {"test_count": 7})
    assert _files(tmp_path) == before
    assert list(original.parent.iterdir()) == [original]
