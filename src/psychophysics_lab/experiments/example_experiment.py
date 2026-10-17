"""WORKED EXAMPLE ONLY: left/right line task (not an empty experiment template).

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""


from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, experiment, TrialTimeline, Show,
    CollectResponse, RecordState, UpdateState,
)


# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200),
    ConfigField("fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1, section="Timing"),
    ConfigField("stimulus_ms", "Line presentation time", "int", 200, units="ms", minimum=1, section="Timing"),
    ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1, section="Timing"),
    ConfigField("response_timeout_ms", "Response timeout (0 waits)", "int", 0, units="ms", minimum=0, section="Timing"),
)


RESPONSES = ResponseParadigm("line_position", ("left", "right"), ("F", "J"))
STIMULUS_SLOTS = {"target": "simple_line"}
STIMULUS_DEFAULTS = {"target": "example_stimulus"}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(values):
    return [trial % 2 for trial in range(values["trial_count"])]


# 3. PREPARE STIMULI
def prepare_stimuli(run, target):
    distance = abs(run.stimulus_parameters()["offset_deg"])
    return run.stimulus_parameters(offset_deg=-distance if target == 0 else distance)


# 4. ONE TRIAL
def make_trial():
    return TrialTimeline((
        Show("fixation", duration="fixation_ms", instructions="+"),
        RecordState("before_line"),
        Show("line", slot="target", duration="stimulus_ms"),
        Show("blank", duration="interval_ms"),
        CollectResponse(actions=("left", "right"), timeout="response_timeout_ms"),
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
    run.initialise(expected_trials=len(conditions), resolution={
        "task": "Report whether the line is left or right.",
        "condition_order": conditions,
        "trial_timeline": make_trial().resolve(run.values).to_dict(),
        "measurement_units": {"line_offset_deg": "degrees", "correct_count": "responses"},
    })
    state = {"correct_count": 0}
    for target in conditions:
        # 1. CHOOSE A CONDITION; 2. PREPARE ITS STIMULI.
        parameters = prepare_stimuli(run, target)
        offset = parameters["offset_deg"]
        # 3. PRESENT ONE TRIAL; 4. INTERPRET the named response by index equality.
        # 5. UPDATE correct_count using update_from_response in the trial plan.
        run.play_trial(
            make_trial(), target=target, condition=offset,
            parameters_by_slot={"target": parameters},
            # 6. EXTRA MEASUREMENTS: finite named scientific values; no file code.
            measurements={"line_offset_deg": offset},
            state=state | {"line_offset_deg": offset},
            instructions=f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}",
        )
        state = dict(run.trial_state)
        # 6. CHECK WHETHER TO FINISH: the loop ends after the configured trial count.
    run.complete()


# 7. FRAMEWORK CONNECTION
def definition(identity="example_experiment", stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity, name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",
        fields=FIELDS,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
