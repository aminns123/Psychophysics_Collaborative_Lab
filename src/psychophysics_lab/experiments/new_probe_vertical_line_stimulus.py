"""Above/below line task. Follow the same seven sections as every experiment.

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""

from psychophysics_lab.researcher import (
    ConfigField,
    ResponseParadigm,
    experiment,
    TrialTimeline,
    Show,
    Stimulus,
    CollectResponse,
    RecordState,
    UpdateState,
)

# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200, units="responses"),
    ConfigField(
        "probe_vertical_offset_deg", "Line distance above/below fixation",
        "float", 2.0, minimum=0.000001,
        units="degrees",
        help_text="Positive vertical angular displacement from central fixation; above = +, below = -.",
    ),
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

PARADIGM = "two_alternative_forced_choice"


SCIENTIFIC_SPEC = {'version': 'new_probe_vertical_line_stimulus-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(settings):
    return [
        {"target": i % 2, "probe_y_deg": settings["probe_vertical_offset_deg"] if i % 2 == 0 else -settings["probe_vertical_offset_deg"]}
        for i in range(settings["trial_count"])
    ]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    condition["value"] = run.responses.alternatives[condition["target"]]
    return condition


# 3. PREPARE STIMULI
def prepare_stimuli(run, condition, state):
    return {
        "fixation": run.stimulus_parameters("fixation"),
        "target": run.stimulus_parameters("target"),
    }


# 4. ONE TRIAL
def make_trial(settings, condition):
    return TrialTimeline(
        (
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
                    Stimulus("target", x_deg=0, y_deg=condition["probe_y_deg"]),
                ),
                duration="stimulus_ms",
            ),
            Show("blank", duration="interval_ms"),
            CollectResponse(
                actions=("above", "below"),
                timeout="response_timeout_ms",
            ),
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
    probe_y = condition["probe_y_deg"]
    return {
        "state": state | {"probe_y_deg": probe_y},
        "measurements": {"probe_y_deg": probe_y},
        "instructions": f"Above: {run.responses.keys[0]}   Below: {run.responses.keys[1]}",
    }


# 6. RUN AND FINISH
def initialise_experiment(run, conditions):
    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "Is the white line above or below fixation?",
            "condition_order": [c["target"] for c in conditions],
            "probe_vertical_offset_deg": run.values["probe_vertical_offset_deg"],
            "above_timeline": make_trial(run.values, {"probe_y_deg": run.values["probe_vertical_offset_deg"]})
            .resolve(run.values)
            .to_dict(),
            "below_timeline": make_trial(run.values, {"probe_y_deg": -run.values["probe_vertical_offset_deg"]})
            .resolve(run.values)
            .to_dict(),
            "measurement_units": {
                "probe_y_deg": "degrees",
                "correct_count": "responses",
            },
        },
    )

    return {"correct_count": 0}


def is_finished(run, conditions, state):
    return run.accepted_trials >= len(conditions)


def finish_experiment(run, conditions, state):
    run.complete()


def procedure(run):
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
def definition(identity="new_probe_vertical_line_stimulus", stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="Decide whether a white line is above or below a fixation cross.",
        procedure=procedure,
        default_config=f"configs/experiments/{identity}.json",
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        calibration_requirements=("geometry", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={
            "fixation": "fixation_cross",
            "target": stimulus,
        },
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
