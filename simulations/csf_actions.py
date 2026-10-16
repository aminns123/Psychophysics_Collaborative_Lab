"""CSF state/action validation ONLY. Never registered for human acquisition.

Run: python -m simulations.csf_actions --output NEW_DIRECTORY
Replays fixed responses through the public actions and compares captured legacy
scientific traces. NO pixels, photons, audio, key events or CSF acquisition occur.
"""
from contextlib import redirect_stdout
import csv
from dataclasses import replace
import io
import json
from pathlib import Path
import random
from types import SimpleNamespace

from psychophysics_lab.researcher import (
    RunContext, experiment, TrialTimeline, Show, CollectResponse, RecordState,
    UpdateAdaptive, AdaptiveSelection, StaircaseConfig, Step, LEFT_RIGHT,
)
from psychophysics_lab.core.presentation import Response
from psychophysics_lab.core.trial_execution import VirtualPresentation
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
from psychophysics_lab.stimuli.registry import get_stimulus
from psychophysics_lab.paths import find_repo_root
from Events.display_contrast import normalized_display_contrast, display_contrast_to_screen_intensity

BASIS = "DEVELOPMENT STATE REPLAY ONLY: no pixels, hardware, actual phase timing or human data"
PATTERN = (True, True, False, True, False, False)


class StateReplay(VirtualPresentation):
    basis = BASIS

    def prepare(self, timeline, resolved):
        # Deliberately no substitute Gabor/line raster for the CSF shader.
        pass


def capture_legacy(case, directory):
    """Fixture capture through the ACTUAL legacy event adapter; not an oracle rewrite."""
    from Events.adaptive_session import LegacyStaircaseSession
    from Events.adaptiveMethods import Trials_read_write_staircase_conditions
    import Functions.functionsForUse as files
    directory.mkdir(parents=True, exist_ok=False)
    conditions, parameters, responses = [directory / n for n in ("conditions.json", "parameters.json", "legacy_response.txt")]
    n = len(case["conditions"])
    files.create_JSON(conditions, {
        "condition_list": case["conditions"], "staircase_Identities": list(range(n)),
        "staircase_intensity_active": [case["start"]] * n,
        "reversal_termination": case["limits"], "probe_Alternative_Choice": [0] * n,
        "staircase_Identity_active": [0], "weber_contrast_active": [0.] * n,
        "stimulus_choice_active": [10], "terminate_bool": [0], "total_Reversals": [0] * n,
        "2AFC_choice": [10, 20],
    })
    files.create_JSON(parameters, {
        "n_dw": case["down"], "n_up": case["up"], "logUNIT_UP": case["step_up"],
        "logUNIT_DW": case["step_down"], "background_intensity": case["background"],
        "max_intensity": case["maximum"], "initial_one_down_limit": case["initial"],
    })
    files.create_Text_columns(responses, list(range(6)))
    session = LegacyStaircaseSession(conditions, parameters, responses, case["ceiling"], synthetic=True)
    logger = session.logger(SimpleNamespace(trials=[], exit=lambda: None))
    rng = random.Random(case["seed"])
    snapshots = []
    with redirect_stdout(io.StringIO()):
        while session.run.status == "running":
            index = session.run.total_trials
            target = index % 2
            def trial(name):
                obj = session.attach(Trials_read_write_staircase_conditions(
                    name, [], 250, [10 if target == 0 else 20, 0],
                    conditions, parameters, responses, keys=["LEFT", "RIGHT"]))
                obj.choose, obj.feedback_enabled = rng.choice, False
                return obj
            logger("TRIAL", index, trial("new_condition"), [])
            selected = files.read_JSON(conditions)["staircase_Identity_active"][0]
            correct = PATTERN[session.run.states[selected].trial_count % len(PATTERN)]
            answer = target if correct else 1 - target
            key = LEFT_RIGHT.keys[answer]
            response = trial("response")
            logger("TRIAL", index, response, [])
            logger("KEY", index, response, [key, key])
            snapshots.append(session.run.snapshot())
    with (directory / "trials.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {"case": case, "rows": rows, "snapshots": snapshots,
            "legacy_baseline": "ad7c132", "scope": "condition/response/adaptive state, not presentation equivalence"}


def replay(fixture, directory):
    """Use RunContext and registered adaptive mechanics; no legacy event adapter."""
    case = fixture["case"]
    directory.mkdir(parents=True, exist_ok=False)
    spec = experiment(id="csf_state_validation", name="CSF state validation",
        description=BASIS, procedure=lambda run: None, responses=LEFT_RIGHT,
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        adaptive=AdaptiveSelection("consecutive_up_down"),
        stimulus_slots={"target": "csf"}, stimulus_defaults={"target": "legacy_csf"})
    selected = snapshot(document_for(get_stimulus("legacy_csf"), {
        "number_conditions": len(case["conditions"]), "condition_unit": "legacy_shader_radians",
        "condition_values": ",".join(str(v) for v in case["conditions"]),
    }), file_identity="validation-fixture")
    backend = StateReplay(Response(0, "LEFT", .25))
    run = RunContext({}, load_monitor_profiles(find_repo_root())["legacy_reference_display"],
                     spec, directory, synthetic=True, data_kind="synthetic",
                     stimulus_snapshots={"target": selected}, virtual_presentation=backend)
    run.initialise(expected_trials=len(fixture["rows"]), resolution={"basis": BASIS, "case": case})
    adaptive = run.adaptive({i: StaircaseConfig(case["down"], case["up"], limit, case["initial"])
                             for i, limit in enumerate(case["limits"])}, case["ceiling"])
    intensities = {i: case["start"] for i in range(len(case["conditions"]))}
    rng = random.Random(case["seed"])
    rows, snapshots = [], []
    def next_intensity(state, response, step):
        # Scientific numeric rule, independent of the legacy event/file adapter.
        contrast = normalized_display_contrast(state["intensity"],
            background_intensity=case["background"], maximum_intensity=case["maximum"])
        factor = 10 ** (-case["step_down"] if step == Step.DOWN else case["step_up"] if step == Step.UP else 0)
        return max(case["background"], display_contrast_to_screen_intensity(contrast * factor,
            background_intensity=case["background"], maximum_intensity=case["maximum"]))
    try:
        while adaptive.status == "running":
            index = adaptive.total_trials
            target = index % 2
            identity = adaptive.select(rng.choice)
            previous = adaptive.snapshot()["staircases"][str(identity)]
            correct = PATTERN[previous["trial_count"] % len(PATTERN)]
            answer = target if correct else 1 - target
            backend.response = Response(answer, LEFT_RIGHT.keys[answer], .25)
            before = intensities[identity]
            decision = adaptive.expected_step(identity, correct)
            trial = TrialTimeline((
                Show("fixation", duration=250, instructions="+"),
                RecordState("selected"),
                Show("new_condition", duration=250),
                Show("stimuli", slot="target", duration=200),
                Show("interval", duration=250),
                CollectResponse(actions=("left", "right"), name="response"),
                UpdateAdaptive(adaptive, identity, next_intensity, state_key="intensity"),
                RecordState("updated"),
            ))
            run.play_trial(trial, target=target, condition=case["conditions"][identity],
                           state={"identity": identity, "intensity": before})
            after = intensities[identity] = run.trial_state["intensity"]
            current = adaptive.snapshot()["staircases"][str(identity)]
            contrast = lambda value: normalized_display_contrast(value,
                background_intensity=case["background"], maximum_intensity=case["maximum"])
            rows.append({
                "trial_index": index + 1, "staircase_id": identity,
                "staircase_trial_index": current["trial_count"],
                "stimulus_condition": case["conditions"][identity],
                "target_alternative": target, "participant_response": answer,
                "correct": int(correct), "presented_display_contrast": contrast(before),
                "presented_screen_intensity": before,
                "step": {Step.DOWN: "down", Step.UP: "up", Step.HOLD: "hold"}[decision],
                "reversal": int(current["reversal_count"] > previous["reversal_count"]),
                "reversal_count": current["reversal_count"],
                "next_display_contrast": contrast(after), "next_screen_intensity": after,
                "staircase_complete": int(current["complete"]), "run_status": adaptive.status,
            })
            snapshots.append(adaptive.snapshot())
        run.complete()
    finally:
        run.close()
    return rows, snapshots


def compare(fixture, rows, snapshots):
    import math
    if len(rows) != len(fixture["rows"]) or snapshots != fixture["snapshots"]:
        raise AssertionError("CSF response count or adaptive state diverged from the legacy fixture.")
    for actual, expected in zip(rows, fixture["rows"]):
        for key, value in actual.items():
            if isinstance(value, (int, float)):
                if not math.isclose(value, float(expected[key]), rel_tol=1e-12, abs_tol=1e-12):
                    raise AssertionError(f"CSF {key} differs: {value} vs {expected[key]}")
            elif value != expected[key]:
                raise AssertionError(f"CSF {key} differs: {value} vs {expected[key]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=BASIS)
    parser.add_argument("--output", type=Path, required=True, help="New diagnostic output directory; never overwrite")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixtures = find_repo_root() / "tests/fixtures/csf_actions"
    for path in sorted(fixtures.glob("*.json")):
        fixture = json.loads(path.read_text())
        rows, snapshots = replay(fixture, args.output / path.stem)
        compare(fixture, rows, snapshots)
        print(f"PASS {path.stem}: {len(rows)} responses, exact adaptive snapshots, numeric tolerance 1e-12")
    print(BASIS)
    print("CSF acquisition migration remains incomplete; the existing CSF remains the default.")


if __name__ == "__main__":
    main()
