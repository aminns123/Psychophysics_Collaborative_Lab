"""Stable public run-data access: actual saved runs and historical/additive TSVs.

These are read-only tests. They never rewrite a generated source run.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.data.reader import load_run
from psychophysics_lab.data.trials import TRIAL_COLUMNS
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]


def _snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


def _write_trials(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_real_generated_run_is_read_only_and_returned_as_arrays(tmp_path):
    artifacts, _ = simulate(
        repo_root=ROOT, data_root=tmp_path / "data", seed=27,
        values={"frequencies_cpd": "2,5",
                "staircases_per_condition": 1, "max_trials": 12},
        analyse=False,
    )
    directory = artifacts.run_directory
    before = _snapshot(directory)
    loaded = load_run(directory)

    assert list(loaded["trials"]) == list(TRIAL_COLUMNS)
    assert set(loaded["data_dictionary"]) == set(TRIAL_COLUMNS)
    assert loaded["manifest"]["trial_schema_version"] == 1
    assert loaded["trials"]["trial_index"].astype(int).tolist() == list(
        range(1, artifacts.accepted_trials + 1)
    )
    assert loaded["trials"]["correct"].dtype.kind == "U"
    assert np.isfinite(loaded["trials"]["presented_display_contrast"].astype(float)).all()
    assert load_run(directory / "trials.tsv")["trials"]["trial_index"].tolist() == (
        loaded["trials"]["trial_index"].tolist()
    )
    assert _snapshot(directory) == before


def test_additive_experiment_column_keeps_existing_fields_and_original_run(tmp_path):
    original = tmp_path / "original" / "run_001"
    original.mkdir(parents=True)
    row = dict.fromkeys(TRIAL_COLUMNS, "")
    row.update(trial_index="1", correct="1", stimulus_condition="target",
               presented_display_contrast="0.125")
    _write_trials(original / "trials.tsv", TRIAL_COLUMNS, [row])
    (original / "manifest.json").write_text(
        json.dumps({"trial_schema_version": 1, "experiment_id": "old_experiment"}),
        encoding="utf-8",
    )
    previous = _snapshot(original)

    # This represents a FUTURE, newly created run with an extra named field,
    # not an in-place change to the older canonical acquisition.
    extended = tmp_path / "new" / "run_001"
    shutil.copytree(original, extended)
    extended_row = dict(row, reaction_time_ms="245.7")
    _write_trials(extended / "trials.tsv", (*TRIAL_COLUMNS, "reaction_time_ms"), [extended_row])
    with (extended / "trial_data_dictionary.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, delimiter="\t",
            fieldnames=("column_name", "units_or_encoding", "meaning"),
        )
        writer.writeheader()
        writer.writerow({
            "column_name": "reaction_time_ms",
            "units_or_encoding": "ms",
            "meaning": "Example experiment-specific response interval",
        })
    after_extension = _snapshot(extended)
    data = load_run(extended)

    assert data["trials"]["reaction_time_ms"].tolist() == ["245.7"]
    assert data["trials"]["presented_display_contrast"].astype(float).tolist() == [0.125]
    assert data["data_dictionary"]["reaction_time_ms"]["units_or_encoding"] == "ms"
    assert "reaction_time_ms" not in load_run(original)["trials"]
    assert _snapshot(original) == previous
    assert _snapshot(extended) == after_extension


def test_older_unversioned_tsv_can_be_read_without_invented_metadata(tmp_path):
    directory = tmp_path / "archived" / "run_001"
    directory.mkdir(parents=True)
    _write_trials(directory / "trials.tsv",
                  ("trial_index", "correct", "old_condition"),
                  [{"trial_index": "1", "correct": "0", "old_condition": "A"}])
    loaded = load_run(directory)
    assert loaded["manifest"] == {}
    assert loaded["data_dictionary"] == {}
    assert loaded["trials"]["old_condition"].tolist() == ["A"]
    assert "presented_display_contrast" not in loaded["trials"]


@pytest.mark.parametrize("broken", [
    "trial_index\tcorrect\tcorrect\n1\t1\t0\n",
    "trial_index\tcorrect\n1\t1\textra\n",
    "trial_index\tcorrect\n1\n",
    "correct\n1\n",
])
def test_invalid_tsv_structure_is_rejected(tmp_path, broken):
    directory = tmp_path / "run_001"
    directory.mkdir()
    (directory / "trials.tsv").write_text(broken, encoding="utf-8")
    with pytest.raises(ValueError):
        load_run(directory)


def test_unknown_future_schema_is_refused_without_rewriting(tmp_path):
    directory = tmp_path / "run_001"
    directory.mkdir()
    _write_trials(directory / "trials.tsv",
                  ("trial_index",), [{"trial_index": "1"}])
    (directory / "manifest.json").write_text(
        '{"trial_schema_version": 2}', encoding="utf-8"
    )
    original = _snapshot(directory)
    with pytest.raises(ValueError, match="Unsupported trial_schema_version"):
        load_run(directory)
    assert _snapshot(directory) == original


def test_empty_and_optional_columns_are_preserved_as_text(tmp_path):
    directory = tmp_path / "run_001"
    directory.mkdir()
    _write_trials(directory / "trials.tsv",
                  ("trial_index", "custom_value"),
                  [{"trial_index": "1", "custom_value": ""}])
    assert load_run(directory)["trials"]["custom_value"].tolist() == [""]
