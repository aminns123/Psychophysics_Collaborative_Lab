"""Is the line above or below the central fixation cross?

This Python file replaces the built-in JSON procedure without changing its
scientific choices. The old design and loader remain internal compatibility
resources for saved data and independently tested historical designs.
Target 0 = above (+2 degrees), 1 = below (-2 degrees); default keys F/J.
Correctness is equality of the target/response alternative indices. Conditions
are balanced then shuffled using random_seed. Stop at trial_count responses.
No adaptation or sound. All durations are milliseconds; 0 timeout waits for a key.
Stimulus defaults/maths are FixationCross and VerticalLineProbe in the library.
RunContext executes the same procedure for live and virtual response sources.
"""


import random
from psychophysics_lab.researcher import (
    ConfigField,
    ResponseParadigm,
    experiment,
    TrialTimeline,
    Show,
    Stimulus,
    CollectResponse,
    RecordState,
    UpdateState,
)


# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
FIELDS = (
    ConfigField(
        "trial_count", "Number of trials", "int", 6, minimum=1, maximum=1000
    ),
    ConfigField("random_seed", "Condition seed", "int", 123, minimum=0),
    ConfigField(
        "fixation_ms",
        "Fixation time",
        "int",
        500,
        minimum=1,
        maximum=3600000,
        units="ms",
        section="Timing",
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
    ),
)


RESPONSES = ResponseParadigm("probe_above_below", ("above", "below"), ("F", "J"))
STIMULUS_SLOTS = {"fixation": "fixation", "probe": "line"}
STIMULUS_DEFAULTS = {"fixation": "fixation_cross", "probe": "vertical_line_probe"}


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(values):
    order = [i % 2 for i in range(values["trial_count"])]
    random.Random(values["random_seed"]).shuffle(order)
    return order


# 3. PREPARE STIMULI
def prepare_stimuli(target):
    """The vertical placement is the only stimulus change between conditions."""
    return 2.0 if target == 0 else -2.0


# 4. ONE TRIAL
def make_trial(probe_y_deg):
    return TrialTimeline(
        (
            Show("fixation", stimuli=(Stimulus("fixation"),), duration="fixation_ms"),
            RecordState("before_probe"),
            Show(
                "probe",
                stimuli=(Stimulus("fixation"), Stimulus("probe", y_deg=probe_y_deg)),
                duration="stimulus_ms",
            ),
            Show("blank", duration="interval_ms"),
            CollectResponse(actions=("above", "below"), timeout="response_timeout_ms"),
            RecordState("response_received"),
            UpdateState(update_from_response, name="update_correct_count"),
        )
    )


# 5. RESPONSES AND ADAPTATION
# Correctness is target/response alternative equality. Count correct answers only;
# no adaptive stimulus change. The loop finishes at the selected trial count.
def update_from_response(state, response):
    return dict(state) | {
        "correct_count": state["correct_count"] + int(response["correct"])
    }


# 6. RUN AND FINISH
def procedure(run):
    order = make_conditions(run.values)
    run.initialise(
        expected_trials=len(order),
        resolution={
            "task": "A white vertical line is shown above or below a central fixation cross.",
            "condition_order": [run.responses.alternatives[i] for i in order],
            "trial_order_seed": run.values["random_seed"],
            "above_timeline": make_trial(2.0).resolve(run.values).to_dict(),
            "below_timeline": make_trial(-2.0).resolve(run.values).to_dict(),
            "stimulus_slots": run.stimulus_snapshots,
        },
    )
    state = {"correct_count": 0}
    for target in order:
        # 1. CHOOSE A CONDITION; 2. PREPARE ITS STIMULI.
        probe_y = prepare_stimuli(target)
        # 3. PRESENT ONE TRIAL; 4. INTERPRET the named response by index equality.
        # 5. UPDATE correct_count using update_from_response in the trial plan.
        run.play_trial(
            make_trial(probe_y),
            target=target,
            condition=run.responses.alternatives[target],
            state=state,
            measurements={"probe_x_deg": 0.0, "probe_y_deg": probe_y},
            instructions="  ".join(
                f"{alt}: {key}"
                for alt, key in zip(run.responses.alternatives, run.responses.keys)
            ),
        )
        state = dict(run.trial_state)
        # 6. CHECK WHETHER TO FINISH: the loop ends after the configured trial count.
    run.complete()


# 7. FRAMEWORK CONNECTION
def definition(identity="probe_above_below"):
    return experiment(
        id=identity,
        name="Probe Above or Below Fixation",
        description="A white vertical line is shown above or below a central fixation cross.",
        procedure=procedure,
        fields=FIELDS,
        responses=RESPONSES,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry",),
        monitor_capabilities=("display_binding", "resolution"),
        supports_simulation=True,
        source_paths=("src/psychophysics_lab/experiments/probe_above_below.py",),
    )


SPEC = definition()
