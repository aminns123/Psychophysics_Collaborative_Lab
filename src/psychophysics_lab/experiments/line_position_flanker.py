"""Line Position Flanker: a scientific design in visual degrees, separate from historical replay.

Source: thesis Chapter 4, Figures 4.3B/4.5, Tables 4.3/4.6. Study-specific
choices remain TUI controls; vertical separation and observer-specific flanker frequency
must be supplied rather than copied from historical pixels. No claim of calibrated
physical contrast or timing is made by this software implementation.
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
)

# 1. SETTINGS AND STIMULI
FIELDS = (
    ConfigField(
        "positions_deg",
        "Probe x positions (degrees; choose study sampling)",
        "text",
        "-0.4,0,0.5",
    ),
    ConfigField("fixation_ms", "Fixation duration", "int", 500, minimum=1, units="ms"),
    ConfigField(
        "stimulus_ms", "Stimulus interval duration", "int", 300, minimum=1, units="ms"
    ),
    ConfigField(
        "staircases_per_condition",
        "Independent staircases per condition",
        "int",
        4,
        minimum=1,
    ),
    ConfigField(
        "starting_contrast",
        "Starting digital probe increment",
        "float",
        0.02,
        minimum=0.000001,
        maximum=0.49,
    ),
    ConfigField(
        "background_intensity",
        "Digital background; measured luminance must be qualified",
        "float",
        0.5,
        minimum=0.01,
        maximum=0.9,
    ),
    ConfigField(
        "n_down", "Consecutive correct answers before a decrease", "int", 4, minimum=1
    ),
    ConfigField("n_up", "Consecutive errors before an increase", "int", 1, minimum=1),
    ConfigField("logUNIT_UP", "Log10 increase", "float", 0.36, minimum=0.000001),
    ConfigField("logUNIT_DW", "Log10 decrease", "float", 0.30294, minimum=0.000001),
    ConfigField(
        "initial_one_down_limit",
        "Initial one-down responses (0 disables)",
        "int",
        0,
        minimum=0,
        maximum=1000,
    ),
    ConfigField(
        "reversal_termination", "Reversals per staircase", "int", 10, minimum=1
    ),
    ConfigField(
        "threshold_reversals",
        "Final reversals retained for threshold",
        "int",
        5,
        minimum=1,
    ),
    ConfigField(
        "max_trials",
        "Global safety ceiling; reaching it is incomplete",
        "int",
        10000,
        minimum=1,
    ),
)
FIELDS += (
    ConfigField(
        "probe_vertical_offset_deg",
        "Above/below displacement (study choice; required)",
        "float",
        None,
        minimum=0.001,
        maximum=5,
        units="degrees",
    ),
)
FIELDS += (
    ConfigField(
        "flanker_cpd",
        "Flanker frequency from prior observer CSF (required)",
        "float",
        None,
        minimum=0.01,
        maximum=32,
        units="cycles/degree",
    ),
)

RESPONSES = ResponseParadigm(
    "line_position_flanker", ("above", "below"), ("UP", "DOWN")
)
STIMULUS_SLOTS = {"fixation": "detection_scene", "first": "detection_scene"}
STIMULUS_DEFAULTS = {slot: "detection_scene" for slot in STIMULUS_SLOTS}
PARADIGM = "two_alternative_forced_choice"
SCIENTIFIC_SPEC = {
    "version": "line_position_flanker-1",
    "response": "Is the line above or below fixation?",
    "quantity": "Digital line increment above background; optical contrast requires measured calibration.",
    "conditions": "TUI-selected horizontal probe positions; independently interleaved repeat staircases and equiprobable above/below targets.",
    "adaptive": "TUI n-down/n-up and log10 steps; standard counter semantics, no inherited pixel/reversal quirks.",
    "stopping": "Reversal completion; global ceiling is incomplete, not a successful threshold.",
    "exclusions": "No post-hoc deletion; abort/timeout/errors preserved; no gamut clipping.",
    "estimator": "Geometric mean final retained presented reversals; mean across all complete repeats.",
    "geometry": "Line .013 degrees wide x .133 high; vertical displacement selected in TUI. Flanker 5 degree square at x=-3 degrees; digital peak-to-peak modulation .018; frequency selected from prior CSF.",
}


# 2. CONDITIONS AND TRIAL ORDER


def make_conditions(settings):
    positions = [float(x) for x in settings["positions_deg"].split(",")]
    rows = []
    for position in positions:
        for repeat in range(settings["staircases_per_condition"]):
            rows.append(
                {
                    "id": len(rows) + 1,
                    "value": position,
                    "x_deg": position,
                    "repeat": repeat + 1,
                }
            )
    return rows


def choose_condition(run, conditions, state):
    algorithm, rng = state["adaptive"], state["rng"]
    identity = algorithm.select(rng.choice)
    condition = dict(conditions[identity - 1])
    condition.update(
        target=rng.randrange(2),
        contrast=state["contrasts"][identity],
        previous_reversals=algorithm.states[identity].reversal_count,
    )
    return condition


# 3. PREPARE STIMULI


def prepare_stimuli(run, condition, state):
    settings = run.values
    background = settings["background_intensity"]
    common = dict(
        background=background,
        contrast=condition["contrast"],
        probe_x_deg=condition["x_deg"],
        probe_y_deg=(
            settings["probe_vertical_offset_deg"]
            if condition["target"] == 0
            else -settings["probe_vertical_offset_deg"]
        ),
        ring_present=False,
        flanker_present=True,
        flanker_cpd=settings["flanker_cpd"],
    )
    fixation = run.stimulus_parameters(
        "fixation",
        background=background,
        probe_present=False,
        ring_present=False,
        flanker_present=False,
    )
    first = run.stimulus_parameters("first", **common, probe_present=True)
    return {"fixation": fixation, "first": first}


# 4. ONE TRIAL


def make_trial(settings, condition):
    return TrialTimeline(
        (
            Show("fixation", slot="fixation", duration="fixation_ms"),
            Show("probe", slot="first", duration="stimulus_ms"),
            CollectResponse(actions=("above", "below"), slot="fixation"),
        )
    )


# 5. RESPONSES AND ADAPTATION


def interpret_response(condition, response):
    """Score the chosen alternative against this trial's assigned target."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def change_contrast(state, response, step):
    exponent = (
        -state["log_down"]
        if step == Step.DOWN
        else state["log_up"] if step == Step.UP else 0
    )
    contrast = state["contrast"] * 10**exponent
    if not 0 < contrast <= state["maximum_contrast"]:
        raise ValueError(
            "Next contrast exceeds the display range; stop and review starting contrast/background, without clipping."
        )
    return contrast


def update_experiment(run, condition, state, response, trial):
    staircase, identity = state["adaptive"], condition["id"]

    trial.apply(
        UpdateAdaptive(staircase, identity, change_contrast, state_key="next_contrast"),
        run.staircase_record_action(staircase, identity),
    )
    state["contrasts"][identity] = trial.state["next_contrast"]
    if staircase.states[identity].reversal_count > condition["previous_reversals"]:
        state["reversals"][identity].append(condition["contrast"])
    return state


def trial_record(run, condition, state):
    settings = run.values
    return run.adaptive_trial_record(
        state["adaptive"],
        condition["id"],
        contrast=condition["contrast"],
        maximum=1 - settings["background_intensity"] - 0.009,
        log_up=settings["logUNIT_UP"],
        log_down=settings["logUNIT_DW"],
        measurements={
            "probe_x_deg": condition["x_deg"],
            "staircase_repeat": condition["repeat"],
        },
        instructions=f"Above: {run.responses.keys[0]}   Below: {run.responses.keys[1]}   Escape stops",
    )


# 6. RUN AND FINISH


def initialise_experiment(run, conditions):
    settings = run.values
    algorithm = run.adaptive(
        {
            c["id"]: StaircaseConfig(
                settings["n_down"],
                settings["n_up"],
                settings["reversal_termination"],
                settings["initial_one_down_limit"],
            )
            for c in conditions
        },
        settings["max_trials"],
    )
    # Fixed n-down/one-up steps have this asymptotic accuracy target. Finite
    # reversal estimates (especially with lapses) still require recovery checks.
    accuracy_target = (
        (settings["logUNIT_UP"] / (settings["logUNIT_UP"] + settings["logUNIT_DW"]))
        ** (1 / settings["n_down"])
        if settings["n_up"] == 1
        else None
    )
    description = {
        "asymptotic_accuracy_target": accuracy_target,
        "adaptive_interpretation": (
            "fixed n-down/one-up stationary target; finite-run bias unqualified"
            if accuracy_target is not None
            else "n-up greater than one: threshold accuracy interpretation requires separate validation"
        ),
        "protocol": dict(SCIENTIFIC_SPEC),
        "staircases_per_condition": settings["staircases_per_condition"],
        "condition_definitions": conditions,
        "hardware_equivalence": False,
    }
    run.initialise(
        expected_trials=settings["max_trials"],
        resolution=description,
        background_intensity=settings["background_intensity"],
    )
    return {
        "adaptive": algorithm,
        "rng": random.Random(f"{run.seed}:conditions"),
        "contrasts": {c["id"]: settings["starting_contrast"] for c in conditions},
        "reversals": {c["id"]: [] for c in conditions},
        "description": description,
    }


def is_finished(run, conditions, state):
    return state["adaptive"].status != "running"


def finish_experiment(run, conditions, state):
    run.save_resolution(
        **(
            state["description"]
            | {"reversal_contrasts": {str(i): v for i, v in state["reversals"].items()}}
        )
    )
    run.complete_adaptive(state["adaptive"])
    # One declared estimator is used here and by post-hoc analysis.
    run.save_primary(
        {
            "version": 1,
            "value_column": "presented_display_contrast",
            "within_staircase": "geometric_mean",
            "across_staircases": "arithmetic_mean",
            "retained_reversals": run.values["threshold_reversals"],
            "completion": "all configured staircases complete",
            "units": "digital_probe_increment",
        },
        conditions,
    )


def procedure(run):
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    while not is_finished(run, conditions, state):
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
            state = update_experiment(run, condition, state, response, trial)
    finish_experiment(run, conditions, state)


# 7. FRAMEWORK CONNECTION


def validate_settings(values):
    import math

    try:
        positions = [float(x) for x in values["positions_deg"].split(",")]
        if (
            not positions
            or len(set(positions)) != len(positions)
            or any(not math.isfinite(x) or abs(x) > 5 for x in positions)
        ):
            yield "Choose distinct finite positions within +/-5 degrees."
    except ValueError:
        yield "Enter finite comma-separated numeric condition values."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Threshold reversal count exceeds reversal termination."
    if values["starting_contrast"] + 0.009 > 1 - values["background_intensity"]:
        yield "Starting digital increment exceeds display gamut."


def definition(identity="line_position_flanker"):
    return experiment(
        id=identity,
        name="Line Position Flanker (software validation)",
        procedure=procedure,
        description="Line Position Flanker",
        fields=FIELDS,
        scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        adaptive=AdaptiveSelection(
            "consecutive_up_down",
            controls=(
                "n_down",
                "n_up",
                "logUNIT_UP",
                "logUNIT_DW",
                "initial_one_down_limit",
                "staircases_per_condition",
                "reversal_termination",
                "max_trials",
            ),
            step_calculator="garcia_perez_1998",
            step_parameterization="log10_display_contrast",
        ),
        validator=validate_settings,
        supports_simulation=True,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        acquisition_block_reason="Scientific design implemented in degrees; measured luminance, effective contrast precision, frame timing and study-specific geometry must be qualified before human acquisition.",
        source_paths=("src/psychophysics_lab/experiments/line_position_flanker.py",),
    )


SPEC = definition()
