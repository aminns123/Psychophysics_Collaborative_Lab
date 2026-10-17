"""Is the line above or below the central fixation cross?

This Python file replaces the built-in JSON procedure without changing its
scientific choices. The old design and loader remain internal compatibility
resources for saved data and independently tested historical designs.
Target 0 = above (+2 degrees), 1 = below (-2 degrees); default keys F/J.
Correctness is equality of the target/response alternative indices. Conditions
are balanced then shuffled using random_seed. Stop at trial_count responses.
No adaptation or sound. All durations are milliseconds; 0 timeout waits for a key.
Stimulus defaults/maths are FixationCross and VerticalLineProbe in the library.
RunContext executes the same procedure for live and virtual response sources.
"""

import random
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
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=1000),
    ConfigField("random_seed", "Condition seed", "int", 123, minimum=0),
    ConfigField(
        "fixation_ms",
        "Fixation time",
        "int",
        500,
        minimum=1,
        maximum=3600000,
        units="ms",
        section="Timing",
    ),
    ConfigField(
        "stimulus_ms",
        "Probe time",
        "int",
        200,
        minimum=1,
        maximum=3600000,
        units="ms",
        section="Timing",
    ),
    ConfigField(
        "interval_ms",
        "Blank time",
        "int",
        150,
        minimum=1,
        maximum=3600000,
        units="ms",
        section="Timing",
    ),
    ConfigField(
        "response_timeout_ms",
        "Response timeout (0 means unlimited)",
        "int",
        0,
        minimum=0,
        maximum=3600000,
        units="ms",
        section="Timing",
    ),
)


RESPONSES = ResponseParadigm("probe_above_below", ("above", "below"), ("F", "J"))
STIMULUS_SLOTS = {"fixation": "fixation", "probe": "line"}
STIMULUS_DEFAULTS = {"fixation": "fixation_cross", "probe": "vertical_line_probe"}

PARADIGM = "two_alternative_forced_choice"


SCIENTIFIC_SPEC = {'version': 'probe_above_below-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(settings):
    order = [i % 2 for i in range(settings["trial_count"])]
    random.Random(settings["random_seed"]).shuffle(order)
    return [{"target": target, "probe_y_deg": 2.0 if target == 0 else -2.0} for target in order]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    condition["value"] = run.responses.alternatives[condition["target"]]
    return condition


# 3. PREPARE STIMULI
def prepare_stimuli(run, condition, state):
    return {
        "fixation": run.stimulus_parameters("fixation"),
        "probe": run.stimulus_parameters("probe"),
    }


# 4. ONE TRIAL
def make_trial(settings, condition):
    return TrialTimeline(
        (
            Show("fixation", stimuli=(Stimulus("fixation"),), duration="fixation_ms"),
            RecordState("before_probe"),
            Show(
                "probe",
                stimuli=(Stimulus("fixation"), Stimulus("probe", y_deg=condition["probe_y_deg"])),
                duration="stimulus_ms",
            ),
            Show("blank", duration="interval_ms"),
            CollectResponse(actions=("above", "below"), timeout="response_timeout_ms"),
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
    trial.apply(UpdateState(update_from_response, name="update_correct_count"))
    return dict(trial.state)


def trial_record(run, condition, state):
    probe_y = condition["probe_y_deg"]
    return {
        "state": dict(state),
        "measurements": {"probe_x_deg": 0.0, "probe_y_deg": probe_y},
        "instructions": "  ".join(
            f"{alt}: {key}" for alt, key in zip(run.responses.alternatives, run.responses.keys)
        ),
    }


# 6. RUN AND FINISH
def initialise_experiment(run, conditions):
    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "A white vertical line is shown above or below a central fixation cross.",
            "condition_order": [run.responses.alternatives[c["target"]] for c in conditions],
            "trial_order_seed": run.values["random_seed"],
            "above_timeline": make_trial(run.values, {"probe_y_deg": 2.0})
            .resolve(run.values)
            .to_dict(),
            "below_timeline": make_trial(run.values, {"probe_y_deg": -2.0})
            .resolve(run.values)
            .to_dict(),
            "stimulus_slots": run.stimulus_snapshots,
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
def definition(identity="probe_above_below"):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="A white vertical line is shown above or below a central fixation cross.",
        procedure=procedure,
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        supports_simulation=True,
        source_paths=("src/psychophysics_lab/experiments/probe_above_below.py",),
    )


SPEC = definition()
