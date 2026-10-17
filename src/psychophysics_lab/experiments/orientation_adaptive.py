"""Tilt discrimination: one file owns the complete scientific procedure.

Target 0 = negative tilt, 1 = positive tilt; F/J by default (TUI can remap).
Correctness compares the target and response alternative indices. Conditions
are balanced, shuffled with random_seed, and stop after trial_count responses.
Adaptation defaults (editable in the TUI): independent 2-down/1-up staircase; two correct answers multiply
contrast by .8, one incorrect by 1.25, hold otherwise, clamp to [.001, 1].
Stop at trial_count accepted responses, not reversals (limit is count + 1).
No audio in this task. Digital contrast is not optical contrast.
Stimulus maths/defaults are in TeachingGabor in stimulus_library.py; optional
saved stimulus presets override appearance, never trial sequence or meanings.
RunContext supplies the same presentation/response/data path for live and virtual
observers. Display calibration and staircase algorithms are shared mechanisms.
"""


import random
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
    ConfigField(
        "trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500
    ),
    ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0),
    ConfigField("n_down", "Consecutive correct answers before decreasing contrast", "int", 2, minimum=1),
    ConfigField("n_up", "Consecutive incorrect answers before increasing contrast", "int", 1, minimum=1),
    ConfigField("down_factor", "Contrast multiplier for a down step", "float", .8, minimum=.000001, maximum=1),
    ConfigField("up_factor", "Contrast multiplier for an up step", "float", 1.25, minimum=1),
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


RESPONSES = ResponseParadigm("tilt", ("negative", "positive"), ("F", "J"))
STIMULUS_SLOTS = {"target": "orientation_patch"}
STIMULUS_DEFAULTS = {"target": "teaching_gabor"}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(values):
    targets = [i % 2 for i in range(values["trial_count"])]
    random.Random(values["random_seed"]).shuffle(targets)
    return targets


# 3. PREPARE STIMULI
def prepare_stimuli(run, target, contrast):
    base = run.stimulus_parameters()
    return run.stimulus_parameters(
        orientation_deg=(-1 if target == 0 else 1) * abs(base["orientation_deg"]),
        contrast=contrast,
    )


# 4. ONE TRIAL
def make_trial():
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
# The shared staircase resets the opposite answer streak and resets a streak
# after its step. The TUI supplies n_down/n_up and both contrast multipliers.
# Hold otherwise; clip digital contrast to [.001, 1]. This teaching task stops at
# trial_count responses; count+1 reversals is deliberately unreachable in that run.
def next_contrast(state, response, step):
    factor = state["down_factor"] if step == Step.DOWN else state["up_factor"] if step == Step.UP else 1
    return max(0.001, min(1.0, state["contrast"] * factor))


# 6. RUN AND FINISH
def procedure(run):
    # EDIT SCHEDULE: seeded balanced alternatives, then random order.
    count = run.values["trial_count"]
    targets = make_conditions(run.values)
    timeline = make_trial().resolve(run.values)
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
    adaptive = (
        run.adaptive({0: StaircaseConfig(run.values["n_down"], run.values["n_up"], count + 1)}, count)
        if run.spec.adaptive
        else None
    )
    contrast = run.stimulus_parameters()["contrast"]
    # EDIT PRESENTATION AND INTERPRETATION; no display or file plumbing needed.
    for target in targets:
        # 1. CHOOSE A CONDITION: next target in the seeded balanced order.
        # 2. PREPARE ITS STIMULI: tilt sign identifies the correct alternative.
        parameters = prepare_stimuli(run, target, contrast)
        actions = (
            TrialTimeline(
                timeline.phases
                + (
                    UpdateAdaptive(adaptive, 0, next_contrast, state_key="contrast"),
                    RecordState("after_adaptation"),
                )
            )
            if adaptive
            else timeline
        )
        # 3. PRESENT ONE TRIAL; 4. INTERPRET the negative/positive response.
        # Correctness is target/response index equality; 5. UPDATE via the plan callback.
        run.play_trial(
            actions,
            target=target,
            state={"contrast": contrast, "down_factor": run.values["down_factor"], "up_factor": run.values["up_factor"]},
            condition=parameters["orientation_deg"],
            parameters_by_slot={"target": parameters},
            instructions=f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort",
        )
        if adaptive:
            contrast = run.trial_state["contrast"]
        # 6. CHECK WHETHER TO FINISH: stop after the configured number of targets.
    run.complete()


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
        fields=FIELDS,
        responses=RESPONSES,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        adaptive=AdaptiveSelection("consecutive_up_down", controls=("n_down", "n_up", "down_factor", "up_factor")) if adaptive else None,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


SPEC = definition()
