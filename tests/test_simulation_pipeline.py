import builtins
import csv
import json
from pathlib import Path
import random

import pytest
from simulations.csf import CSFObserver
from simulations.run import simulate
from psychophysics_lab.core.synthetic import simulation_workspace, SimulationRun
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


def test_workspace_never_adopts_or_changes_existing_data(tmp_path):
    occupied=tmp_path/"psycolab_simulations";occupied.mkdir()
    sentinel=occupied/"human.tsv";sentinel.write_bytes(b"DO NOT CHANGE")
    with pytest.raises(ValueError,match="unmarked"):
        simulation_workspace(occupied,ROOT)
    assert sentinel.read_bytes() == b"DO NOT CHANGE"
    assert len(list(occupied.iterdir())) == 1
    with pytest.raises(ValueError,match="named"):
        simulation_workspace(tmp_path/"real_data",ROOT)
    assert not (tmp_path/"real_data").exists()


def test_human_and_synthetic_workspaces_are_mutually_exclusive(tmp_path):
    synthetic=simulation_workspace(tmp_path/"psycolab_simulations",ROOT)
    for candidate in (synthetic,synthetic/"subfolder",tmp_path):
        with pytest.raises(ValueError,match="synthetic"):
            resolve_data_root(candidate,ROOT)
    human=tmp_path/"human";human.mkdir()
    (human/"psycolab_data_config.json").write_text("{}")
    with pytest.raises(ValueError,match="acquisition workspace"):
        simulation_workspace(human/"psycolab_simulations",ROOT)
    request=SetupRequest("real_person","new","contrast_sensitivity","legacy_reference_display",{})
    with pytest.raises(ValueError,match="synthetic_"):
        run_request(request,repo_root=ROOT,data_root=synthetic,simulation=SimulationRun(synthetic,{"seed":1},lambda *a:None))
    assert list(synthetic.iterdir()) == [synthetic/".psycolab_synthetic.json"]


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
