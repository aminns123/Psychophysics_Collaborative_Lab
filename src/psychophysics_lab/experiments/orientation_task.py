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
    Show,
    CollectResponse,
)

# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500),
    ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0),
    ConfigField(
        "fixation_ms",
        "Fixation duration",
        "int",
        500,
        units="ms",
        minimum=1,
        section="Timing",
    ),
    ConfigField(
        "stimulus_ms",
        "Stimulus duration",
        "int",
        200,
        units="ms",
        minimum=1,
        section="Timing",
    ),
    ConfigField(
        "interval_ms",
        "Blank duration",
        "int",
        150,
        units="ms",
        minimum=1,
        section="Timing",
    ),
    ConfigField(
        "response_timeout_ms",
        "Response timeout (0 waits for key)",
        "int",
        0,
        units="ms",
        minimum=0,
        section="Timing",
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


# 2. CONDITIONS AND TRIAL ORDER
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


# 3. PREPARE STIMULI
def prepare_stimuli(run, condition, state):
    return {
        "target": run.stimulus_parameters(
            orientation_deg=condition["orientation_deg"], contrast=state["contrast"]
        )
    }


# 4. ONE TRIAL
def make_trial(settings, condition):
    return TrialTimeline(
        (
            Show("fixation", duration="fixation_ms", instructions="+"),
            Show("target", slot="target", duration="stimulus_ms"),
            Show("interval", duration="interval_ms"),
            CollectResponse(
                actions=("negative", "positive"),
                timeout="response_timeout_ms",
                instructions="Negative tilt: {negative}    Positive tilt: {positive}    Esc: abort",
            ),
        )
    )


# 5. RESPONSES AND ADAPTATION
def interpret_response(condition, response):
    """Both categories score the chosen spatial/property alternative or interval."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def trial_record(run, condition, state):
    return {
        "state": {"contrast": state["contrast"]},
        "instructions": f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort",
    }


# 6. RUN AND FINISH
def initialise_experiment(run, conditions):
    count = run.values["trial_count"]
    targets = [c["target"] for c in conditions]
    timeline = make_trial(run.values, {"target": 0}).resolve(run.values)
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


def finish_experiment(run, conditions, state):
    run.complete()


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(settings, seed, maximum=1.0, condition="tilt_sign")


def prepare_method_stimuli(run, condition, state):
    if run.values.get("contrast_method", "original") == "original":
        return prepare_stimuli(run, condition, state)
    base = run.stimulus_parameters()
    angle = (-1 if condition["target"] == 0 else 1) * abs(base["orientation_deg"])
    return {"target": run.stimulus_parameters(
        orientation_deg=angle, contrast=condition["contrast"]
    )}


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


def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "original": lambda: original_method(run),
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_stimuli=prepare_method_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )


# 7. FRAMEWORK CONNECTION
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
        fields=FIELDS,
        method_planner=make_fixed_schedule, validator=validate_method_settings,
        method_reviewer=lambda run: review_teaching_adaptive(run, make_conditions, choose_condition),
        adaptive=AdaptiveSelection('consecutive_up_down', controls=('n_down','n_up','down_factor','up_factor','max_trials')),

        scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
