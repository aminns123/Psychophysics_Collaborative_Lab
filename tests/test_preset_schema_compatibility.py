"""Issue #81: saved preset compatibility must not silently reinterpret newer schemas.

All fixtures live in pytest's temporary directory. No real laboratory presets
or participant data are read or modified.
"""
import json
from pathlib import Path

import pytest

from psychophysics_lab.config.local import (
    load_presets, save_preset, update_preset, PRESET_SCHEMA_VERSION,
)


def _files(root: Path):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.rglob("*") if p.is_file()
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
