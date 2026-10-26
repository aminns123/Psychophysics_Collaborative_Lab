"""Finite teaching termination is explicit, independently validated science."""
import json
from pathlib import Path
import pytest

from psychophysics_lab.adaptive import AdaptiveRun, StaircaseConfig
from scripts.validate_run import validate_run
from simulations.run import simulate


def test_finite_goal_does_not_fabricate_reversals_or_change_steps():
    config = {0: StaircaseConfig(2, 1, 10)}
    historic = AdaptiveRun(config, 20, starting_values={0: .2})
    finite = AdaptiveRun(config, 20, starting_values={0: .2}, response_goal=4)
    def update(algorithm):
        return lambda step: algorithm.states[0].last_value * (.8 if int(step) == 0 else 1.25 if int(step) == 1 else 1)
    for answer in (True, True, False, True):
        assert finite.respond(0, answer, update(finite)) == historic.respond(0, answer, update(historic))
    assert finite.states == historic.states
    assert finite.status == "completed" and historic.status == "running"
    assert not finite.states[0].complete
    assert "response_goal" not in historic.snapshot()
    with pytest.raises(RuntimeError, match="ended"):
        finite.respond(0, True, update(finite))


@pytest.mark.parametrize("goal", [0, True, 21])
def test_finite_goal_must_be_an_integer_within_safety_ceiling(goal):
    with pytest.raises(ValueError):
        AdaptiveRun({0: StaircaseConfig(2, 1, 10)}, 20, response_goal=goal)


def test_saved_goal_cannot_replace_the_configured_teaching_plan(tmp_path):
    artifact, _ = simulate(repo_root=Path(__file__).resolve().parents[1], data_root=tmp_path,
                           experiment_id="example_experiment", analyse=False,
                           values={"contrast_method": "adaptive", "trial_count": 4})
    assert not [c for c in validate_run(artifact.run_directory) if not c.passed]
    for filename in ("adaptive_session.json", "manifest.json"):
        path = artifact.run_directory / filename
        document = json.loads(path.read_text())
        state = document if filename == "adaptive_session.json" else document["adaptive_session"]
        state["response_goal"] = 3
        path.write_text(json.dumps(document), encoding="utf-8")
    status = next(c for c in validate_run(artifact.run_directory)
                  if c.name == "Final lifecycle status consistency")
    assert not status.passed and "configured teaching plan" in status.detail
