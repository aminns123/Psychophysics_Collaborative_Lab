"""EXAMPLE EXPERIMENT: is a white line left or right of centre?

START HERE: Edit these three parts:
    1. make_trial_order() — conditions and order.
    2. procedure()       — parameters per trial and response-driven updates.
    3. definition()      — settings, response keys and stimulus choice.

The corresponding experiment JSON declares the chronological phases:
fixation -> line -> blank -> response (and their durations).
Do not write window, key-event, calibration or saving code; PsyCoLab owns those.
This basic teaching task has NO adaptive method. For an advanced staircase
example, inspect orientation_adaptive.py after understanding this example.
"""
from pathlib import Path
from psychophysics_lab.core.timeline import load_timeline
from psychophysics_lab.researcher import ConfigField, ResponseParadigm, experiment


# EDIT 1: WHICH TRIALS AND IN WHAT ORDER?
def make_trial_order(trial_count):
    """0 = line left, 1 = line right. Alternating is intentionally simple."""
    return [trial % 2 for trial in range(trial_count)]


# EDIT 2: WHAT DO YOU SHOW, RECORD AND CHANGE AFTER A RESPONSE?
def procedure(run):
    conditions = make_trial_order(run.values["trial_count"])

    # FRAMEWORK: load the companion JSON for the ordered presentation phases.
    timeline_file = (Path(__file__).resolve().parents[3] / "configs"
                     / "experiments" / (run.spec.id + ".json"))
    timeline = load_timeline(
        timeline_file, timings=run.values, slots=run.stimulus_snapshots
    )
    run.initialise(expected_trials=len(conditions), resolution={
        "task": "Report whether the line is left or right.",
        "condition_order": conditions,
        "response_keys": run.responses.keys,
        "trial_timeline": timeline.to_dict(),
        "stimulus_slots": run.stimulus_snapshots,
    })

    for target in conditions:
        # EDIT: set the scientific stimulus condition for this trial.
        distance = abs(run.stimulus_parameters()["offset_deg"])
        offset = -distance if target == 0 else distance
        parameters = run.stimulus_parameters(offset_deg=offset)

        # FRAMEWORK: show the ordered phases, collect the response, SAVE it.
        correct = run.play_trial(
            timeline,
            target=target,
            condition=offset,
            parameters_by_slot={"target": parameters},
            measurements={"line_offset_deg": offset},
            instructions=f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}   Escape: abort",
        )

        # EDIT (OPTIONAL): use 'correct' to decide the NEXT stimulus state.
        # To run an adaptive staircase, select a reusable adaptive algorithm.
        # See orientation_adaptive.py rather than reimplementing the staircase.

    run.complete()  # FRAMEWORK: finalise only after all responses were saved.


# EDIT 3: WHAT CAN BE CONFIGURED IN THE NORMAL TUI?
def definition(identity="example_experiment", stimulus="example_stimulus"):
    return experiment(
        id=identity,
        name=identity.replace("_", " ").title(),
        description="Beginner left/right line-position discrimination.",
        procedure=procedure,
        fields=(
            ConfigField("trial_count", "Number of trials", "int", 6,
                        minimum=1, maximum=200),
            ConfigField("fixation_ms", "Fixation time", "int", 500,
                        units="ms", minimum=1, section="Timing"),
            ConfigField("stimulus_ms", "Line presentation time", "int", 200,
                        units="ms", minimum=1, section="Timing"),
            ConfigField("interval_ms", "Blank time", "int", 150,
                        units="ms", minimum=1, section="Timing"),
            ConfigField("response_timeout_ms", "Response timeout (0 waits)", "int", 0,
                        units="ms", minimum=0, section="Timing"),
        ),
        responses=ResponseParadigm("line_position", ("left", "right"), ("F", "J")),
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        stimulus_slots={"target": "simple_line"},
        stimulus_defaults={"target": stimulus},
        supports_simulation=True,
        source_paths=(f"src/psychophysics_lab/experiments/{identity}.py",),
    )


# FRAMEWORK: exporting SPEC makes the experiment discoverable.
SPEC = definition()
