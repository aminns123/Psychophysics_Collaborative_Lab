"""Is the line above or below the central fixation cross?

This Python file replaces the built-in JSON procedure without changing its
scientific choices. The old design and loader remain internal compatibility
resources for saved data and independently tested historical designs.
Target 0 = above (+selected degrees), 1 = below (-selected degrees); default keys F/J.
Correctness is equality of the target/response alternative indices. Conditions
are balanced then shuffled using random_seed. Stop at trial_count responses.
No adaptation or sound. All durations are milliseconds; 0 timeout waits for a key.
Stimulus defaults/maths are FixationCross and VerticalLineProbe in the library.
RunContext executes the same procedure for live and virtual response sources.
"""

import random
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
    Stimulus,
    CollectResponse,
    RecordState,
    UpdateState,
)

# 1. PARAMETERS
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6, minimum=1, maximum=1000, help_text='Accepted-response goal for the finite teaching/original path; fixed mode derives its own count from levels, conditions and repetitions.'),
    ConfigField("random_seed", "Condition seed", "int", 123, minimum=0, units="integer seed", help_text='Integer seed for the experiment-owned condition randomization. Repeating the same seed and complete settings reproduces that randomization; changing it changes trial order.'),
    ConfigField(
        "probe_vertical_offset_deg", "Line distance above/below fixation",
        "float", 2.0, minimum=0.000001,
        units="degrees",
        help_text="Positive vertical angular displacement; above is + and below is -.",
    ),
    ConfigField(
        "fixation_ms",
        "Fixation time",
        "int",
        500,
        minimum=1,
        maximum=3600000,
        units="ms",
        section="Timing",
        help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.',
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
        help_text='Scheduled stimulus exposure duration in milliseconds; changing it changes the trial timeline, not measured display qualification.',
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
        help_text='Scheduled gap between the declared stimulus intervals, in milliseconds; only timeline phases using this setting are affected.',
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
        help_text='Time allowed for a valid response in milliseconds; zero waits without a timeout. Timeout is an incomplete response, not an invented answer.',
    ),
)


FIELDS += teaching_method_fields(
    default="original", strengths="0,0.1,0.2",
    label="Vertical-line increment above grey background",
) + teaching_adaptive_fields()

RESPONSES = ResponseParadigm("probe_above_below", ("above", "below"), ("F", "J"))
STIMULUS_SLOTS = {"fixation": "fixation", "probe": "line"}
STIMULUS_DEFAULTS = {"fixation": "fixation_cross", "probe": "vertical_line_probe"}

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
    """Fixation -> displaced probe with fixation -> blank -> above/below answer."""
    return [
        Show('fixation', stimuli=(Stimulus('fixation'),), duration='fixation_ms'),
        RecordState('before_probe'),
        Show(
            'probe',
            stimuli=(Stimulus('fixation'), Stimulus('probe', y_deg=condition['probe_y_deg'])),
            duration='stimulus_ms',
        ),
        Show('blank', duration='interval_ms'),
        CollectResponse(actions=('above', 'below'), timeout='response_timeout_ms'),
        RecordState('response_received'),
    ]


def prepare_stimuli(run, condition, state):
    return {
        "fixation": run.stimulus_parameters("fixation"),
        "probe": run.stimulus_parameters("probe"),
    }


def prepare_method_stimuli(run, condition, state):
    if run.values.get("contrast_method", "original") == "original":
        return prepare_stimuli(run, condition, state)
    return {
        "fixation": run.stimulus_parameters("fixation"),
        "probe": run.stimulus_parameters(
            "probe", intensity=0.5 + condition["contrast"]
        ),
    }


# 4. SCIENTIFIC RULES — CONDITIONS AND UPDATES


SCIENTIFIC_SPEC = {'version': 'probe_above_below-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


ADAPTIVE_RULE = AdaptiveSelection('consecutive_up_down',
    controls=('n_down','n_up','down_factor','up_factor','max_trials'))


def make_conditions(settings):
    order = [i % 2 for i in range(settings["trial_count"])]
    random.Random(settings["random_seed"]).shuffle(order)
    offset = settings["probe_vertical_offset_deg"]
    return [{"target": target, "probe_y_deg": offset if target == 0 else -offset} for target in order]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    condition["value"] = run.responses.alternatives[condition["target"]]
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
    trial.apply(UpdateState(update_from_response, name="update_correct_count"))
    return dict(trial.state)


def initialise_experiment(run, conditions):
    run.initialise(
        expected_trials=len(conditions),
        resolution={
            "task": "A white vertical line is shown above or below a central fixation cross.",
            "condition_order": [run.responses.alternatives[c["target"]] for c in conditions],
            "trial_order_seed": run.values["random_seed"],
            "probe_vertical_offset_deg": run.values["probe_vertical_offset_deg"],
            "above_timeline": TrialTimeline(trial_events(run.values, {"probe_y_deg": run.values["probe_vertical_offset_deg"]}))
            .resolve(run.values)
            .to_dict(),
            "below_timeline": TrialTimeline(trial_events(run.values, {"probe_y_deg": -run.values["probe_vertical_offset_deg"]}))
            .resolve(run.values)
            .to_dict(),
            "stimulus_slots": run.stimulus_snapshots,
        },
    )

    return {"correct_count": 0}


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(settings, seed, maximum=0.5, condition="above_or_below")


def prepare_selection(run, condition):
    if "probe_y_deg" not in condition:
        offset = run.values["probe_vertical_offset_deg"]
        condition["probe_y_deg"] = offset if condition["target"] == 0 else -offset


def validate_method_settings(values):
    method = values.get("contrast_method", "original")
    if method == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except ValueError as exc:
            yield str(exc)
    elif method == "adaptive":
        if not 0 <= values["starting_strength"] <= 0.5:
            yield "Starting vertical-line increment must lie between 0 and 0.5."
        if values["trial_count"] > values["max_trials"]:
            yield "Adaptive trial_count exceeds the max_trials safety ceiling."


# 5. STOPPING AND RESULTS
# Original and finite adaptive modes collect trial_count accepted responses.
# Fixed levels collect their scheduled repetitions; neither estimates a threshold.


def trial_record(run, condition, state):
    probe_y = condition["probe_y_deg"]
    return {
        "state": dict(state),
        "measurements": {"probe_x_deg": 0.0, "probe_y_deg": probe_y},
        "instructions": "  ".join(
            f"{alt}: {key}" for alt, key in zip(run.responses.alternatives, run.responses.keys)
        ),
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
        display_mapping="I_line=0.5+selected increment, background=0.5. Not measured optical contrast.",
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


def definition(identity="probe_above_below"):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="A white vertical line is shown above or below a central fixation cross.",
        procedure=procedure,
        session_start=SESSION_START,
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        method_planner=make_fixed_schedule, validator=validate_method_settings,
        method_reviewer=lambda run: review_teaching_adaptive(run, make_conditions, choose_condition),
        adaptive=ADAPTIVE_RULE,

        responses=RESPONSES,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        supports_simulation=True,
        source_paths=("src/psychophysics_lab/experiments/probe_above_below.py",),
    )


SPEC = definition()
