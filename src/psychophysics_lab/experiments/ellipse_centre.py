"""Ellipse Centre: a scientific design in visual degrees, separate from historical replay.

Researcher-defined psychophysics procedure. Study-specific
choices remain TUI controls; unspecified ring digital increment must
be supplied rather than copied from historical pixels. No claim of calibrated
physical contrast or timing is made by this software implementation.
"""

from psychophysics_lab.analysis.primary import expected_staircases
import random
import sys
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.experiments._internal.parameter_compatibility import migrate_probe_intensity
from psychophysics_lab.methods.contrast import AdaptiveContrastMethod, run_contrast_experiment
from psychophysics_lab.methods.probe import (
    probe_contrast_fields, probe_constant_method, validate_probe_fixed_settings,
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
    Beep,
)

# 1. SETTINGS AND STIMULI
FIELDS = (
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
        minimum=0,
        maximum=1,
        units='normalised digital increment above background',
        help_text="Ring pixels = background + increment, not absolute intensity or measured luminance. Range 0 to 1-background; probe overlap can reduce local headroom. Ignored for absent rings.",
    ),
    ConfigField("aspect_ratios", "Ellipse b/a ratios", "text", "0.5,0.75,1",
                units="minor/major axis ratio (unitless)",
                help_text="Comma-separated ratios from 0.5 to 1; each ratio defines a condition."),
    ConfigField(
        "ellipse_centre_y_deg", "Ellipse and probe centre vertical position",
        "float", 0.6, minimum=-5, maximum=5, units="degrees",
        help_text="Common y coordinate of ellipse and probe, relative to fixation; 0 is fixation.",
    ),
    ConfigField(
        "ring_radius_deg", "Ellipse outer horizontal radius",
        "float", 0.5, minimum=0.17, maximum=3, units="degrees",
        help_text="Outer semi-major axis of the ellipse; aspect ratio sets the vertical semi-axis.",
    ),
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
RESPONSES = ResponseParadigm("ellipse_centre", ("first", "second"), ("1", "2"))
STIMULUS_SLOTS = {
    "fixation": "detection_scene",
    "first": "detection_scene",
    "second": "detection_scene",
}
STIMULUS_DEFAULTS = {slot: "detection_scene" for slot in STIMULUS_SLOTS}
PARADIGM = "two_interval_forced_choice"
FIELDS += probe_contrast_fields()

SCIENTIFIC_SPEC = {
    "boundary_policy": "Saturate adaptive strength at the digital gamut bound; flat holds are not reversals. Positive float floor prevents log underflow. Boundary-affected estimates are flagged, not qualified thresholds.",
    "version": "ellipse_centre-5",
    "response": "Which temporal interval contains the line; first/second.",
    "quantity": "Digital line increment above background; optical contrast requires measured calibration.",
    "conditions": "TUI-selected aspect ratios and ellipse vertical centre; line is at ellipse centre x=0; independently interleaved repeat staircases and equiprobable first/second targets.",
    "adaptive": "TUI n-down/n-up and log10 steps; reversal direction starts at the actual initial presentation, holds ignored.",
    "stopping": "Reversal completion; global ceiling is incomplete, not a successful threshold.",
    "exclusions": "No post-hoc deletion; abort/timeout/errors preserved.",
    "estimator": "Median final retained presented reversals; mean across all complete repeats.",
    "geometry": "Degrees; probe dimensions are selected stimulus parameters; ring uses nested ellipses with .16 degree axial inset, requiring visual qualification.",
}


# 2. CONDITIONS AND TRIAL ORDER


def make_conditions(settings):
    # Every condition places the line at the centre of a visible ellipse.
    ratios = [float(x) for x in settings["aspect_ratios"].split(",")]
    rows = []
    for ratio in ratios:
        for repeat in range(settings["staircases_per_condition"]):
            rows.append(
                {
                    "id": len(rows) + 1,
                    "value": f"x=0.0;ratio={ratio};ring=1",
                    "x_deg": 0.0,
                    "aspect_ratio": ratio,
                    "ring": True,
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
        probe_y_deg=settings["ellipse_centre_y_deg"],
        ring_radius_deg=settings["ring_radius_deg"],
        ring_y_deg=settings["ellipse_centre_y_deg"],
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
    """Probe increment bounded by resolved local pixel overlap, never remote layers."""
    return condition.get("maximum_probe_increment", 1 - settings["background_intensity"])


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
    from psychophysics_lab.experiments._internal.detection_limits import resolve_probe_limits
    resolve_probe_limits(run, conditions, prepare_stimuli)
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
        starting_values={c["id"]: settings["starting_probe_intensity"] - settings["background_intensity"]
                         for c in conditions},
    )
    # Fixed n-down/one-up steps have this asymptotic accuracy target. Finite
    # reversal estimates (especially with lapses) still require recovery checks.
    # Normalise first: two individually finite large steps can overflow
    # when added directly. This is algebraically the same step-size ratio.
    step_scale = max(settings["logUNIT_UP"], settings["logUNIT_DW"])
    relative_up = settings["logUNIT_UP"] / step_scale
    relative_down = settings["logUNIT_DW"] / step_scale
    accuracy_target = (
        (relative_up / (relative_up + relative_down))
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
        "ellipse_centre_y_deg": settings["ellipse_centre_y_deg"],
        "ring_radius_deg": settings["ring_radius_deg"],
        "hardware_equivalence": False,
    }
    run.initialise(
        expected_trials=settings["max_trials"],
        resolution=description | {"primary_estimator": primary_rule(settings, conditions),
                                  "expected_staircases": expected_staircases(conditions)},
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


def primary_rule(settings, conditions):
    return {
            "version": 1,
            "value_column": "presented_display_contrast",
            "within_staircase": "median",
            "across_staircases": "arithmetic_mean",
            "retained_reversals": settings["threshold_reversals"],
            "completion": "all configured staircases complete",
            "strength_bounds": {
                str(c["id"]): [sys.float_info.min, maximum_contrast(settings, c)]
                for c in conditions
            },
            "units": "digital_probe_increment",
        }


def finish_experiment(run, conditions, state):
    run.save_resolution(
        **(
            state["description"]
            | {"reversal_contrasts": {str(i): v for i, v in state["reversals"].items()}}
        )
    )
    run.complete_adaptive(state["adaptive"])
    # One declared estimator is used here and by post-hoc analysis.
    run.save_primary(primary_rule(run.values, conditions), conditions)


def adaptive_contrast_method(run):
    """Use this study's original staircase rules; no algorithm or RNG change."""
    return AdaptiveContrastMethod(
        run,
        make_conditions=make_conditions,
        initialise=initialise_experiment,
        select=choose_condition,
        record=trial_record,
        update=update_experiment,
        finished=is_finished,
        finish=finish_experiment,
    )


def constant_contrast_method(run):
    """Use shared level scheduling; retain our scientific conditions and trials."""
    return probe_constant_method(
        run, make_conditions, prepare_stimuli, scientific_spec=SCIENTIFIC_SPEC,
    )


def procedure(run):
    # Scientific timeline and stimulus conversion stay above. The method
    # chooses the probe increment; RunContext still records the same TSV.
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_contrast_method(run),
            "constant_stimuli": lambda: constant_contrast_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )


# 7. FRAMEWORK CONNECTION


def validate_settings(values):
    import math

    try:
        if "aspect_ratios" in values:
            ratios = [float(x) for x in values["aspect_ratios"].split(",")]
            if (
                not ratios
                or len(set(ratios)) != len(ratios)
                or any(not 0.5 <= x <= 1 for x in ratios)
            ):
                yield "Choose distinct ellipse aspect ratios within 0.5Ã¢â‚¬â€œ1."
            elif any(values["ring_radius_deg"] * ratio <= 0.16 for ratio in ratios):
                yield (f"Ellipse inner axes must be positive: a={values['ring_radius_deg']:g} deg, "
                       f"b=a*(b/a)={[round(values['ring_radius_deg']*r, 8) for r in ratios]} deg. "
                       f"Both must exceed the 0.16 deg inner-axis inset; for these ratios choose a > {0.16/min(ratios):g} deg "
                       f"or each b/a > {0.16/values['ring_radius_deg']:g}.")
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
    if values["ring_increment"] is not None and values["ring_increment"] > 1 - values["background_intensity"]:
        yield (f"Ring increment {values['ring_increment']:g} plus background {values['background_intensity']:g} "
               f"exceeds 1; allowed ring increment is [0, {1-values['background_intensity']:g}].")
    # Probe/ring overlap is checked on the resolved stimulus grid before acquisition.

    # Fixed levels use the same scientific conditions but no staircase IDs.
    yield from validate_probe_fixed_settings(values, make_conditions)



def definition(identity="ellipse_centre"):
    return experiment(
        id=identity,
        name="Ellipse Centre (software validation)",
        procedure=procedure,
        description="Ellipse Centre",
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
        source_paths=("src/psychophysics_lab/experiments/ellipse_centre.py",),
    )


SPEC = definition()
