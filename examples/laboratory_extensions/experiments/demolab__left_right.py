"""LABORATORY EXAMPLE: left/right line task in an independent source folder.

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""

from psychophysics_lab.researcher import (
    ConfigField,
    ResponseParadigm,
    experiment,
    TrialTimeline,
    WaitForKey,
    legacy_trial_factory,
    Show,
    Beep,
    CollectResponse,
    RecordState,
    UpdateState,
)

# PART A1 — EXPERIMENTAL CHOICES
# Question: which side contains the line? Targets alternate left/right; no staircase.
# Timing is requested ms, displacement is degrees, commands are digital intensity.
# Selected values override Python defaults; changing this source requires Test → Ready.
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
CALIBRATION_REQUIREMENTS = ("geometry",)
MONITOR_CAPABILITIES = ("display_binding", "resolution")
STIMULUS_SLOTS = {"target": "simple_line"}
STIMULUS_DEFAULTS = {"target": "demolab__line"}

PARADIGM = "two_alternative_forced_choice"

# A pure, session-only fixation; trial slots and their defaults stay unchanged.
STIMULUS_SLOTS["ready_fixation"] = "fixation"
STIMULUS_DEFAULTS["ready_fixation"] = "fixation_cross"


# Session opening — once, before scientific responses
# Edit the Python list directly. SESSION_START = [] disables the opening.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


# Chronological events — repeated for the currently selected target
# One fresh flat event list per selected condition; effective strengths are prepared below.


def fixation_events(settings):
    """A small reusable list; composition stays ordinary Python."""
    return [Show("fixation", duration="fixation_ms", instructions="+")]


def trial_events(settings, condition):
    return fixation_events(settings) + [
        RecordState('before_line'),
        Show('line', slot='target', duration='stimulus_ms', beep=None),  # Optional: Beep(550, 35).
        Show('blank', duration='interval_ms'),
        CollectResponse(
            actions=('left', 'right'),
            timeout='response_timeout_ms',
            beep=None,
        ),  # Optional accepted answer: Beep(750, 35).
        RecordState('response_received'),
    ]


def prepare_stimuli(run, condition, state):
    return {"target": run.stimulus_parameters(offset_deg=condition["offset_deg"])}


# Requested geometry saved in the existing per-trial journal; canonical columns stay unchanged.
MEASUREMENT_UNITS = {"line_offset_deg": "degrees"}
STATE_UNITS = {"correct_count": "responses"}


def trial_measurements(settings, condition):
    return {"line_offset_deg": condition["offset_deg"]}


def response_instructions(responses):
    return f"Left: {responses.keys[0]}   Right: {responses.keys[1]}"


# PART A2 — SCIENTIFIC METHODS
# Scheduled rows encode target alternatives, not scientific factors or tracks.
# The stimulus preset supplies displacement magnitude; choose_condition supplies its sign.


SCIENTIFIC_SPEC = {'version': 'demolab__left_right-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


def make_conditions(settings):
    return [{"target": i % 2} for i in range(settings["trial_count"])]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    distance = abs(run.stimulus_parameters()["offset_deg"])
    condition["offset_deg"] = -distance if condition["target"] == 0 else distance
    condition["value"] = condition["offset_deg"]
    return condition


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


# Stop after the scheduled accepted responses; no threshold estimator.


def is_finished(run, conditions, state):
    return run.accepted_trials >= len(conditions)


def finish_experiment(run, conditions, state):
    run.complete()


def initial_state():
    return {"correct_count": 0}


def scientific_resolution(run, conditions):
    return {
        "task": "Report whether the line is left or right.",
        "condition_order": [c["target"] for c in conditions],
        "trial_timeline": TrialTimeline(trial_events(run.values, {"target": 0})).resolve(run.values).to_dict(),
        "measurement_units": MEASUREMENT_UNITS | STATE_UNITS,
    }


# PART B — FRAMEWORK INTEGRATION
# Connect the science above to the same canonical RunContext; no new execution engine.

def initialise_experiment(run, conditions):
    run.initialise(expected_trials=len(conditions), resolution=scientific_resolution(run, conditions))
    return initial_state()


def trial_record(run, condition, state):
    offset = condition["offset_deg"]
    return {
        "state": state | {"line_offset_deg": offset},
        "measurements": trial_measurements(run.values, condition),
        "instructions": response_instructions(run.responses),
    }


def procedure(run):
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    while not is_finished(run, conditions, state):
        condition = choose_condition(run, conditions, state)
        stimuli = prepare_stimuli(run, condition, state)
        with run.trial(
            trial_events(run.values, condition),
            target=condition["target"],
            condition=condition["value"],
            parameters_by_slot=stimuli,
            **trial_record(run, condition, state),
        ) as trial:
            response = interpret_response(condition, trial.response)
            state = update_experiment(run, condition, state, response, trial)
    finish_experiment(run, conditions, state)


# Compatibility and registration
# Central compatibility for callers expecting make_trial(...).resolve(...).
make_trial = legacy_trial_factory(trial_events)


def definition(identity="demolab__left_right", stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        session_start=SESSION_START,
        default_config="presets/left_right.json",
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        calibration_requirements=CALIBRATION_REQUIREMENTS,
        monitor_capabilities=MONITOR_CAPABILITIES,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS | {"target": stimulus},
        supports_simulation=True,
        source_paths=(f"experiments/{identity}.py",),
    )


SPEC = definition()
