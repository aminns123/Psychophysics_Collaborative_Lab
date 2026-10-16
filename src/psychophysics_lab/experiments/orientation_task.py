"""EDIT THE SCIENCE: self-paced left/right tilt discrimination.

Stimulus settings live in JSON; trial scheduling, task meaning and outcomes live
here. The framework owns geometry, windows, keys, clocks and durable records.
"""
import random
from psychophysics_lab.researcher import (
    ConfigField, experiment, ResponseParadigm, AdaptiveSelection, StaircaseConfig, Step,
)


def procedure(run):
    # EDIT SCHEDULE: seeded balanced alternatives, then random order.
    count = run.values["trial_count"]
    targets = [i % 2 for i in range(count)]
    random.Random(run.values["random_seed"]).shuffle(targets)
    run.initialise(expected_trials=count, resolution={
        "task": "Report negative or positive tilt using the configured keys",
        "targets": targets, "response_keys": run.responses.keys,
        "stimulus_slots": run.stimulus_snapshots,
        "presentation": "self-paced static patch; software reaction times",
    })
    adaptive = run.adaptive({0: StaircaseConfig(2, 1, count + 1)}, count) if run.spec.adaptive else None
    contrast = run.stimulus_parameters()["contrast"]
    # EDIT PRESENTATION AND INTERPRETATION; no display or file plumbing needed.
    for target in targets:
        base = run.stimulus_parameters()
        parameters = run.stimulus_parameters(orientation_deg=(-1 if target == 0 else 1)*abs(base["orientation_deg"]), contrast=contrast)
        correct = run.present(target=target, condition=parameters["orientation_deg"], parameters=parameters,
            instructions=f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort")
        if adaptive:
            _, contrast = run.update_adaptive(adaptive, 0, correct,
                lambda step: max(.001, min(1., contrast * (.8 if step == Step.DOWN else 1.25 if step == Step.UP else 1))))
    run.complete()


def definition(identity="orientation_task", stimulus="teaching_gabor", *, adaptive=False, source_path=__file__):
    # EDIT DECLARATIONS: geometry is required for degrees; digital contrast is
    # not an optical contrast threshold. Add luminance/timing for tasks needing it.
    from pathlib import Path
    return experiment(id=identity, name=identity.replace("_", " ").title(),
        description="Self-paced tilt discrimination with a registered visual stimulus.", procedure=procedure,
        fields=(ConfigField("trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500),
                ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0)),
        responses=ResponseParadigm("tilt", ("negative", "positive"), ("F", "J")),
        calibration_requirements=("geometry",), monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots={"target": "orientation_patch"}, stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        adaptive=AdaptiveSelection("consecutive_up_down") if adaptive else None,
        source_paths=("src/psychophysics_lab/experiments/" + Path(source_path).name,
                      "src/psychophysics_lab/experiments/orientation_task.py"))


SPEC = definition()
