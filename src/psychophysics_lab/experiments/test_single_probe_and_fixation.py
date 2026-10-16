"""EDIT THE SCIENCE: ordered trial states and response-driven adaptation.

Edit chronological phases/durations in configs/experiments/test_single_probe_and_fixation.json;
stimulus appearance in configs/stimuli/teaching_gabor.json. The experiment decides
condition, order and updates. The framework presents, listens and saves.
"""
import random
from pathlib import Path
from psychophysics_lab.core.timeline import load_timeline
from psychophysics_lab.researcher import (
    ConfigField, experiment, ResponseParadigm, AdaptiveSelection, StaircaseConfig, Step,
)


def procedure(run):
    # EDIT SCHEDULE: seeded balanced alternatives, then random order.
    count   = run.values["trial_count"]
    targets = [i % 2 for i in range(count)]
    random.Random(run.values["random_seed"]).shuffle(targets)
    # Resolve the ordered scientific design *before* opening a human display.
    # The JSON may contain fixed durations or references to validated TUI fields.
    config = Path(__file__).resolve().parents[3] / "configs/experiments" / (run.spec.id + ".json")
    if not config.is_file():
        # Generated modules exercised outside a repository use the working reference.
        from psychophysics_lab.core import timeline as engine
        config = Path(engine.__file__).resolve().parents[3] / "configs/experiments/test_single_probe_and_fixation.json"
    timeline = load_timeline(config, timings=run.values, slots=run.stimulus_snapshots)
    import hashlib
    run.initialise(expected_trials=count, resolution={
        "task": "Report negative or positive tilt using the configured keys",
        "targets": targets, "response_keys": run.responses.keys,
        "stimulus_slots": run.stimulus_snapshots,
        "presentation": "ordered fixation/target/interval/response; software times only",
        "trial_timeline": timeline.to_dict(),
        "timeline_source": config.name,
        "timeline_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
    })
    adaptive = run.adaptive({0: StaircaseConfig(2, 1, count + 1)}, count) if run.spec.adaptive else None
    contrast = run.stimulus_parameters()["contrast"]
    # EDIT PRESENTATION AND INTERPRETATION; no display or file plumbing needed.
    for target in targets:
        base        = run.stimulus_parameters()
        parameters  = run.stimulus_parameters(orientation_deg=(-1 if target == 0 else 1)*abs(base["orientation_deg"]), contrast=contrast)
        correct     = run.play_trial(timeline, target=target,
            condition=parameters["orientation_deg"], parameters_by_slot={"target": parameters},
            instructions=f"Negative tilt: {run.responses.keys[0]}   Positive tilt: {run.responses.keys[1]}   Escape: abort")
        if adaptive:
            _, contrast = run.update_adaptive(adaptive, 0, correct,
                lambda step: max(.001, min(1., contrast * (.8 if step == Step.DOWN else 1.25 if step == Step.UP else 1))))
    run.complete()


def definition(identity="test_single_probe_and_fixation", stimulus="teaching_gabor", *, adaptive=False, source_path=__file__):
    # EDIT DECLARATIONS: geometry is required for degrees; digital contrast is
    # not an optical contrast threshold. Add luminance/timing for tasks needing it.
    from pathlib import Path
    return experiment(id=identity, name=identity.replace("_", " ").title(),
        description="Self-paced tilt discrimination with a registered visual stimulus.", procedure=procedure,
        fields=(ConfigField("trial_count", "Accepted trials", "int", 6, minimum=1, maximum=500),
                ConfigField("random_seed", "Trial order seed", "int", 123, minimum=0),
                ConfigField("fixation_ms", "Fixation duration", "int", 500, units="ms", minimum=1, section="Timing"),
                ConfigField("stimulus_ms", "Stimulus duration", "int", 200, units="ms", minimum=1, section="Timing"),
                ConfigField("interval_ms", "Blank duration", "int", 150, units="ms", minimum=1, section="Timing"),
                ConfigField("response_timeout_ms", "Response timeout (0 waits for key)", "int", 0, units="ms", minimum=0, section="Timing")),
        responses=ResponseParadigm("tilt", ("negative", "positive"), ("F", "J")),
        calibration_requirements=("geometry",), monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots={"target": "orientation_patch"}, stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        adaptive=AdaptiveSelection("consecutive_up_down") if adaptive else None,
        source_paths=("src/psychophysics_lab/experiments/" + Path(source_path).name,
                      "src/psychophysics_lab/experiments/test_single_probe_and_fixation.py"))


SPEC = definition()
