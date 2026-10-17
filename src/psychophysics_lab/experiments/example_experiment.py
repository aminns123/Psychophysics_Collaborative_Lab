"""WORKED EXAMPLE ONLY: left/right line task (not an empty experiment template).

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""

from psychophysics_lab.researcher import (
    ConfigField,
    ResponseParadigm,
    experiment,
    TrialTimeline,
    Show,
    CollectResponse,
    RecordState,
    UpdateState,
)

# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200),
    ConfigField(
        "fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1, section="Timing"
    ),
    ConfigField(
        "stimulus_ms", "Line presentation time", "int", 200, units="ms", minimum=1, section="Timing"
    ),
    ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1, section="Timing"),
    ConfigField(
        "response_timeout_ms",
        "Response timeout (0 waits)",
        "int",
        0,
        units="ms",
        minimum=0,
        section="Timing",
    ),
)


RESPONSES = ResponseParadigm("line_position", ("left", "right"), ("F", "J"))
STIMULUS_SLOTS = {"target": "simple_line"}
STIMULUS_DEFAULTS = {"target": "example_stimulus"}

PARADIGM = "two_alternative_forced_choice"


SCIENTIFIC_SPEC = {'version': 'example_experiment-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(settings):
    return [{"target": i % 2} for i in range(settings["trial_count"])]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    distance = abs(run.stimulus_parameters()["offset_deg"])
    condition["offset_deg"] = -distance if condition["target"] == 0 else distance
    condition["value"] = condition["offset_deg"]
    return condition


# 3. PREPARE STIMULI
def prepare_stimuli(run, condition, state):
    return {"target": run.stimulus_parameters(offset_deg=condition["offset_deg"])}


# 4. ONE TRIAL
def make_trial(settings, condition):
    return TrialTimeline(
        (
            Show("fixation", duration="fixation_ms", instructions="+"),
            RecordState("before_line"),
            Show("line", slot="target", duration="stimulus_ms"),
            Show("blank", duration="interval_ms"),
            CollectResponse(actions=("left", "right"), timeout="response_timeout_ms"),
            RecordState("response_received"),
        )
    )


# 5. RESPONSES AND ADAPTATION
def interpret_response(condition, response):
    """Both categories score the chosen spatial/property alternative or interval."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def update_from_response(state, response):
    return dict(state) | {"correct_count": state["correct_count"] + int(response["correct"])}


def update_experiment(run, condition, state, response, trial):
    trial.apply(UpdateState(update_from_response))
    return dict(trial.state)


def trial_record(run, condition, state):
    offset = condition["offset_deg"]
    return {
        "state": state | {"line_offset_deg": offset},
        "measurements": {"line_offset_deg": offset},
        "instructions": f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}",
    }


# 6. RUN AND FINISH
def initialise_experiment(run, conditions):
    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "Report whether the line is left or right.",
            "condition_order": [c["target"] for c in conditions],
            "trial_timeline": make_trial(run.values, {"target": 0}).resolve(run.values).to_dict(),
            "measurement_units": {"line_offset_deg": "degrees", "correct_count": "responses"},
        },
    )
    return {"correct_count": 0}


def is_finished(run, conditions, state):
    return run.accepted_trials >= len(conditions)


def finish_experiment(run, conditions, state):
    run.complete()


def procedure(run):
    if not getattr(run, "synthetic", False) and SPEC.acquisition_block_reason:
        raise ValueError(SPEC.acquisition_block_reason)
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    while not is_finished(run, conditions, state):
        condition = choose_condition(run, conditions, state)
        stimuli = prepare_stimuli(run, condition, state)
        with run.trial(
            make_trial(run.values, condition),
            target=condition["target"],
            condition=condition["value"],
            parameters_by_slot=stimuli,
            **trial_record(run, condition, state),
        ) as trial:
            response = interpret_response(condition, trial.response)
            state = update_experiment(run, condition, state, response, trial)
    finish_experiment(run, conditions, state)


# 7. FRAMEWORK CONNECTION
def definition(identity="example_experiment", stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
