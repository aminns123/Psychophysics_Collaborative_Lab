"""Scientific actions tested through the real runner and interrupted backend."""
from dataclasses import replace
import json
from pathlib import Path
import pytest

from psychophysics_lab.researcher import (
    TrialTimeline, Show, Stimulus, CollectResponse, RecordState, UpdateState,
    UpdateAdaptive, AdaptiveSelection, StaircaseConfig, Step, ParticipantAbort,
)
from psychophysics_lab.experiments import registry
from psychophysics_lab.core.presentation import Response
from psychophysics_lab.core.timeline import scientific_snapshot
from psychophysics_lab.core.trial_execution import execute_timeline
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def run_actions(tmp_path, monkeypatch, build, *, count=1, adaptive=False):
    def procedure(run):
        run.initialise(expected_trials=count, resolution={"task": "scientific action regression"})
        for _ in range(count):
            timeline, state = build(run)
            run.play_trial(timeline, target=0, condition="left", state=state)
        run.complete()
    spec = replace(registry.get_experiment("example_experiment"), id="action_regression",
                   procedure=procedure, source_paths=(),
                   adaptive=AdaptiveSelection("consecutive_up_down") if adaptive else None)
    monkeypatch.setitem(registry._REGISTRY, spec.id, spec)
    return simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=spec.id,
                    values={"trial_count": count}, analyse=False)[0]


def read_trace(root):
    return json.loads(next(root.rglob("trial_actions.json")).read_text())


def test_snapshot_and_update_order_immutability_and_no_timed_io(tmp_path, monkeypatch):
    from psychophysics_lab.core import trial_execution
    from psychophysics_lab import researcher
    original = researcher.atomic_write_json
    running = False
    execute = trial_execution.execute_timeline
    def observe(*args, **kwargs):
        nonlocal running
        running = True
        try:
            return execute(*args, **kwargs)
        finally:
            running = False
    def write(*args, **kwargs):
        assert not running, "Persistence inside timed action loop"
        return original(*args, **kwargs)
    monkeypatch.setattr(trial_execution, "execute_timeline", observe)
    monkeypatch.setattr(researcher, "atomic_write_json", write)
    original_state = {"contrast": .5, "nested": {"history": [1]}}
    def update(state, response):
        assert response["valid"] and response["meaning"] in ("left", "right")
        with pytest.raises(TypeError):
            state["nested"]["history"][0] = 9
        return dict(state) | {"contrast": .25}
    def build(run):
        return TrialTimeline((
            Show("line", slot="target", duration="stimulus_ms"),
            RecordState("before", fields=("contrast",)),
            CollectResponse(actions=("left", "right")),
            UpdateState(update),
            RecordState("after"),
        )), original_state
    result = run_actions(tmp_path, monkeypatch, build)
    assert all(check.passed for check in validate_run(result.run_directory))
    trace = read_trace(tmp_path)["trials"][0]
    assert [e["kind"] for e in trace["events"]] == [
        "show", "record_state", "response", "update_state", "record_state"]
    assert trace["events"][1]["snapshot"]["state"] == {"contrast": .5}
    assert trace["events"][-1]["snapshot"]["state"]["contrast"] == .25
    assert original_state["contrast"] == .5
    assert trace["plan"]["phases"][0]["duration_ms"] == 200
    assert "software_onset_s" not in trace["events"][0]
    assert "virtual_onset_ms" in trace["events"][0]


@pytest.mark.parametrize("after_response", [False, True])
@pytest.mark.parametrize("failure", ["abort", "invalid", "exception"])
def test_partial_events_and_response_preserved(tmp_path, monkeypatch, after_response, failure):
    def change(state, response):
        if failure == "abort":
            raise ParticipantAbort("stopped")
        if failure == "invalid":
            return {"bad": float("nan")}
        raise RuntimeError("scientific callback failed")
    def build(run):
        phases = [Show("line", slot="target", duration=1)]
        if after_response:
            phases.append(CollectResponse(actions=("left", "right")))
        phases.append(UpdateState(change))
        if not after_response:
            phases.append(CollectResponse(actions=("left", "right")))
        return TrialTimeline(tuple(phases)), {"value": 1}
    if failure == "abort":
        result = run_actions(tmp_path, monkeypatch, build)
        assert result.status == "aborted_by_user"
    else:
        with pytest.raises((ValueError, RuntimeError)):
            run_actions(tmp_path, monkeypatch, build)
    trace = read_trace(tmp_path)["trials"][0]
    assert trace["status"] == ("aborted" if failure == "abort" else "error")
    assert trace["events"][-1]["kind"] == "update_state"
    assert trace["final_state"] == {"value": 1}
    manifest = json.loads(next(tmp_path.rglob("manifest.json")).read_text())
    assert manifest["accepted_trials"] == int(after_response)
    checks = validate_run(next(tmp_path.rglob("manifest.json")).parent)
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]


def test_adaptive_action_records_registered_algorithm_history(tmp_path, monkeypatch):
    def update(state, response, step):
        return state["contrast"] * (.5 if step == Step.DOWN else 2 if step == Step.UP else 1)
    def build(run):
        algorithm = run.adaptive({0: StaircaseConfig(1, 1, 20)}, 2)
        return TrialTimeline((
            Show("line", slot="target", duration=1),
            CollectResponse(actions=("left", "right")),
            UpdateAdaptive(algorithm, 0, update, state_key="contrast"),
            RecordState("adapted"),
        )), {"contrast": .5}
    result = run_actions(tmp_path, monkeypatch, build, adaptive=True)
    trace = read_trace(tmp_path)["trials"][0]
    event = trace["events"][2]
    assert event["adaptive_before"]["total_trials"] == 0
    assert event["adaptive_after"]["total_trials"] == 1
    history = json.loads((result.run_directory / "adaptive_history.json").read_text())
    assert history["updates"][0]["trial_index"] == 1
    assert history["updates"][0]["state"] == event["adaptive_after"]


def test_nonvisual_actions_never_redraw_and_positions_preserve_order():
    from psychophysics_lab.core.presentation import placement_pixels
    from types import SimpleNamespace
    class Backend:
        synthetic = False
        shown = []
        def play_phase(self, phase, event, **kwargs):
            self.shown.append(phase.name)
            return Response(0, "F", .2) if phase.kind == "response" else None
    backend = Backend()
    timeline = TrialTimeline((
        Show("pair", duration=50, stimuli=(Stimulus("first", -2, 1), Stimulus("second", 2, -1))),
        RecordState("capture"), CollectResponse(actions=("left", "right")),
        RecordState("after"),
    )).validate_slots(("first", "second"))
    events = []
    execute_timeline(timeline, backend, events, lambda *args: None)
    assert backend.shown == ["pair", "answer"]
    assert len(events) == 4
    assert timeline.to_dict()["phases"][0]["stimuli"][1]["slot"] == "second"
    profile = SimpleNamespace(viewing_distance_m=.6, physical_width_m=.5, physical_height_m=.3)
    left = placement_pixels(profile, (1000, 600), (100, 100), Stimulus("first", -2, 0))
    right = placement_pixels(profile, (1000, 600), (100, 100), Stimulus("second", 2, 0))
    assert left[0] < 450 < right[0]
    with pytest.raises(ValueError, match="fit"):
        placement_pixels(profile, (1000, 600), (100, 100), Stimulus("first", 80, 0))


def test_callback_failure_events_are_retained_by_live_traversal():
    class Backend:
        synthetic = False
        def play_phase(self, phase, event, **kwargs):
            event["software_onset_s"] = 10.
            raise ParticipantAbort("Escape")
    events = []
    with pytest.raises(ParticipantAbort):
        execute_timeline(TrialTimeline((Show("line", slot="target", duration=5),
                         CollectResponse(actions=("left", "right")))),
                         Backend(), events, lambda *args: None)
    assert len(events) == 1 and events[0]["status"] == "aborted"
    assert events[0]["software_onset_s"] == 10.
    assert "software_finished_s" in events[0]


def test_invalid_state_meanings_duration_and_missing_fields_fail(tmp_path, monkeypatch):
    for bad in ({"n": float("inf")}, {1: "key"}, {"obj": object()}):
        with pytest.raises(ValueError):
            scientific_snapshot(bad)
    with pytest.raises(ValueError, match="Unknown"):
        TrialTimeline((Show("line", slot="target", duration="missing"),
                       CollectResponse(actions=("left", "right")))).resolve({})
    def build(run):
        return TrialTimeline((Show("line", slot="target", duration=1),
                              CollectResponse(actions=("yes", "no")))), {}
    with pytest.raises(ValueError, match="meanings"):
        run_actions(tmp_path, monkeypatch, build)


def test_timeout_is_not_an_accepted_response(tmp_path, monkeypatch):
    def build(run):
        return TrialTimeline((Show("line", slot="target", duration=1),
                              CollectResponse(actions=("left", "right"), timeout=1))), {}
    with pytest.raises(TimeoutError):
        run_actions(tmp_path, monkeypatch, build)
    trace = read_trace(tmp_path)["trials"][0]
    assert trace["events"][-1]["status"] == "error"
    assert json.loads(next(tmp_path.rglob("manifest.json")).read_text())["accepted_trials"] == 0
