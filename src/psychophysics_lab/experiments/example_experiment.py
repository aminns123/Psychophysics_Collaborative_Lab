"""WORKED EXAMPLE ONLY: left/right line task (not an empty experiment template).

The companion JSON supplies settings; the TUI can override them for a run.
PsyCoLab owns geometry, display, keys, validation and all saving.
"""

from psychophysics_lab.methods.contrast import run_contrast_experiment
from psychophysics_lab.methods.teaching import (
    teaching_method_fields, teaching_adaptive_fields, fixed_teaching_schedule,
    constant_teaching_method, OriginalTeachingMethod, TeachingAdaptiveMethod,
    review_teaching_adaptive,
)

from psychophysics_lab.researcher import (
    ConfigField,
    ResponseParadigm,
    AdaptiveSelection,
    experiment,
    TrialTimeline,
    WaitForKey,
    legacy_trial_factory,
    Show,
    CollectResponse,
    RecordState,
    UpdateState,
)

# 1. PARAMETERS
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=200, help_text='Accepted-response goal for the finite teaching/original path; fixed mode derives its own count from levels, conditions and repetitions.'),
    ConfigField(
        "fixation_ms", "Fixation time", "int", 500, units="ms", minimum=1, section="Timing",
        help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.',
    ),
    ConfigField(
        "stimulus_ms", "Line presentation time", "int", 200, units="ms", minimum=1, section="Timing",
        help_text='Scheduled stimulus exposure duration in milliseconds; changing it changes the trial timeline, not measured display qualification.',
    ),
    ConfigField("interval_ms", "Blank time", "int", 150, units="ms", minimum=1, section="Timing", help_text='Scheduled gap between the declared stimulus intervals, in milliseconds; only timeline phases using this setting are affected.'),
    ConfigField(
        "response_timeout_ms",
        "Response timeout (0 waits)",
        "int",
        0,
        units="ms",
        minimum=0,
        section="Timing",
        help_text='Time allowed for a valid response in milliseconds; zero waits without a timeout. Timeout is an incomplete response, not an invented answer.',
    ),
)


FIELDS += teaching_method_fields(
    default="original", strengths="0,0.1,0.2",
    label="Line digital increment above grey background",
) + teaching_adaptive_fields()


RESPONSES = ResponseParadigm("line_position", ("left", "right"), ("F", "J"))
STIMULUS_SLOTS = {"target": "simple_line"}
STIMULUS_DEFAULTS = {"target": "example_stimulus"}

PARADIGM = "two_alternative_forced_choice"

# A pure, session-only fixation; trial slots and their defaults stay unchanged.
STIMULUS_SLOTS["ready_fixation"] = "fixation"
STIMULUS_DEFAULTS["ready_fixation"] = "fixation_cross"


# 2. SESSION START — ONCE
# Edit the Python list directly. SESSION_START = [] disables the opening.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


# 3. TRIAL EVENTS — REPEATED
# One fresh flat event list per selected condition; effective strengths are prepared below.


def trial_events(settings, condition):
    """Fixation -> line -> blank -> left/right answer; markers only observe state."""
    return [
        Show('fixation', duration='fixation_ms', instructions='+'),
        RecordState('before_line'),
        Show('line', slot='target', duration='stimulus_ms'),
        Show('blank', duration='interval_ms'),
        CollectResponse(actions=('left', 'right'), timeout='response_timeout_ms'),
        RecordState('response_received'),
    ]


def prepare_stimuli(run, condition, state):
    return {"target": run.stimulus_parameters(offset_deg=condition["offset_deg"])}


def prepare_method_stimuli(run, condition, state):
    if run.values.get("contrast_method", "original") == "original":
        return prepare_stimuli(run, condition, state)
    # The selected method owns increment above the stimulus's grey 0.5 command.
    return {"target": run.stimulus_parameters(
        offset_deg=condition["offset_deg"], intensity=0.5 + condition["contrast"]
    )}


# 4. SCIENTIFIC RULES — CONDITIONS AND UPDATES


SCIENTIFIC_SPEC = {'version': 'example_experiment-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


ADAPTIVE_RULE = AdaptiveSelection('consecutive_up_down',
    controls=('n_down','n_up','down_factor','up_factor','max_trials'))


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


def initialise_experiment(run, conditions):
    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "Report whether the line is left or right.",
            "condition_order": [c["target"] for c in conditions],
            "trial_timeline": TrialTimeline(trial_events(run.values, {"target": 0})).resolve(run.values).to_dict(),
            "measurement_units": {"line_offset_deg": "degrees", "correct_count": "responses"},
        },
    )
    return {"correct_count": 0}


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(settings, seed, maximum=0.5, condition="line_side")


def prepare_selection(run, condition):
    if "offset_deg" not in condition:
        distance = abs(run.stimulus_parameters()["offset_deg"])
        condition["offset_deg"] = -distance if condition["target"] == 0 else distance


def validate_method_settings(values):
    method = values.get("contrast_method", "original")
    if method == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except ValueError as exc:
            yield str(exc)
    elif method == "adaptive":
        if not 0 <= values["starting_strength"] <= 0.5:
            yield "Starting line increment must lie between 0 and 0.5."
        if values["trial_count"] > values["max_trials"]:
            yield "Adaptive trial_count exceeds the max_trials safety ceiling."


# 5. STOPPING AND RESULTS
# Original and finite adaptive modes collect trial_count accepted responses.
# Fixed levels collect the scheduled level repetitions; no threshold is claimed.


def trial_record(run, condition, state):
    offset = condition["offset_deg"]
    return {
        "state": state | {"line_offset_deg": offset},
        "measurements": {"line_offset_deg": offset},
        "instructions": f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}",
    }


def is_finished(run, conditions, state):
    return run.accepted_trials >= len(conditions)


def finish_experiment(run, conditions, state):
    run.complete()


def original_method(run):
    return OriginalTeachingMethod(
        run, make_conditions=make_conditions,
        initialise=initialise_experiment, choose=choose_condition,
        record=trial_record, update=update_experiment, finish=finish_experiment,
    )


def adaptive_method(run):
    return TeachingAdaptiveMethod(
        run, make_conditions=make_conditions, choose=choose_condition,
        maximum=0.5,
    )


def fixed_method(run):
    return constant_teaching_method(
        run, make_fixed_schedule,
        units="digital_line_increment_above_0.5",
        display_mapping="I_line=0.5+selected increment; background=0.5. Not calibrated optical contrast.",
    )


def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "original": lambda: original_method(run),
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_selection=prepare_selection,
        prepare_stimuli=prepare_method_stimuli,
        trial_events=trial_events,
        interpret_response=interpret_response,
    )


# 6. FRAMEWORK REGISTRATION — MINIMAL AND LAST
# Central compatibility for callers expecting make_trial(...).resolve(...).
make_trial = legacy_trial_factory(trial_events)


def definition(identity="example_experiment", stimulus=STIMULUS_DEFAULTS["target"]):
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        session_start=SESSION_START,
        default_config=f"configs/experiments/{identity}.json",
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        method_planner=make_fixed_schedule, validator=validate_method_settings,
        method_reviewer=lambda run: review_teaching_adaptive(run, make_conditions, choose_condition),
        adaptive=ADAPTIVE_RULE,

        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS | {"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
