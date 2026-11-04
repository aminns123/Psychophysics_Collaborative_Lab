"""Real TUI mount/teardown and recording across multiple runs; no optical claims."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab import app as launcher
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.researcher import experiment, ConfigField
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen
from psychophysics_lab.ui.session import RunResultScreen
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def prepare(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "find_repo_root", lambda: ROOT)
    monkeypatch.setattr(launcher, "default_data_root", lambda _: tmp_path / "data")
    monkeypatch.setattr(launcher, "preferred_data_root", lambda _, default: default)
    monkeypatch.setattr(launcher, "remember_data_root", lambda *a: None)
    monkeypatch.setattr("psychophysics_lab.extensions.initialise_default", lambda *a, **k: None)


@pytest.mark.parametrize("second", ["session_one", "session_two"])
def test_two_recorded_experiments_in_one_application_session(monkeypatch, tmp_path, second):
    prepare(monkeypatch, tmp_path)
    from psychophysics_lab.core.runner import run_request
    from psychophysics_lab.core.synthetic import SimulationRun
    def software_run(request, **options):
        return run_request(replace(request, participant_id="synthetic_123"), **options,
            simulation=SimulationRun(tmp_path / "data", {"seed": 123}, lambda *a: None))
    monkeypatch.setattr("psychophysics_lab.core.runner.run_request", software_run)

    def procedure(run):
        count = run.values["trial_count"]
        run.initialise(expected_trials=count, resolution={"task": "nonvisual recording integration"})
        for _ in range(count):
            run.record(stimulus_condition="left", target_alternative=0,
                       participant_response=0, response_key="LEFT", correct=1)
        run.complete()

    for identity in ("session_one", "session_two"):
        monkeypatch.setitem(registry._REGISTRY, identity, experiment(id=identity, name=identity,
            description="Software integration only", procedure=procedure,
            fields=(ConfigField("trial_count", "Number of responses", "int", 2, minimum=1, maximum=5),),
            calibration_not_applicable="No display or physical participant in this test", monitor_capabilities=()))
    prompts = []

    def tui(**options):
        prompts.append(options)
        index = len(prompts)

        async def drive():
            app = PsyCoLabSetupApp(**options)
            async with app.run_test(size=(130, 45)) as pilot:
                await pilot.pause()
                if index > 1:
                    assert isinstance(app.screen, RunResultScreen)
                    assert "completed successfully" in str(app.screen.query_one("#run-result-summary", Static).render())
                    assert app.screen_stack[0].query_one("#participant", Input).value == "S001"
                    assert int(app.config_drafts[("S001", "session_one", "legacy_reference_display")]["trial_count"]) == index
                    if index == 2:
                        app.screen.query_one("#run-repeat", Button).press()
                        await pilot.pause()
                        assert isinstance(app.screen, ExperimentConfigScreen)
                        field = app.screen.query_one("#field-trial-count", Input)
                        assert field.value == "2"
                        field.value = "3"
                        app.open_hub_page("setup")
                    else:
                        app.screen.query_one("#run-select", Button).press()
                        await pilot.pause()
                if index == 3:
                    app.exit(None)
                    return None
                identity = "session_one" if index == 1 else second
                app.query_one("#participant", Input).value = "S001"
                app.query_one("#experiment", Select).value = identity
                await pilot.pause()
                app.config_drafts[("S001", identity, "legacy_reference_display")] = {"trial_count": index + 1}
                request = SetupRequest("S001", "new", identity, "legacy_reference_display", {"trial_count": index + 1},
                                       data_root=str(tmp_path / "data"))
                app.exit(request)
                return request

        return asyncio.run(drive())

    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui", tui)
    assert launcher._main([]) == 0
    assert len(prompts) == 3
    manifests = list((tmp_path / "data").rglob("manifest.json"))
    assert len(manifests) == 2 and len({p.parent for p in manifests}) == 2
    assert sorted(json.loads(path.read_text())["accepted_trials"] for path in manifests) == [2, 3]
    for path in manifests:
        manifest = json.loads(path.read_text())
        assert manifest["status"] == "completed"
        assert all(check.passed for check in validate_run(path.parent))


@pytest.mark.parametrize("status", ["aborted_by_user", "max_trials_reached", "returned", "error", "exception", "interrupt", "system_exit"])
def test_failure_and_incomplete_runs_return_without_success(monkeypatch, tmp_path, status):
    prepare(monkeypatch, tmp_path)
    request = SetupRequest("S001", "new", "example_experiment", "legacy_reference_display", {})
    prompts = []
    def tui(**options):
        prompts.append(options)
        return request if len(prompts) == 1 else None
    def run(*args, **kwargs):
        if status == "system_exit":
            raise SystemExit(0)
        if status in {"exception", "interrupt"}:
            raise KeyboardInterrupt() if status == "interrupt" else RuntimeError("recording failed")
        return SimpleNamespace(status=status, accepted_trials=1, run_directory=tmp_path / "data" / "run",
            trial_log_file=tmp_path / "trials.tsv", manifest_file=tmp_path / "manifest.json")
    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui", tui)
    monkeypatch.setattr("psychophysics_lab.core.runner.run_request", run)
    assert launcher._main([]) == 0
    assert len(prompts) == 2
    assert "successfully" not in prompts[1]["run_outcome"]["summary"]


def test_failed_runner_attaches_exact_partial_record_and_next_run_works(monkeypatch, tmp_path):
    from psychophysics_lab.core.runner import run_request
    from psychophysics_lab.core.synthetic import SimulationRun
    def broken(run):
        run.initialise(expected_trials=2, resolution={"task": "fault injection"})
        run.record(stimulus_condition="x", target_alternative=0, participant_response=0, response_key="F", correct=1)
        raise OSError("storage disconnected")
    spec = experiment(id="broken_session", name="Broken", description="Test", procedure=broken,
        calibration_not_applicable="Software test", monitor_capabilities=())
    monkeypatch.setitem(registry._REGISTRY, spec.id, spec)
    request = SetupRequest("synthetic_1", "new", spec.id, "legacy_reference_display", {})
    with pytest.raises(OSError) as caught:
        run_request(request, repo_root=ROOT, data_root=tmp_path / "data",
                    simulation=SimulationRun(tmp_path / "data", {"seed": 1}, lambda *a: None))
    directory = launcher._failed_run_directory(caught.value)
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["status"] == "error" and manifest["accepted_trials"] == 1
    assert all(c.passed for c in validate_run(directory))
    def recovered(run):
        run.initialise(expected_trials=1, resolution={"task": "recovery integration"})
        run.record(stimulus_condition="x", target_alternative=0, participant_response=0, response_key="F", correct=1)
        run.complete()
    monkeypatch.setitem(registry._REGISTRY, spec.id, replace(spec, procedure=recovered))
    result = run_request(request, repo_root=ROOT, data_root=tmp_path / "data",
        simulation=SimulationRun(tmp_path / "data", {"seed": 1}, lambda *a: None))
    assert result.status == "completed" and result.run_directory != directory
    assert json.loads((directory / "manifest.json").read_text())["status"] == "error"
    assert all(c.passed for c in validate_run(result.run_directory))


def test_audio_cleanup_waits_for_previous_run(monkeypatch):
    import sys
    import threading
    from psychophysics_lab.core import tone
    from psychophysics_lab.core.timeline import Beep
    started, release = threading.Event(), threading.Event()
    def beep(*a):
        started.set()
        assert release.wait(3)
    monkeypatch.setitem(sys.modules, "winsound", SimpleNamespace(Beep=beep))
    tone.request_beep(Beep(440, 5), trigger="accepted_response")
    assert started.wait(2)
    release.set()
    tone.finish_pending_beeps()
    assert not any(t.name == "PsyCoLabBeep" and t.is_alive() for t in threading.enumerate())


@pytest.mark.parametrize("second", ["orientation_task", "probe_above_below"])
def test_two_official_experiments_use_real_virtual_pipeline_without_restarting(monkeypatch, tmp_path, second):
    prepare(monkeypatch, tmp_path)
    from simulations.run import simulate
    outcomes, prompts = [], []
    def run(request, **options):
        result, _ = simulate(data_root=options["data_root"], repo_root=ROOT, seed=123,
            experiment_id=request.experiment_id, values=request.experiment_values, analyse=False)
        outcomes.append(result)
        return result
    requests = iter([SetupRequest("S001", "new", identity, "legacy_reference_display",
                    {"trial_count": 2, "contrast_method": "original"})
                     for identity in ("orientation_task", second)] + [None])
    def tui(**options):
        prompts.append(options)
        return next(requests)
    monkeypatch.setattr("psychophysics_lab.ui.setup.run_setup_tui", tui)
    monkeypatch.setattr("psychophysics_lab.core.runner.run_request", run)
    assert launcher._main([]) == 0 and len(prompts) == 3
    assert len(outcomes) == 2 and outcomes[0].run_directory != outcomes[1].run_directory
    for result in outcomes:
        assert result.status == "completed" and result.accepted_trials == 2
        assert all(check.passed for check in validate_run(result.run_directory))
        assert json.loads(result.manifest_file.read_text())["data_kind"] == "synthetic"
