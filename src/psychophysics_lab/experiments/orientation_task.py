"""Tilt discrimination: one file owns the complete scientific procedure.

Target 0 = negative tilt, 1 = positive tilt; F/J by default (TUI can remap).
Correctness compares the target and response alternative indices. Conditions
are balanced, shuffled with random_seed, and stop after trial_count responses.
The original task has no adaptation or audio; optional teaching methods can now be selected explicitly. Digital contrast is not optical contrast.
Stimulus maths/defaults are in TeachingGabor in stimulus_library.py; optional
saved stimulus presets override appearance, never trial sequence or meanings.
RunContext supplies the same presentation/response/data path for live and virtual
observers. Display calibration and staircase algorithms are shared mechanisms.
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
    experiment,
    ResponseParadigm,
    AdaptiveSelection,
    TrialTimeline,
    WaitForKey,
    legacy_trial_factory,
    Show,
    CollectResponse,
)

# 1. PARAMETERS
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500, help_text='Accepted-response goal for the finite teaching/original path; fixed mode derives its own count from levels, conditions and repetitions.'),
    ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0, help_text='Integer seed for the experiment-owned condition randomization. Repeating the same seed and complete settings reproduces that randomization; changing it changes trial order.'),
    ConfigField(
        "fixation_ms",
        "Fixation duration",
        "int",
        500,
        units="ms",
        minimum=1,
        section="Timing",
        help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.',
    ),
    ConfigField(
        "stimulus_ms",
        "Stimulus duration",
        "int",
        200,
        units="ms",
        minimum=1,
        section="Timing",
        help_text='Scheduled stimulus exposure duration in milliseconds; changing it changes the trial timeline, not measured display qualification.',
    ),
    ConfigField(
        "interval_ms",
        "Blank duration",
        "int",
        150,
        units="ms",
        minimum=1,
        section="Timing",
        help_text='Scheduled gap between the declared stimulus intervals, in milliseconds; only timeline phases using this setting are affected.',
    ),
    ConfigField(
        "response_timeout_ms",
        "Response timeout (0 waits for key)",
        "int",
        0,
        units="ms",
        minimum=0,
        section="Timing",
        help_text='Time allowed for a valid response in milliseconds; zero waits without a timeout. Timeout is an incomplete response, not an invented answer.',
    ),
)


FIELDS += teaching_method_fields(
    default="original", strengths="0.05,0.1,0.2",
    label="Gabor digital contrast modulation",
) + teaching_adaptive_fields()

RESPONSES = ResponseParadigm("tilt", ("negative", "positive"), ("F", "J"))
STIMULUS_SLOTS = {"target": "orientation_patch"}
STIMULUS_DEFAULTS = {"target": "teaching_gabor"}

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
    """Fixation -> tilted Gabor -> blank interval -> negative/positive answer."""
    return [
        Show('fixation', duration='fixation_ms', instructions='+'),
        Show('target', slot='target', duration='stimulus_ms'),
        Show('interval', duration='interval_ms'),
        CollectResponse(
            actions=('negative', 'positive'),
            timeout='response_timeout_ms',
            instructions='Negative tilt: {negative}    Positive tilt: {positive}    Esc: abort',
        ),
    ]


def prepare_stimuli(run, condition, state):
    return {
        "target": run.stimulus_parameters(
            orientation_deg=condition["orientation_deg"], contrast=state["contrast"]
        )
    }


def prepare_method_stimuli(run, condition, state):
    if run.values.get("contrast_method", "original") == "original":
        return prepare_stimuli(run, condition, state)
    base = run.stimulus_parameters()
    angle = (-1 if condition["target"] == 0 else 1) * abs(base["orientation_deg"])
    return {"target": run.stimulus_parameters(
        orientation_deg=angle, contrast=condition["contrast"]
    )}


# 4. SCIENTIFIC RULES — CONDITIONS AND UPDATES


SCIENTIFIC_SPEC = {
    "version": "orientation-task-1",
    "response": "Negative or positive tilt; index equality.",
    "quantity": "Teaching digital Gabor contrast, not optical contrast.",
    "conditions": "Balanced shuffled target signs using declared seed.",
    "adaptive": "None.",
    "stopping": "Accepted trial count.",
    "exclusions": "No post-hoc deletion; interrupted input preserved.",
    "estimator": "No threshold estimator; responses and correctness only.",
}


ADAPTIVE_RULE = AdaptiveSelection('consecutive_up_down', controls=('n_down','n_up','down_factor','up_factor','max_trials'))


def make_conditions(settings):
    targets = [i % 2 for i in range(settings["trial_count"])]
    random.Random(settings["random_seed"]).shuffle(targets)
    return [{"target": target} for target in targets]


def choose_condition(run, conditions, state):
    condition = dict(conditions[run.accepted_trials])
    base = run.stimulus_parameters()
    condition["orientation_deg"] = (-1 if condition["target"] == 0 else 1) * abs(
        base["orientation_deg"]
    )
    condition["value"] = condition["orientation_deg"]
    return condition


def interpret_response(condition, response):
    """Both categories score the chosen spatial/property alternative or interval."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def initialise_experiment(run, conditions):
    count = run.values["trial_count"]
    targets = [c["target"] for c in conditions]
    timeline = TrialTimeline(trial_events(run.values, {"target": 0})).resolve(run.values)
    run.initialise(
        expected_trials=count,
        resolution={
            "task": "Report negative or positive tilt using the configured keys",
            "targets": targets,
            "response_keys": run.responses.keys,
            "stimulus_slots": run.stimulus_snapshots,
            "presentation": "ordered fixation/target/interval/response; software times only",
            "trial_timeline": timeline.to_dict(),
            "timeline_source": __file__.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
            "trial_order_seed": run.values["random_seed"],
        },
    )
    contrast = run.stimulus_parameters()["contrast"]

    return {"contrast": contrast}


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(settings, seed, maximum=1.0, condition="tilt_sign")


def validate_method_settings(values):
    if values.get("contrast_method", "original") == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except ValueError as exc:
            yield str(exc)
    elif values.get("contrast_method") == "adaptive":
        if not 0 <= values["starting_strength"] <= 1:
            yield "Adaptive starting strength must be between 0 and 1."
        if values["trial_count"] > values["max_trials"]:
            yield "Adaptive trial count exceeds the max_trials safety ceiling."


# 5. STOPPING AND RESULTS
# Original and finite adaptive modes stop after trial_count accepted answers;
# fixed levels stop after their scheduled presentations. No threshold is fitted.


def trial_record(run, condition, state):
    return {
        "state": {"contrast": state["contrast"]},
        "instructions": f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort",
    }


def finish_experiment(run, conditions, state):
    run.complete()


def original_method(run):
    return OriginalTeachingMethod(
        run, make_conditions=make_conditions,
        initialise=initialise_experiment, choose=choose_condition,
        record=trial_record, update=None, finish=finish_experiment,
    )


def adaptive_method(run):
    return TeachingAdaptiveMethod(
        run, make_conditions=make_conditions,
        choose=choose_condition, maximum=1.0,
    )


def fixed_method(run):
    return constant_teaching_method(
        run, make_fixed_schedule,
        units="teaching_gabor_digital_modulation",
        display_mapping="I=0.5+0.5*C*envelope*cos(orientation phase); not measured optical contrast.",
    )


def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "original": lambda: original_method(run),
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_stimuli=prepare_method_stimuli,
        trial_events=trial_events,
        interpret_response=interpret_response,
    )


# 6. FRAMEWORK REGISTRATION — MINIMAL AND LAST
# Central compatibility for callers expecting make_trial(...).resolve(...).
make_trial = legacy_trial_factory(trial_events)


def definition(
    identity="orientation_task",
    stimulus=STIMULUS_DEFAULTS["target"],
    *,
    source_path=__file__,
):
    # EDIT DECLARATIONS: geometry is required for degrees; digital contrast is
    # not an optical contrast threshold. Add luminance/timing for tasks needing it.
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Self-paced tilt discrimination with a registered visual stimulus.",
        procedure=procedure,
        session_start=SESSION_START,
        fields=FIELDS,
        method_planner=make_fixed_schedule, validator=validate_method_settings,
        method_reviewer=lambda run: review_teaching_adaptive(run, make_conditions, choose_condition),
        adaptive=ADAPTIVE_RULE,

        scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS | {"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
