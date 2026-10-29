"""Finite teaching discrimination; original, adaptive and constant-stimuli modes.

A1 contains everyday experimental choices, A2 the inspectable scientific rules,
and B the unchanged execution/recording connections. Digital increments are not
calibrated optical contrast; none of these finite tasks estimates a threshold.
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

# PART A1 — EXPERIMENTAL CHOICES
# Scheduled durations are ms; placement is degrees. Selected Configure values
# override defaults without rewriting this file or a saved preset.
# Target alternatives are response codes, not independent staircase tracks.
# The distance factor is probe_vertical_offset_deg. Balance target rows then
# shuffle with random_seed; odd counts retain one extra above target. Original
# canonical conditions are above/below; finite adaptation uses one track.
FIXED_CONDITION = 'above_or_below'  # historical fixed-mode canonical cell label
TARGET_ALTERNATIVES = ('above', 'below')
RESPONSE_KEYS = ("F", "J")
CALIBRATION_REQUIREMENTS = ("geometry",)
MONITOR_CAPABILITIES = ("display_binding", "resolution")
MAXIMUM_INCREMENT = 0.5  # digital I_line - I_background; background command = 0.5
# Original uses the selected stimulus intensity. Adaptive/fixed use 0.5 + strength.
# Original/adaptive stop after trial_count accepted answers; fixed mode schedules
# fixed_repetitions per strength (not per side). Odd target counts are preserved.

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

RESPONSES = ResponseParadigm("probe_above_below", TARGET_ALTERNATIVES, RESPONSE_KEYS)

STIMULUS_SLOTS = {"fixation": "fixation", "probe": "line"}

STIMULUS_DEFAULTS = {"fixation": "fixation_cross", "probe": "vertical_line_probe"}

PARADIGM = "two_alternative_forced_choice"

STIMULUS_SLOTS["ready_fixation"] = "fixation"

STIMULUS_DEFAULTS["ready_fixation"] = "fixation_cross"

# Session opening runs once; SESSION_START = [] disables it. SPACE is not a trial answer.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


def target_position(settings, condition):
    """Target 0 above (+degrees), 1 below (-degrees), relative to fixation."""
    offset = settings["probe_vertical_offset_deg"]
    return {"probe_y_deg": offset if condition["target"] == 0 else -offset}


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
        CollectResponse(actions=TARGET_ALTERNATIVES, timeout='response_timeout_ms'),
        RecordState('response_received'),
    ]

# These are the EXISTING original-mode journal measurements, with explicit units.
# Adaptive mode retains the owned staircase observations; fixed mode retains
# fixed_repeat and presented_display_contrast (digital increment), from teaching.py.
MEASUREMENT_UNITS = {'probe_x_deg': 'degrees', 'probe_y_deg': 'degrees'}


def trial_measurements(settings, condition):
    """Requested geometry, not a physically measured location; original mode."""
    return {"probe_x_deg": 0.0, "probe_y_deg": condition["probe_y_deg"]}


def response_instructions(responses):
    """Participant prompt; keys are the effective selected response mapping."""
    return "  ".join(f"{alt}: {key}" for alt, key in zip(responses.alternatives, responses.keys))


# PART A2 — SCIENTIFIC METHODS
# Original line: alternating 0/1. Above/below: balanced then random_seed shuffle.
# Shared finite adaptation retains n-down/n-up, multiplicative steps, bounds,
# and trial_count stopping; fixed uses the seeded shared level schedule.
# Legacy SCIENTIFIC_SPEC text is retained verbatim for saved-run compatibility.
SCIENTIFIC_SPEC = {'version': 'probe_above_below-1', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'None; fixed-trial demonstration.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}

ADAPTIVE_RULE = AdaptiveSelection('consecutive_up_down',
    controls=('n_down','n_up','down_factor','up_factor','max_trials'))

def make_conditions(settings):
    order = [i % 2 for i in range(settings["trial_count"])]
    random.Random(settings["random_seed"]).shuffle(order)
    return [{"target": target, **target_position(settings, {"target": target})} for target in order]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    condition["value"] = run.responses.alternatives[condition["target"]]
    return condition


def prepare_selection(run, condition):
    if "probe_y_deg" not in condition:
        condition.update(target_position(run.values, condition))


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


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(settings, seed, maximum=MAXIMUM_INCREMENT, condition=FIXED_CONDITION)


def validate_method_settings(values):
    method = values.get("contrast_method", "original")
    if method == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except ValueError as exc:
            yield str(exc)
    elif method == "adaptive":
        if not 0 <= values["starting_strength"] <= MAXIMUM_INCREMENT:
            yield "Starting vertical-line increment must lie between 0 and 0.5."
        if values["trial_count"] > values["max_trials"]:
            yield "Adaptive trial_count exceeds the max_trials safety ceiling."


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
        maximum=MAXIMUM_INCREMENT,
    )


def fixed_method(run):
    return constant_teaching_method(
        run, make_fixed_schedule,
        units="digital_line_increment_above_0.5",
        display_mapping="I_line=0.5+selected increment, background=0.5. Not measured optical contrast.",
    )


def initial_state():
    """Original-mode accepted correct-response count starts at zero."""
    return {"correct_count": 0}


def scientific_resolution(run, conditions):
    """Existing task/order/timeline metadata; no result estimator is introduced."""
    return {
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
    }


# PART B — FRAMEWORK INTEGRATION
# No scientific choices here: initialise, project existing records, bind callbacks.
def initialise_experiment(run, conditions):
    run.initialise(expected_trials=len(conditions), resolution=scientific_resolution(run, conditions))
    return initial_state()


def trial_record(run, condition, state):
    return {
        "state": dict(state),
        "measurements": trial_measurements(run.values, condition),
        "instructions": response_instructions(run.responses),
    }


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
        calibration_requirements=CALIBRATION_REQUIREMENTS,
        monitor_capabilities=MONITOR_CAPABILITIES,
        supports_simulation=True,
        source_paths=("src/psychophysics_lab/experiments/probe_above_below.py",),
    )


SPEC = definition()
