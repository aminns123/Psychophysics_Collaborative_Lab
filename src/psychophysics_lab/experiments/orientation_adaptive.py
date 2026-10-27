"""Tilt discrimination: one file owns the complete scientific procedure.

Target 0 = negative tilt, 1 = positive tilt; F/J by default (TUI can remap).
Correctness compares the target and response alternative indices. Conditions
are balanced, shuffled with random_seed, and stop after trial_count responses.
Adaptation defaults (editable in the TUI): independent 2-down/1-up staircase; two correct answers multiply
contrast by .8, one incorrect by 1.25, hold otherwise, saturate at 1.
Only representable-number underflow protection is applied at the lower bound;
there is no scientific .001 contrast floor.
Stop at trial_count accepted responses, not reversals (limit is count + 1).
No audio in this task. Digital contrast is not optical contrast.
Stimulus maths/defaults are in TeachingGabor in stimulus_library.py; optional
saved stimulus presets override appearance, never trial sequence or meanings.
RunContext supplies the same presentation/response/data path for live and virtual
observers. Display calibration and staircase algorithms are shared mechanisms.
"""

import random
from psychophysics_lab.methods.contrast import AdaptiveContrastMethod, run_contrast_experiment
from psychophysics_lab.methods.teaching import (
    teaching_method_fields, fixed_teaching_schedule, constant_teaching_method,
)

from psychophysics_lab.researcher import (
    ConfigField,
    experiment,
    ResponseParadigm,
    AdaptiveSelection,
    StaircaseConfig,
    Step,
    TrialTimeline,
    Show,
    CollectResponse,
    UpdateAdaptive,
    RecordState,
)

# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField("trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500, help_text='Accepted-response goal for the finite teaching/original path; fixed mode derives its own count from levels, conditions and repetitions.'),
    ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0, help_text='Integer seed for the experiment-owned condition randomization. Repeating the same seed and complete settings reproduces that randomization; changing it changes trial order.'),
    ConfigField(
        "n_down", "Consecutive correct answers before decreasing contrast", "int", 2, minimum=1,
        help_text='Consecutive correct responses required before a downward strength step. Increasing this count delays downward steps; it does not change the selected step magnitude.',
    ),
    ConfigField(
        "n_up", "Consecutive incorrect answers before increasing contrast", "int", 1, minimum=1,
        help_text='Consecutive incorrect responses required before an upward strength step. Increasing this count delays upward steps; it does not change the selected step magnitude.',
    ),
    ConfigField(
        "down_factor",
        "Contrast multiplier for a down step",
        "float",
        0.8,
        minimum=0.000001,
        maximum=1,
        help_text='Multiplicative strength factor for an eligible downward step; the selected method enforces its lower strength bound.',
    ),
    ConfigField("up_factor", "Contrast multiplier for an up step", "float", 1.25, minimum=1, help_text='Multiplicative strength factor for an eligible upward step; the selected method enforces its upper strength bound.'),
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
    default="adaptive", strengths="0.05,0.1,0.2",
    label="Gabor digital contrast modulation",
)


RESPONSES = ResponseParadigm("tilt", ("negative", "positive"), ("F", "J"))
STIMULUS_SLOTS = {"target": "orientation_patch"}
STIMULUS_DEFAULTS = {"target": "teaching_gabor"}

PARADIGM = "two_alternative_forced_choice"


SCIENTIFIC_SPEC = {'version': 'orientation_adaptive-2', 'response': 'Two named alternatives; target/response alternative equality.', 'quantity': 'Teaching stimulus digital commands and geometry; no calibrated optical threshold claim.', 'conditions': 'Explicit condition order in make_conditions; shuffled only where its seed is declared.', 'adaptive': 'TUI consecutive up/down factors; demonstration only.', 'stopping': 'Configured accepted response count, not a threshold convergence criterion.', 'exclusions': 'No retrospective deletion; timeout/abort/error preserved as run status.', 'estimator': 'No scientific threshold estimate; response/accuracy records only.'}


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
    # Fixed strengths arrive as a selected trial value. Adaptive continues to
    # read the historically tested state['contrast'] and original orientation.
    strength = condition["contrast"] if "contrast" in condition else state["contrast"]
    orientation = (
        (-1 if condition["target"] == 0 else 1)
        * abs(run.stimulus_parameters()["orientation_deg"])
        if "orientation_deg" not in condition
        else condition["orientation_deg"]
    )
    return {
        "target": run.stimulus_parameters(
            orientation_deg=orientation, contrast=strength
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


# Consecutive correct/incorrect counts and multipliers come from the TUI. A step
# resets its streak; each response resets the opposite streak. No initial phase.
# This teaching experiment saturates digital contrast at [0, 1] and stops after
# trial_count responses; count+1 reversals is intentionally unreachable in that run.
def next_contrast(state, response, step):
    factor = (
        state["down_factor"] if step == Step.DOWN else state["up_factor"] if step == Step.UP else 1
    )
    import sys
    value = state["contrast"]
    if step == Step.HOLD or factor == 1:
        return value
    if value == 0:
        return sys.float_info.min if step == Step.UP else 0.0
    # Only a representable positive numeric floor; never raise a valid small
    # contrast to a scientific floor such as .001 after a down/hold decision.
    return max(min(sys.float_info.min, value), min(1.0, value * factor))


def update_experiment(run, condition, state, response, trial):
    trial.apply(
        UpdateAdaptive(state["adaptive"], 0, next_contrast, state_key="contrast"),
        RecordState("after_adaptation"),
    )
    state["contrast"] = trial.state["contrast"]
    return state


def trial_record(run, condition, state):
    return {
        "state": {
            "contrast": state["contrast"],
            "down_factor": run.values["down_factor"],
            "up_factor": run.values["up_factor"],
        },
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
    adaptive = (
        run.adaptive(
            {0: StaircaseConfig(run.values["n_down"], run.values["n_up"], count + 1)},
            run.values["max_trials"],
            starting_values={0: contrast}
        )
        if run.spec.adaptive
        else None
    )
    return {"contrast": contrast, "adaptive": adaptive}


def is_finished(run, conditions, state):
    return run.accepted_trials >= len(conditions)


def finish_experiment(run, conditions, state):
    run.complete()


def make_fixed_schedule(settings, seed):
    return fixed_teaching_schedule(
        settings, seed, maximum=1.0, condition="tilt_sign"
    )


def fixed_method(run):
    return constant_teaching_method(
        run, make_fixed_schedule,
        units="teaching_gabor_digital_modulation",
        display_mapping="Gabor: I=0.5+0.5*C*envelope*cos(orientation phase); not measured optical contrast.",
    )


def adaptive_method(run):
    # Delegate to the original n-down/n-up teaching callbacks and step rule.
    return AdaptiveContrastMethod(
        run, make_conditions=make_conditions,
        initialise=initialise_experiment, select=choose_condition,
        record=trial_record, update=update_experiment,
        finished=is_finished, finish=finish_experiment,
    )


def validate_method_settings(values):
    if values.get("contrast_method", "adaptive") == "adaptive" and values["trial_count"] > values["max_trials"]:
        yield "Accepted teaching trials must not exceed max_trials (the response safety ceiling)."
    if values.get("contrast_method", "adaptive") == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except ValueError as exc:
            yield str(exc)


def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )


# 7. FRAMEWORK CONNECTION
def definition(
    identity="orientation_adaptive",
    stimulus=STIMULUS_DEFAULTS["target"],
    *,
    adaptive=True,
    source_path=__file__,
):
    # EDIT DECLARATIONS: geometry is required for degrees; digital contrast is
    # not an optical contrast threshold. Add luminance/timing for tasks needing it.
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Self-paced tilt discrimination with a registered visual stimulus.",
        procedure=procedure,
        fields=FIELDS, scientific_spec=SCIENTIFIC_SPEC,
        method_planner=make_fixed_schedule, validator=validate_method_settings,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        adaptive=(
            AdaptiveSelection(
                "consecutive_up_down", controls=("n_down", "n_up", "down_factor", "up_factor")
            )
            if adaptive
            else None
        ),
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
