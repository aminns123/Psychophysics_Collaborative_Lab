"""Above/below line task. Follow the same seven sections as every experiment.

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""


from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, experiment, TrialTimeline,
    Show, Stimulus, CollectResponse, RecordState, UpdateState,
)


# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200),
    ConfigField("fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1),
    ConfigField("stimulus_ms", "Probe time", "int", 200, units="ms", minimum=1),
    ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1),
    ConfigField("response_timeout_ms", "Response timeout", "int", 0, units="ms", minimum=0),
)


RESPONSES = ResponseParadigm(
    "probe_position",
    ("above", "below"),
    ("F", "J"),
)


STIMULUS_SLOTS = {
    "fixation": "fixation",
    "target": "simple_line",
}


STIMULUS_DEFAULTS = {
    "fixation": "fixation_cross",
    "target": "new_probe_vertical_line",
}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(values):
    return [trial % 2 for trial in range(values["trial_count"])]


# 3. PREPARE STIMULI
def prepare_stimuli(target):
    """The vertical placement is the only stimulus change between conditions."""
    return 2.0 if target == 0 else -2.0


# 4. ONE TRIAL
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


# 5. RESPONSES AND ADAPTATION
# Correctness is target/response alternative equality. Count correct answers only;
# no adaptive stimulus change. The loop finishes at the selected trial count.
def update_from_response(state, response):
    return dict(state) | {"correct_count": state["correct_count"] + int(response["correct"])}


# 6. RUN AND FINISH
def procedure(run):
    conditions = make_conditions(run.values)

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
        # 1. CHOOSE A CONDITION; 2. PREPARE ITS STIMULI.
        probe_y = prepare_stimuli(target)

        # 3. PRESENT ONE TRIAL; 4. INTERPRET the named response by index equality.
        # 5. UPDATE correct_count using update_from_response in the trial plan.
        run.play_trial(
            make_trial(probe_y),
            target=target,
            condition="above" if target == 0 else "below",
            measurements={"probe_y_deg": probe_y},
            state=state | {"probe_y_deg": probe_y},
            instructions=f"Above: {run.responses.keys[0]}   Below: {run.responses.keys[1]}",
        )

        state = dict(run.trial_state)
        # 6. CHECK WHETHER TO FINISH: the loop ends after the configured trial count.

    run.complete()


# 7. FRAMEWORK CONNECTION
def definition(identity="new_probe_vertical_line_stimulus",
               stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="Decide whether a white line is above or below a fixation cross.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",

        fields=FIELDS,

        responses=RESPONSES,

        calibration_requirements=("geometry", "timing"),
        monitor_capabilities=("display_binding", "resolution"),

        stimulus_slots=STIMULUS_SLOTS,

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
