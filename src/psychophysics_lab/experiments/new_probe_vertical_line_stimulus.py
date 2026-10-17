"""START HERE: left/right line task. Edit the six labelled scientific sections.

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, experiment, TrialTimeline,
    Show, Stimulus, CollectResponse, RecordState, UpdateState,
)

# 1. STIMULUS: choose a registered stimulus in definition() below.
# 2. CONDITIONS: 0 means left, 1 means right.
def make_trial_order(trial_count):
    return [trial % 2 for trial in range(trial_count)]


# 4. RESPONSE MEANING / NEXT STATE: this function only returns scientific values.
def update_from_response(state, response):
    return dict(state) | {"correct_count": state["correct_count"] + int(response["correct"])}


# 3. CHRONOLOGICAL ACTIONS: duration names refer to validated JSON/TUI settings.
def make_trial(probe_y_deg):
    return TrialTimeline((
        # Show the registered fixation cross
        Show(
            "fixation",
            stimuli=(Stimulus("fixation"),),
            duration="fixation_ms",
        ),

        RecordState("before_probe"),

        # Show fixation AND the white line
        Show(
            "probe",
            stimuli=(
                Stimulus("fixation", x_deg=0, y_deg=0),
                Stimulus("target", x_deg=0, y_deg=probe_y_deg),
            ),
            duration="stimulus_ms",
        ),

        Show("blank", duration="interval_ms"),

        CollectResponse(
            actions=("above", "below"),
            timeout="response_timeout_ms",
        ),

        RecordState("response_received"),
        UpdateState(update_from_response),
    ))


def procedure(run):
    conditions = make_trial_order(run.values["trial_count"])

    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "Is the white line above or below fixation?",
            "condition_order": conditions,
            "above_timeline": make_trial(2.0).resolve(run.values).to_dict(),
            "below_timeline": make_trial(-2.0).resolve(run.values).to_dict(),
            "measurement_units": {
                "probe_y_deg": "degrees",
                "correct_count": "responses",
            },
        },
    )

    state = {"correct_count": 0}

    for target in conditions:

        # 0 = above, 1 = below
        probe_y = 2.0 if target == 0 else -2.0

        run.play_trial(
            make_trial(probe_y),
            target=target,
            condition="above" if target == 0 else "below",
            measurements={"probe_y_deg": probe_y},
            state=state | {"probe_y_deg": probe_y},
            instructions=f"Above: {run.responses.keys[0]}   Below: {run.responses.keys[1]}",
        )

        state = dict(run.trial_state)

    run.complete()

# 5. OPTIONAL ADAPTATION: this beginner task has none.
# See orientation_adaptive.py / orientation_task.py for UpdateAdaptive.
def definition(identity="new_probe_vertical_line_stimulus",
               stimulus="new_probe_vertical_line"):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="Decide whether a white line is above or below a fixation cross.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",

        fields=(
            ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200),
            ConfigField("fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1),
            ConfigField("stimulus_ms", "Probe time", "int", 200, units="ms", minimum=1),
            ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1),
            ConfigField("response_timeout_ms", "Response timeout", "int", 0, units="ms", minimum=0),
        ),

        responses=ResponseParadigm(
            "probe_position",
            ("above", "below"),
            ("F", "J"),
        ),

        calibration_requirements=("geometry", "timing"),
        monitor_capabilities=("display_binding", "resolution"),

        stimulus_slots={
            "fixation": "fixation",
            "target": "simple_line",
        },

        stimulus_defaults={
            "fixation": "fixation_cross",
            "target": stimulus,
        },

        supports_simulation=True,
        source_paths=(
            f"src/psychophysics_lab/experiments/{identity}.py",
        ),
    )


SPEC = definition()
