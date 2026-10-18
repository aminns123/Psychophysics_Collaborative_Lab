"""Ellipse Major Axis: a scientific design in visual degrees, separate from historical replay.

Source: thesis Chapter 4, Figures 4.3B/4.5, Tables 4.3/4.6. Study-specific
choices remain TUI controls; unspecified ring digital increment must
be supplied rather than copied from historical pixels. No claim of calibrated
physical contrast or timing is made by this software implementation.
"""

import random
import sys
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.experiments._internal.parameter_compatibility import migrate_probe_intensity
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
    Beep,
)

# 1. SETTINGS AND STIMULI
FIELDS = (
    ConfigField(
        "positions_deg",
        "Probe x positions (degrees; choose study sampling)",
        "text",
        "-0.4,0,0.5",
        units='degrees',
    ),
    ConfigField("fixation_ms", "Fixation duration", "int", 500, minimum=1, units="ms"),
    ConfigField(
        "stimulus_ms", "Stimulus interval duration", "int", 250, minimum=1, units="ms"
    ),
    ConfigField(
        "staircases_per_condition",
        "Independent staircases per condition",
        "int",
        4,
        minimum=1,
        units='staircases',
    ),
    ConfigField(
        "starting_probe_intensity",
        "Starting probe intensity",
        "float",
        0.52,
        minimum=0,
        maximum=1,
        units='digital intensity, 0 to 1',
        help_text="0 = black; 1 = white. This bright-probe task uses intensity at or above background. The staircase changes the difference from background, not absolute intensity. Ring/flanker overlap uses the scene's additive headroom; see the resolved range below.",
    ),
    ConfigField(
        "background_intensity",
        "Background intensity",
        "float",
        0.5,
        minimum=0,
        maximum=1,
        units='digital intensity, 0 to 1',
    ),
    ConfigField(
        "n_down", "Consecutive correct answers before a decrease", "int", 4, minimum=1,
        units='consecutive correct responses',
    ),
    ConfigField("n_up", "Consecutive errors before an increase", "int", 1, minimum=1, units='consecutive incorrect responses'),
    ConfigField("logUNIT_UP", "Increase in probe difference from background", "float", 0.36, minimum=0.000001, units='log10 units', help_text="Multiply the probe-background difference by 10**step; hold at the upper bound."),
    ConfigField("logUNIT_DW", "Decrease in probe difference from background", "float", 0.30294, minimum=0.000001, units='log10 units', help_text="Multiply the probe-background difference by 10**(-step); this approaches background, rather than subtracting the step from intensity."),
    ConfigField(
        "initial_one_down_limit",
        "Initial one-down responses (0 disables)",
        "int",
        0,
        minimum=0,
        maximum=1000,
        units='responses',
    ),
    ConfigField(
        "reversal_termination", "Reversals per staircase", "int", 10, minimum=1,
        units='reversals',
    ),
    ConfigField(
        "threshold_reversals",
        "Final reversals retained for threshold",
        "int",
        8,
        minimum=1,
        units='reversals',
    ),
    ConfigField(
        "max_trials",
        "Global safety ceiling; reaching it is incomplete",
        "int",
        10000,
        minimum=1,
        units='responses',
    ),
)
FIELDS += (
    ConfigField("isi_ms", "Gap between intervals", "int", 250, minimum=1, units="ms"),
    ConfigField(
        "ring_increment",
        "Ring digital increment (study choice; required)",
        "float",
        None,
        minimum=0.00001,
        maximum=1,
        units='digital increment',
    ),
    ConfigField("aspect_ratios", "Ellipse b/a ratios", "text", "0.5,0.75,1", units='b/a, unitless'),
    ConfigField(
        "auditory_cues", "Interval onset cues", "choice", True, choices=(True, False)
    ),
    ConfigField(
        "cue_hz", "Cue frequency (study choice)", "int", 550, minimum=37, maximum=32767,
        units='Hz',
    ),
    ConfigField(
        "cue_ms",
        "Cue duration (study choice)",
        "int",
        35,
        minimum=1,
        maximum=1000,
        units="ms",
    ),
)
FIELDS += (
    ConfigField(
        "ring_conditions",
        "Matched conditions",
        "choice",
        "base_and_ring",
        choices=("base_and_ring", "base_only", "ring_only"),
    ),
)

RESPONSES = ResponseParadigm("ellipse_major_axis", ("first", "second"), ("1", "2"))
STIMULUS_SLOTS = {
    "fixation": "detection_scene",
    "first": "detection_scene",
    "second": "detection_scene",
}
STIMULUS_DEFAULTS = {slot: "detection_scene" for slot in STIMULUS_SLOTS}
PARADIGM = "two_interval_forced_choice"
SCIENTIFIC_SPEC = {
    "boundary_policy": "Saturate adaptive strength at the digital gamut bound; flat holds are not reversals. Positive float floor prevents log underflow. Boundary-affected estimates are flagged, not qualified thresholds.",
    "version": "ellipse_major_axis-4",
    "response": "Which temporal interval contains the line; first/second.",
    "quantity": "Digital line increment above background; optical contrast requires measured calibration.",
    "conditions": "TUI-selected positions/ratios, independent interleaved staircases; independent random alternatives.",
    "adaptive": "TUI n-down/n-up and log10 steps; standard counter semantics, no inherited pixel/reversal quirks.",
    "stopping": "Reversal completion; global ceiling is incomplete, not a successful threshold.",
    "exclusions": "No post-hoc deletion; abort/timeout/errors preserved.",
    "estimator": "Median final retained presented reversals; mean across all complete repeats.",
    "geometry": "Degrees; probe dimensions are selected stimulus parameters (defaults .013 wide x .133 high); ring uses nested ellipses with .16 degree axial inset, requiring visual qualification.",
}


# 2. CONDITIONS AND TRIAL ORDER


def make_conditions(settings):
    positions = [float(x) for x in settings["positions_deg"].split(",")]
    ratios = [float(x) for x in settings["aspect_ratios"].split(",")]
    rings = (
        [False, True]
        if settings["ring_conditions"] == "base_and_ring"
        else [settings["ring_conditions"] == "ring_only"]
    )
    rows = []
    for ratio in ratios:
        for position in positions:
            for ring in rings:
                value = f"x={position};ratio={ratio};ring={int(ring)}"
                for repeat in range(settings["staircases_per_condition"]):
                    rows.append(
                        {
                            "id": len(rows) + 1,
                            "value": value,
                            "x_deg": position,
                            "aspect_ratio": ratio,
                            "ring": ring,
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
        probe_y_deg=0.0,
        ring_radius_deg=0.6,
        ring_y_deg=0.0,
        aspect_ratio=condition["aspect_ratio"],
        ring_present=condition["ring"],
        ring_increment=settings["ring_increment"],
        flanker_present=False,
    )
    fixation = run.stimulus_parameters(
        "fixation",
        background=background,
        probe_present=False,
        ring_present=False,
        flanker_present=False,
    )
    first = run.stimulus_parameters(
        "first", **common, probe_present=condition["target"] == 0
    )
    second = run.stimulus_parameters(
        "second", **common, probe_present=condition["target"] == 1
    )
    return {"fixation": fixation, "first": first, "second": second}


# 4. ONE TRIAL


def make_trial(settings, condition):
    cue = (
        Beep(settings["cue_hz"], settings["cue_ms"])
        if settings["auditory_cues"]
        else None
    )
    return TrialTimeline(
        (
            Show("fixation", slot="fixation", duration="fixation_ms"),
            Show("interval_one", slot="first", duration="stimulus_ms", beep=cue),
            Show("inter_interval", slot="fixation", duration="isi_ms"),
            Show("interval_two", slot="second", duration="stimulus_ms", beep=cue),
            CollectResponse(actions=("first", "second"), slot="fixation"),
        )
    )


# 5. RESPONSES AND ADAPTATION


def interpret_response(condition, response):
    """Score the chosen alternative against this trial's assigned target."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def maximum_contrast(settings, condition):
    """Digital headroom for the additive scene (or symmetric grating)."""
    return (1
        - settings["background_intensity"]
        - (settings["ring_increment"] if condition["ring"] else 0))


def change_contrast(state, response, step):
    exponent = (
        -state["log_down"]
        if step == Step.DOWN
        else state["log_up"] if step == Step.UP else 0
    )
    # Saturate the adaptive value; an outward step at the bound is a flat hold.
    # Flat holds do not count as reversals. The requested step remains in events.
    return bounded_log_step(state["contrast"], exponent, maximum=state["maximum_contrast"])


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
        maximum=maximum_contrast(settings, condition),
        log_up=settings["logUNIT_UP"],
        log_down=settings["logUNIT_DW"],
        measurements={
            "probe_x_deg": condition["x_deg"],
            "staircase_repeat": condition["repeat"],
        },
        instructions=f"First interval: {run.responses.keys[0]}   Second interval: {run.responses.keys[1]}   Escape stops",
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
        # The user selects an absolute intensity. Adapt the digital difference
        # from background, so all existing log-step and threshold units persist.
        "contrasts": {c["id"]: settings["starting_probe_intensity"] - settings["background_intensity"] for c in conditions},
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
            "within_staircase": "median",
            "across_staircases": "arithmetic_mean",
            "retained_reversals": run.values["threshold_reversals"],
            "completion": "all configured staircases complete",
            "strength_bounds": {
                str(c["id"]): [sys.float_info.min, maximum_contrast(run.values, c)]
                for c in conditions
            },
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
        if "aspect_ratios" in values:
            ratios = [float(x) for x in values["aspect_ratios"].split(",")]
            if (
                not ratios
                or len(set(ratios)) != len(ratios)
                or any(not 0.5 <= x <= 1 for x in ratios)
            ):
                yield "Choose distinct ellipse aspect ratios within 0.5–1."
    except ValueError:
        yield "Enter finite comma-separated numeric condition values."
    if values["starting_probe_intensity"] < values["background_intensity"]:
        yield "Starting probe intensity must be at or above background for this bright-probe procedure."
    difference = values["starting_probe_intensity"] - values["background_intensity"]
    if 0 < difference < sys.float_info.min:
        yield "Starting probe intensity is closer to background than the positive log-staircase numeric floor; use exact background or a representable larger difference."
    if values["background_intensity"] == 1:
        yield "Background intensity of 1 leaves no headroom for this bright-probe log staircase."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Threshold reversal count exceeds reversal termination."
    if (
        (values["starting_probe_intensity"] - values["background_intensity"]) + (values["ring_increment"] or 0)
        > 1 - values["background_intensity"]
    ):
        yield "Starting probe intensity plus any additive ring/flanker layer exceeds 1. Review the scene headroom; no intensity was clipped."


def definition(identity="ellipse_major_axis"):
    return experiment(
        id=identity,
        name="Ellipse Major Axis (software validation)",
        procedure=procedure,
        description="Ellipse Major Axis",
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
        migrate_values=migrate_probe_intensity,
        supports_simulation=True,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        acquisition_block_reason="Scientific design implemented in degrees; measured luminance, effective contrast precision, frame timing and study-specific geometry must be qualified before human acquisition.",
        trial_column_overrides={
            "presented_display_contrast": {
                "units_or_encoding": "digital_probe_increment",
                "meaning": "Presented digital line increment above background.",
                "notes": "Stored directly as I_probe - I_background before subpixel area coverage. Not historical C_disp or calibrated optical contrast.",
            },
            "next_display_contrast": {
                "units_or_encoding": "digital_probe_increment",
                "meaning": "Post-response digital line increment above background.",
                "notes": "Stored directly as I_probe - I_background before subpixel area coverage. Not historical C_disp or calibrated optical contrast.",
            },
            "stimulus_condition": {"units_or_encoding": "x=degrees;ratio=minor/major axis;ring=0 or 1"},
        },
        source_paths=("src/psychophysics_lab/experiments/ellipse_major_axis.py",),
    )


SPEC = definition()
