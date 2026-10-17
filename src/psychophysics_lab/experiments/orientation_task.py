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


def procedure(run):
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    for _ in conditions:
        condition = choose_condition(run, conditions, state)
        stimuli = prepare_stimuli(run, condition, state)
        with run.trial(
            make_trial(run.values, condition),
            target=condition["target"],
            condition=condition["value"],
            parameters_by_slot=stimuli,
            **trial_record(run, condition, state),
        ) as trial:
            response = interpret_response(condition, trial.response)
            # Fixed stimulus; no artificial adaptive update stage.
    finish_experiment(run, conditions, state)


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
