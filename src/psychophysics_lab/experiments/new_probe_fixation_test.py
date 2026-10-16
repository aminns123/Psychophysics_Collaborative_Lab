"""START HERE: left/right line task. Edit the six labelled scientific sections.

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, experiment, TrialTimeline, Show,
    CollectResponse, RecordState, UpdateState,
)


# 1. STIMULUS: choose a registered stimulus in definition() below.
# 2. CONDITIONS: 0 means left, 1 means right.
def make_trial_order(trial_count):
    return [trial % 2 for trial in range(trial_count)]


# 4. RESPONSE MEANING / NEXT STATE: this function only returns scientific values.
def update_from_response(state, response):
    return dict(state) | {"correct_count": state["correct_count"] + int(response["correct"])}


# 3. CHRONOLOGICAL ACTIONS: duration names refer to validated JSON/TUI settings.
TRIAL = TrialTimeline((
    Show("fixation", duration="fixation_ms", instructions="+"),
    RecordState("before_line"),
    Show("line", slot="target", duration="stimulus_ms"),
    Show("blank", duration="interval_ms"),
    CollectResponse(actions=("left", "right"), timeout="response_timeout_ms"),
    RecordState("response_received"),
    UpdateState(update_from_response),
))


def procedure(run):
    conditions = make_trial_order(run.values["trial_count"])
    run.initialise(expected_trials=len(conditions), resolution={
        "task": "Report whether the line is left or right.",
        "condition_order": conditions,
        "trial_timeline": TRIAL.resolve(run.values).to_dict(),
        "measurement_units": {"line_offset_deg": "degrees", "correct_count": "responses"},
    })
    state = {"correct_count": 0}
    for target in conditions:
        distance    = abs(run.stimulus_parameters()["offset_deg"])
        offset      = -distance if target == 0 else distance
        run.play_trial(
            TRIAL, target=target, condition=offset,
            parameters_by_slot={"target": run.stimulus_parameters(offset_deg=offset)},
            # 6. EXTRA MEASUREMENTS: finite named scientific values; no file code.
            measurements={"line_offset_deg": offset},
            state=state | {"line_offset_deg": offset},
            instructions=f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}",
        )
        state = dict(run.trial_state)
    run.complete()


# 5. OPTIONAL ADAPTATION: this beginner task has none.
# See orientation_adaptive.py / orientation_task.py for UpdateAdaptive.
def definition(identity="new_probe_fixation_test", stimulus="example_stimulus"):
    return experiment(
        id=identity, name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",
        fields=(
            ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200),
            ConfigField("fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1, section="Timing"),
            ConfigField("stimulus_ms", "Line presentation time", "int", 200, units="ms", minimum=1, section="Timing"),
            ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1, section="Timing"),
            ConfigField("response_timeout_ms", "Response timeout (0 waits)", "int", 0, units="ms", minimum=0, section="Timing"),
        ),
        responses=ResponseParadigm("line_position", ("left", "right"), ("F", "J")),
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots={"target": "simple_line"},
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
