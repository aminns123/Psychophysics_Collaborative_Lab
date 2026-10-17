"""Tilt discrimination: one file owns the complete scientific procedure.

Target 0 = negative tilt, 1 = positive tilt; F/J by default (TUI can remap).
Correctness compares the target and response alternative indices. Conditions
are balanced, shuffled with random_seed, and stop after trial_count responses.
No adaptation or audio in this task. Digital contrast is not optical contrast.
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


def next_contrast(state, response, step):
    factor = 0.8 if step == Step.DOWN else 1.25 if step == Step.UP else 1
    return max(0.001, min(1.0, state["contrast"] * factor))


def procedure(run):
    # EDIT SCHEDULE: seeded balanced alternatives, then random order.
    count = run.values["trial_count"]
    targets = [i % 2 for i in range(count)]
    random.Random(run.values["random_seed"]).shuffle(targets)
    timeline = TRIAL.resolve(run.values)
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
        run.adaptive({0: StaircaseConfig(2, 1, count + 1)}, count)
        if run.spec.adaptive
        else None
    )
    contrast = run.stimulus_parameters()["contrast"]
    # EDIT PRESENTATION AND INTERPRETATION; no display or file plumbing needed.
    for target in targets:
        base = run.stimulus_parameters()
        parameters = run.stimulus_parameters(
            orientation_deg=(-1 if target == 0 else 1) * abs(base["orientation_deg"]),
            contrast=contrast,
        )
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
        run.play_trial(
            actions,
            target=target,
            state={"contrast": contrast},
            condition=parameters["orientation_deg"],
            parameters_by_slot={"target": parameters},
            instructions=f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort",
        )
        if adaptive:
            contrast = run.trial_state["contrast"]
    run.complete()


def definition(
    identity="orientation_task",
    stimulus="teaching_gabor",
    *,
    adaptive=False,
    source_path=__file__,
):
    # EDIT DECLARATIONS: geometry is required for degrees; digital contrast is
    # not an optical contrast threshold. Add luminance/timing for tasks needing it.
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Self-paced tilt discrimination with a registered visual stimulus.",
        procedure=procedure,
        fields=(
            ConfigField(
                "trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500
            ),
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
        ),
        responses=ResponseParadigm("tilt", ("negative", "positive"), ("F", "J")),
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots={"target": "orientation_patch"},
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        adaptive=AdaptiveSelection("consecutive_up_down") if adaptive else None,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


# Settings are declared above; no companion timeline file is required.
TRIAL = TrialTimeline(
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

SPEC = definition()
