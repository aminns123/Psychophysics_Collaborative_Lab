import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from Events.adaptive_session import LegacyStaircaseSession
from Events.adaptiveMethods import Trials_read_write_staircase_conditions
import Functions.functionsForUse as funcs
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def synthetic_run(tmp_path, monkeypatch, status="max_trials_reached"):
    """Exercise real configuration, runner finalization and legacy response IO.

    Only experiment display/composition is substituted; no Pyglet import/window.
    """
    import psychophysics_lab.core.runner as runner
    real_import = runner.importlib.import_module

    def experiment(conditions, parameters, response, state):
        root = Path(response).parent
        configured_conditions = json.loads(Path(conditions).read_text())
        configured_conditions["2AFC_choice"] = [10, 20]
        write_json(Path(conditions), configured_conditions)
        session = LegacyStaircaseSession(conditions, parameters, response,
                                        max_trials=3 if status == "max_trials_reached" else 30,
                                        metadata_path=root / "adaptive_session.json")
        write_json(root / "runtime_display.json", {"monitor_profile_id": "legacy_reference_display"})
        write_json(root / "resolved_experiment.json", {
            "experiment_id": "contrast_sensitivity",
            "adaptive_parameters": {"max_accepted_responses": session.run.max_trials},
        })
        window = SimpleNamespace(trials=[1], exit=lambda: None)
        logger = session.logger(window)
        sequence = [(0, True), (1, True), (0, False)]
        if status == "completed":
            sequence = [(identity, correct) for identity in (0, 1) for correct in (True, False, True)]
        elif status in {"aborted", "aborted_by_user", "error"}:
            sequence = sequence[:1]
        elif status == "empty_abort":
            sequence = []
        for identity, correct in sequence:
            def trial(name):
                return session.attach(Trials_read_write_staircase_conditions(
                    name, [], 250, [10, 0], conditions, parameters, response, keys=["LEFT", "RIGHT"]))
            with patch("random.choice", return_value=identity), patch("Events.adaptiveMethods._beep"):
                logger("TRIAL", 0, trial("new_condition"), [])
                target = trial("response")
                logger("TRIAL", 0, target, [])
                key = "LEFT" if correct else "RIGHT"
                logger("KEY", 0, target, [key, key])
        if status in {"aborted_by_user", "empty_abort"}:
            session.abort_by_user()
        if status == "error":
            session.save(status="error", error="synthetic failure")
        session.finish()
        funcs.removeZeroRow(response)
        # The legacy spacing helper cannot read an empty file. This synthetic
        # zero-response fixture checks the validator, without changing runtime.
        if sequence:
            funcs.correctFileSpacings(response)

    def import_module(name, *args, **kwargs):
        if name == "Experiments.contrast_sensitivity_function":
            return SimpleNamespace(run_experiment=experiment)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(runner.importlib, "import_module", import_module)
    request = SetupRequest("S001", "new", "contrast_sensitivity", "legacy_reference_display", {
        "Max_monitor_Luminance": 500., "Background_Luminance": 49., "Background_Screen_intensity": .374,
        "n_down": 1, "reversal_termination": 1,
        "max_trials": 3 if status == "max_trials_reached" else 30,
    })
    return run_request(request, repo_root=ROOT, data_root=tmp_path / "data").run_directory


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("status", ["completed", "max_trials_reached", "aborted_by_user", "aborted", "error"])
def test_valid_finalized_runs_are_read_only(tmp_path, monkeypatch, status):
    root = synthetic_run(tmp_path, monkeypatch, status)
    before = snapshot(root)
    checks = validate_run(root)
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]
    assert snapshot(root) == before


def test_existing_zero_response_export_failure_is_reported_without_repair(tmp_path, monkeypatch):
    root = synthetic_run(tmp_path, monkeypatch, "empty_abort")
    before = snapshot(root)
    checks = validate_run(root)
    assert any(c.name.startswith("Required canonical") and not c.passed for c in checks)
    assert any(c.name.startswith("Readable trial") and not c.passed for c in checks)
    assert snapshot(root) == before


@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    return synthetic_run(tmp_path, monkeypatch)


def mutate_json(root, name, mutation):
    path = root / name
    payload = json.loads(path.read_text())
    mutation(payload)
    write_json(path, payload)


@pytest.mark.parametrize("name,mutation,check", [
    ("manifest.json", lambda p: p.update(accepted_trials=99), "Accepted count"),
    ("manifest.json", lambda p: p.update(status="running"), "Final lifecycle"),
    ("manifest.json", lambda p: p.update(status="completed"), "Final lifecycle"),
    ("adaptive_session.json", lambda p: p.update(total_trials=99), "Adaptive counts"),
    ("state/parameters.final.json", lambda p: p.update(number_trials=99), "Configured maximum"),
    ("state/parameters.final.json", lambda p: p.pop("max_trials"), "Configured maximum"),
    ("monitor_profile.json", lambda p: p.update(notes=r"C:\Users\Someone\data"), "Portable canonical"),
    ("monitor_profile.json", lambda p: p.update(notes="/home/someone/data"), "Portable canonical"),
    ("experiment_config.json", lambda p: p["legacy_setup"].update(Name="S002"), "Manifest, configuration"),
    ("manifest.json", lambda p: p.update(output_sha256={"../outside": "0" * 64}), "Supplied output"),
])
def test_corrupt_metadata_fails_individual_checks(run_dir, name, mutation, check):
    mutate_json(run_dir, name, mutation)
    before = snapshot(run_dir)
    results = validate_run(run_dir)
    assert any(c.name.startswith(check) and not c.passed for c in results)
    assert snapshot(run_dir) == before


@pytest.mark.parametrize("column,value,check", [
    ("trial_index", "9", "Sequential"),
    ("presented_display_contrast", "0.1234", "Per-staircase"),
    ("presented_screen_intensity", "0.1234", "Per-staircase"),
    ("next_screen_intensity", "nan", "Per-staircase"),
    ("run_status", "running", "Final lifecycle"),
])
def test_corrupt_interleaved_trial_values(run_dir, column, value, check):
    path = run_dir / "trials.tsv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        header, rows = reader.fieldnames, list(reader)
    rows[-1][column] = value
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, header, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    assert any(c.name.startswith(check) and not c.passed for c in validate_run(run_dir))


@pytest.mark.parametrize("name,contents,check", [
    ("trials.tsv", "wrong\theader\n", "Canonical trial header"),
    ("manifest.json", "not JSON", "Manifest JSON"),
    ("manifest.json", "[]", "Manifest JSON"),
    ("trials_readable.txt", "wrong", "Readable trial"),
    ("trial_data_dictionary.tsv", "wrong", "Trial dictionary"),
    ("legacy_response.txt", "0 0 0 0 0 0", "Legacy response"),
])
def test_malformed_or_derived_files(run_dir, name, contents, check):
    (run_dir / name).write_text(contents)
    assert any(c.name.startswith(check) and not c.passed for c in validate_run(run_dir))


def test_missing_file_and_cli_exit_codes(run_dir):
    command = [sys.executable, str(ROOT / "scripts/validate_run.py"), str(run_dir)]
    before = snapshot(run_dir)
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("PASS\n")
    assert snapshot(run_dir) == before
    (run_dir / "trials_readable.txt").unlink()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stdout.startswith("FAIL\n")
    assert "missing files" in result.stdout


def test_missing_hashes_are_reported_without_false_integrity_claim(run_dir):
    mutate_json(run_dir, "manifest.json", lambda p: p.pop("output_sha256"))
    results = validate_run(run_dir)
    assert all(c.passed for c in results)
    assert any("no hashes supplied" in c.detail for c in results)


def test_missing_directory_reports_failure(tmp_path):
    assert not all(c.passed for c in validate_run(tmp_path / "missing"))
