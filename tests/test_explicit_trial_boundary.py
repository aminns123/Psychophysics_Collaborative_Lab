"""Staged response/update calls reuse the original recorder, including failures."""

from dataclasses import replace
from pathlib import Path
import csv
import json

import pytest
from psychophysics_lab.researcher import (
    Show,
    CollectResponse,
    TrialTimeline,
    UpdateState,
    UpdateAdaptive,
    RecordState,
    ParticipantAbort,
    AdaptiveSelection,
    StaircaseConfig,
)
from psychophysics_lab.experiments._internal import registry
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


def run_case(tmp_path, monkeypatch, procedure, adaptive=False):
    spec = replace(
        registry.get_experiment("example_experiment"),
        id="explicit_boundary_test",
        procedure=procedure,
        source_paths=(),
        default_config="",
        adaptive=AdaptiveSelection("consecutive_up_down") if adaptive else None,
    )
    monkeypatch.setitem(registry._REGISTRY, spec.id, spec)
    return simulate(
        repo_root=ROOT,
        data_root=tmp_path,
        experiment_id=spec.id,
        values={"trial_count": 1},
        analyse=False,
    )[0]


def visible_trial():
    return TrialTimeline(
        (Show("line", slot="target", duration=1), CollectResponse(actions=("left", "right")))
    )


@pytest.mark.parametrize("failure", [None, "error", "abort", "invalid"])
def test_update_and_failure_preserve_exactly_one_response_and_ordered_events(
    tmp_path, monkeypatch, failure
):
    from psychophysics_lab import researcher

    current = [None]
    original_write = researcher.atomic_write_json

    def checked_write(*args, **kwargs):
        assert not getattr(current[0], "_in_trial", False), "Persistence before scientific trial boundary closed"
        return original_write(*args, **kwargs)

    monkeypatch.setattr(researcher, "atomic_write_json", checked_write)
    held = []

    def update(state, response):
        assert response["valid"]
        if failure == "error":
            raise RuntimeError("scientific update failed")
        if failure == "abort":
            raise ParticipantAbort("stopped after response")
        if failure == "invalid":
            return {"value": float("nan")}
        return {"value": 2}

    def procedure(run):
        current[0] = run
        run.initialise(expected_trials=1, resolution={"task": "explicit boundary"})
        with run.trial(visible_trial(), target=0, condition="left", state={"value": 1}) as trial:
            held.append(trial)
            assert trial.response["valid"]
            with pytest.raises(TypeError):
                trial.response["correct"] = False
            trial.apply(UpdateState(update), RecordState("after_update"))
        run.complete()

    if failure in {"error", "invalid"}:
        with pytest.raises((RuntimeError, ValueError)):
            run_case(tmp_path, monkeypatch, procedure)
    else:
        artifacts = run_case(tmp_path, monkeypatch, procedure)
        assert artifacts.status == ("completed" if failure is None else "aborted_by_user")
    trace_path = next(tmp_path.rglob("trial_actions.json"))
    trace = json.loads(trace_path.read_text())["trials"][0]
    rows = list(csv.DictReader((trace_path.parent / "trials.tsv").open(), delimiter="\t"))
    assert len(rows) == 1
    assert [e["action_index"] for e in trace["events"]] == list(range(len(trace["events"])))
    assert [e["kind"] for e in trace["events"]][:3] == ["show", "response", "update_state"]
    assert trace["final_state"] == {"value": 2 if failure is None else 1}
    with pytest.raises(RuntimeError, match="open trial"):
        held[0].apply(RecordState("too_late"))
    assert all(c.passed for c in validate_run(trace_path.parent))


def test_updates_in_make_trial_are_rejected_before_input(tmp_path, monkeypatch):
    def procedure(run):
        run.initialise(expected_trials=1, resolution={"task": "invalid staged plan"})
        plan = TrialTimeline(visible_trial().phases + (UpdateState(lambda s, r: dict(s)),))
        with run.trial(plan, target=0, condition="left"):
            pass

    with pytest.raises(ValueError, match="cannot contain scientific updates"):
        run_case(tmp_path, monkeypatch, procedure)
    assert all(
        not list(csv.DictReader(path.open(), delimiter="\t"))
        for path in tmp_path.rglob("trials.tsv")
    )


def test_failed_adaptive_update_preserves_response_without_inventing_an_update(
    tmp_path, monkeypatch
):
    def fail(state, response, step):
        raise RuntimeError("adaptive update failed")

    def procedure(run):
        algorithm = run.adaptive({1: StaircaseConfig(1, 1, 10)}, 1)
        run.initialise(expected_trials=1, resolution={"task": "failed adaptation"})
        with run.trial(
            visible_trial(), target=0, condition="left", adaptive_record=algorithm
        ) as trial:
            trial.apply(UpdateAdaptive(algorithm, 1, fail))

    with pytest.raises(RuntimeError, match="adaptive update failed"):
        run_case(tmp_path, monkeypatch, procedure, adaptive=True)
    path = next(tmp_path.rglob("trial_actions.json"))
    trace = json.loads(path.read_text())["trials"][0]
    assert trace["status"] == "error"
    assert trace["events"][-1]["status"] == "error"
    assert len(list(csv.DictReader((path.parent / "trials.tsv").open(), delimiter="\t"))) == 1
    assert json.loads((path.parent / "adaptive_session.json").read_text())["total_trials"] == 0
    assert json.loads((path.parent / "manifest.json").read_text())["status"] == "error"
