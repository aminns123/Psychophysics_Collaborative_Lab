import builtins
import csv
import json
from pathlib import Path
import random

import pytest
from simulations.csf import CSFObserver
from simulations.run import simulate
from psychophysics_lab.core.synthetic import simulation_workspace, SimulationRun, synthetic_recorded_utc
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.local import config_root
from psychophysics_lab.paths import resolve_data_root
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def test_seeded_pipeline_is_repeatable_labeled_and_headless(tmp_path,monkeypatch):
    real_import=builtins.__import__
    def no_hardware(name,*args,**kwargs):
        if name.split(".")[0] in {"pyglet","libC","winsound"}:
            raise AssertionError("Simulation imported hardware: " + name)
        return real_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",no_hardware)
    workspace=tmp_path/"psycolab_simulations"
    before=random.getstate()
    a,analysis=simulate(workspace=workspace,seed=123,repo_root=ROOT,values={"max_trials":120})
    b,_=simulate(workspace=workspace,seed=123,repo_root=ROOT,values={"max_trials":120})
    assert random.getstate() == before
    assert a.run_directory != b.run_directory
    assert a.trial_log_file.read_bytes() == b.trial_log_file.read_bytes()
    assert a.response_file.read_bytes() == b.response_file.read_bytes()
    assert a.status == "completed" and analysis is not None
    assert all(c.passed for c in validate_run(a.run_directory)), [c for c in validate_run(a.run_directory) if not c.passed]
    for name in ("manifest.json","trial_context.json","experiment_config.json","SYNTHETIC_DATA.json","runtime_display.json","adaptive_session.json"):
        assert json.loads((a.run_directory/name).read_text())["data_kind"] == "synthetic"
    rows=list(csv.DictReader(a.trial_log_file.open(),delimiter="\t"))
    assert rows and all(row["response_key"].startswith("SIMULATED_") for row in rows)
    assert rows[0]["recorded_utc"] == "2000-01-01T00:00:00+00:00"
    assert all(row["recorded_utc"] == synthetic_recorded_utc(float(row["event_time_s"])) for row in rows)
    assert json.loads((a.run_directory / "trial_context.json").read_text())["synthetic_clock"]["not_wall_clock"]
    assert "Deterministic virtual UTC" in (a.run_directory / "trial_data_dictionary.tsv").read_text()
    assert json.loads(analysis.summary_json.read_text())["data_kind"] == "synthetic"
    assert not (config_root(ROOT)/"preferences.json").exists()
    assert all(path.is_relative_to(workspace) for path in (a.run_directory,analysis.output_directory))
    c,_=simulate(workspace=workspace,seed=456,repo_root=ROOT,values={"max_trials":120})
    assert c.trial_log_file.read_bytes() != a.trial_log_file.read_bytes()


def test_short_simulation_has_no_fabricated_threshold(tmp_path):
    artifacts,analysis=simulate(workspace=tmp_path/"psycolab_simulations",seed=3,repo_root=ROOT,values={"max_trials":1})
    assert artifacts.status == "max_trials_reached" and artifacts.accepted_trials == 1
    assert analysis is None


def test_csf_tuning_and_threshold_have_correct_direction():
    observer=CSFObserver(threshold=.1,preferred_condition=63,lapse=.02)
    assert observer.probability_correct(0,63) == .5
    assert observer.probability_correct(.1,63) == pytest.approx(.74)
    assert observer.probability_correct(.2,63) > observer.probability_correct(.1,63)
    assert observer.probability_correct(.1,63) > observer.probability_correct(.1,252)
    assert observer.probability_correct(1e300,63) == pytest.approx(.98)
    assert CSFObserver(threshold=.2).probability_correct(.1,63) < observer.probability_correct(.1,63)


@pytest.mark.parametrize("kwargs", [dict(threshold=0),dict(slope=-1),dict(lapse=.5),dict(lapse=float("nan")),dict(preferred_condition=0),dict(tuning_width_octaves=0)])
def test_invalid_observer_rejected(kwargs):
    with pytest.raises(ValueError):
        CSFObserver(**kwargs)


def test_virtual_observers_share_human_data_root_without_touching_human_files(tmp_path):
    from psychophysics_lab.data.workspace import save_workspace_state
    from psychophysics_lab.data.participants import list_participants
    from psychophysics_lab.core.synthetic import MARKER, register_virtual_participant

    data_root = tmp_path / "local_psychophysics_data"
    data_root.mkdir()
    human = data_root / "H001"
    human.mkdir()
    sentinel = human / "human_trials.tsv"
    sentinel.write_bytes(b"DO NOT CHANGE")
    request = SetupRequest("H001", "new", "contrast_sensitivity", "legacy_reference_display", {})
    save_workspace_state(data_root, request, status="completed")
    original_state = (data_root / "psycolab_data_config.json").read_bytes()

    assert simulation_workspace(data_root, ROOT) == data_root.resolve()
    artifacts, _ = simulate(data_root=data_root, repo_root=ROOT, seed=123, values={"max_trials": 1})
    assert artifacts.run_directory.is_relative_to(data_root / "synthetic_123")
    assert (data_root / "synthetic_123" / MARKER).is_file()
    assert (artifacts.run_directory / "SYNTHETIC_DATA.json").exists()
    assert (data_root / "runs_index.csv").exists()
    assert sentinel.read_bytes() == b"DO NOT CHANGE"
    assert (data_root / "psycolab_data_config.json").read_bytes() == original_state
    assert list_participants(data_root) == ("H001",)
    assert resolve_data_root(data_root, ROOT) == data_root.resolve()


def test_virtual_ids_are_reserved_and_existing_unmarked_ids_are_not_adopted(tmp_path):
    from psychophysics_lab.core.synthetic import register_virtual_participant

    data_root = tmp_path / "local_psychophysics_data"
    data_root.mkdir()
    occupied = data_root / "synthetic_77"
    occupied.mkdir()
    sentinel = occupied / "trials.tsv"
    sentinel.write_bytes(b"DO NOT CHANGE")
    with pytest.raises(ValueError, match="not marked synthetic"):
        register_virtual_participant(data_root, "synthetic_77")
    assert sentinel.read_bytes() == b"DO NOT CHANGE"

    with pytest.raises(ValueError, match="reserved"):
        run_request(SetupRequest("synthetic_77", "new", "contrast_sensitivity",
                                 "legacy_reference_display", {}), repo_root=ROOT, data_root=data_root)
    with pytest.raises(ValueError, match="synthetic_"):
        run_request(SetupRequest("real_person", "new", "contrast_sensitivity",
                                 "legacy_reference_display", {}), repo_root=ROOT, data_root=data_root,
                    simulation=SimulationRun(data_root, {"seed": 1}, lambda *args: None))
    with pytest.raises(ValueError, match="separate folder"):
        simulation_workspace(ROOT / "unwanted", ROOT)
    assert sentinel.read_bytes() == b"DO NOT CHANGE"


def test_default_simulator_uses_selected_external_human_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "local_psychophysics_data"
    monkeypatch.setenv("PSYCOLAB_DATA_DIR", str(data_root))
    artifacts, _ = simulate(seed=5, repo_root=ROOT, values={"max_trials": 1}, analyse=False)
    assert artifacts.run_directory.is_relative_to(data_root / "synthetic_5")
    assert not (ROOT / "psycolab_simulations").exists()


def test_simulator_failure_stays_synthetic_and_finalises(tmp_path,monkeypatch):
    from simulations import registry
    from dataclasses import replace
    original=registry.get_simulation("contrast_sensitivity")
    def fail(*args):
        raise RuntimeError("synthetic test failure")
    monkeypatch.setitem(registry._REGISTRY,"contrast_sensitivity",replace(original,runtime_factory=lambda *args:fail))
    workspace=tmp_path/"psycolab_simulations"
    with pytest.raises(RuntimeError,match="synthetic test failure"):
        simulate(workspace=workspace,repo_root=ROOT)
    manifest=json.loads(next(workspace.rglob("manifest.json")).read_text())
    assert manifest["data_kind"] == "synthetic" and manifest["status"] == "error"
    assert not (config_root(ROOT)/"preferences.json").exists()


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf"), -float("inf")])
def test_synthetic_clock_rejects_nonfinite_or_negative_event_time(value):
    with pytest.raises(ValueError):
        synthetic_recorded_utc(value)


def test_synthetic_clock_fractional_event_time_and_human_fallback(tmp_path):
    from datetime import datetime, timezone
    from psychophysics_lab.data.trials import TrialLog
    assert synthetic_recorded_utc(0) == "2000-01-01T00:00:00+00:00"
    assert synthetic_recorded_utc(1.25) == "2000-01-01T00:00:01.250000+00:00"
    human_log = tmp_path / "human.tsv"
    earliest = datetime.now(timezone.utc)
    TrialLog(human_log).append({"trial_index": 1, "response_key": "LEFT"})
    latest = datetime.now(timezone.utc)
    with human_log.open(newline="", encoding="utf-8") as handle:
        human_row = next(csv.DictReader(handle, delimiter="\t"))
    assert earliest <= datetime.fromisoformat(human_row["recorded_utc"]) <= latest
