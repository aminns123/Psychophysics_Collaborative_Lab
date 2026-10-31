"""Line Position Flanker: a scientific design in visual degrees, separate from historical replay.

Researcher-defined psychophysics procedure. Study-specific
choices remain TUI controls; vertical separation and observer-specific flanker frequency
must be supplied rather than copied from historical pixels. No prior CSF run is required. No claim of calibrated
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
    make_probe_fixed_schedule,
)
from psychophysics_lab.researcher import (
    ConfigField,
    experiment,
    ResponseParadigm,
    AdaptiveSelection,
    StaircaseConfig,
    Step,
    TrialTimeline,
    WaitForKey,
    legacy_trial_factory,
    Show,
    CollectResponse,
    Beep,
    UpdateAdaptive,
)

# 1. PARAMETERS
FIELDS = (
    ConfigField(
        "positions_deg",
        "Probe x positions (degrees; choose study sampling)",
        "text",
        "-0.4,0,0.5",
        units='degrees',
        help_text="Probe position conditions in visual degrees in this experiment's declared reference coordinates. Each entry adds a tested condition; Review geometry shows the actual placement.",
    ),
    ConfigField("fixation_ms", "Fixation duration", "int", 500, minimum=1, units="ms", help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.'),
    ConfigField(
        "stimulus_ms", "Stimulus interval duration", "int", 300, minimum=1, units="ms",
        help_text='Scheduled stimulus exposure duration in milliseconds; changing it changes the trial timeline, not measured display qualification.',
    ),
    ConfigField(
        "staircases_per_condition",
        "Independent staircases per condition",
        "int",
        4,
        minimum=1,
        units='staircases',
        help_text='Number of independently updated adaptive staircases in each scientific condition. More staircases divide accepted responses across more adaptive tracks.',
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
        help_text="The inducing grating adds +/-0.009. Background must be in [0.009, 0.991] so the grating stays in gamut. Only pixels where the probe overlaps the flanker share headroom.",
    ),
    ConfigField(
        "n_down", "Consecutive correct answers before a decrease", "int", 4, minimum=1,
        units='consecutive correct responses',
        help_text='Consecutive correct responses required before a downward strength step. Increasing this count delays downward steps; it does not change the selected step magnitude.',
    ),
    ConfigField("n_up", "Consecutive errors before an increase", "int", 1, minimum=1, units='consecutive incorrect responses', help_text='Consecutive incorrect responses required before an upward strength step. Increasing this count delays upward steps; it does not change the selected step magnitude.'),
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
        help_text='Maximum initial accepted responses per staircase using a one-correct downward rule. The first incorrect response ends this phase early; subsequent responses use the selected consecutive-correct rule. Zero disables the initial phase.',
    ),
    ConfigField(
        "reversal_termination", "Reversals per staircase", "int", 10, minimum=1,
        units='reversals',
        help_text='Reversal count required to complete each adaptive staircase. A reversal is a change of step direction; the safety ceiling can stop the run before this goal.',
    ),
    ConfigField(
        "threshold_reversals",
        "Final reversals retained for threshold",
        "int",
        5,
        minimum=1,
        units='reversals',
        help_text='Number of final eligible reversal values included in the declared threshold summary. Too few eligible reversals makes that estimator unavailable.',
    ),
    ConfigField(
        "max_trials",
        "Global safety ceiling; reaching it is incomplete",
        "int",
        10000,
        minimum=1,
        units='responses',
        help_text='Accepted-response safety ceiling used by the selected adaptive/fixed method. Fixed plans exceeding it are rejected; adaptive stopping at this ceiling does not establish threshold convergence.',
    ),
)
FIELDS += (
    ConfigField("auditory_cues", "Beep at probe onset and accepted response", "choice", False,
                choices=(False, True), help_text="Optional Windows sound; does not indicate correctness. Speaker onset is uncalibrated."),
    ConfigField("cue_hz", "Beep frequency", "int", 550, minimum=37, maximum=32767, units="Hz", help_text="Used only when auditory cues are enabled."),
    ConfigField("cue_ms", "Beep duration", "int", 35, minimum=1, maximum=1000, units="ms", help_text="Used only when auditory cues are enabled."),
    ConfigField(
        "probe_vertical_offset_deg",
        "Probe centre above/below fixation (required)",
        "float",
        None,
        minimum=0.001,
        maximum=5,
        units="degrees",
        help_text="Distance from fixation to probe centre, not pixels or total separation. At x=0, a displacement smaller than half the selected probe length puts the line across fixation. For an appearance check, try 0.2 degrees; choose the study value yourself.",
    ),
)
FIELDS += (
    ConfigField(
        "flanker_cpd",
        "Flanker spatial frequency (required)",
        "float",
        None,
        minimum=0.01,
        maximum=32,
        units="cycles/degree",
        help_text='Spatial frequency of the flanker grating in cycles per visual degree. This changes the flanker pattern and its sampling requirements, not the probe condition coordinates.',
    ),
)

RESPONSES = ResponseParadigm(
    "line_position_flanker", ("above", "below"), ("UP", "DOWN")
)
STIMULUS_SLOTS = {"fixation": "detection_scene", "first": "detection_scene"}
STIMULUS_DEFAULTS = {slot: "detection_scene" for slot in STIMULUS_SLOTS}
PARADIGM = "two_alternative_forced_choice"
FIELDS += probe_contrast_fields()

# A pure, session-only fixation; trial slots and their defaults stay unchanged.
STIMULUS_SLOTS["ready_fixation"] = "gaussian_fixation"
STIMULUS_DEFAULTS["ready_fixation"] = "gaussian_fixation"


# 2. SESSION START — ONCE
# Edit the Python list directly. SESSION_START = [] disables the opening.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


# 3. TRIAL EVENTS — REPEATED
# One fresh flat event list per selected condition; effective strengths are prepared below.


def trial_events(settings, condition):
    """Fixation -> probe/flanker scene -> above/below answer with existing cues."""
    cue = Beep(settings["cue_hz"], settings["cue_ms"]) if settings["auditory_cues"] else None
    return [
        Show('fixation', slot='fixation', duration='fixation_ms'),
        Show('probe', slot='first', duration='stimulus_ms', beep=cue),
        CollectResponse(actions=('above', 'below'), slot='fixation', beep=cue),
    ]


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


# 4. SCIENTIFIC RULES — CONDITIONS AND UPDATES


SCIENTIFIC_SPEC = {
    "boundary_policy": "Saturate adaptive strength at the digital gamut bound; flat holds are not reversals. Positive float floor prevents log underflow. Boundary-affected estimates are flagged, not qualified thresholds.",
    "version": "line_position_flanker-5",
    "response": "Is the line above or below fixation?",
    "quantity": "Digital line increment above background; optical contrast requires measured calibration.",
    "conditions": "TUI-selected horizontal probe positions; independently interleaved repeat staircases and equiprobable above/below targets.",
    "adaptive": "TUI n-down/n-up and log10 steps; reversal direction starts at the actual initial presentation, holds ignored.",
    "stopping": "Reversal completion; global ceiling is incomplete, not a successful threshold.",
    "exclusions": "No post-hoc deletion; abort/timeout/errors preserved.",
    "estimator": "Geometric mean final retained presented reversals; mean across all complete repeats.",
    "geometry": "Probe width/length come from the selected DetectionScene parameters; displacement is an experiment setting. Flanker 5 degree square at x=-3 degrees; digital peak-to-peak modulation .018; frequency selected independently by the researcher.",
}


ADAPTIVE_RULE = AdaptiveSelection(
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
)


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
    if values["starting_probe_intensity"] < values["background_intensity"]:
        yield "Starting probe intensity must be at or above background for this bright-probe procedure."
    difference = values["starting_probe_intensity"] - values["background_intensity"]
    if 0 < difference < sys.float_info.min:
        yield "Starting probe intensity is closer to background than the positive log-staircase numeric floor; use exact background or a representable larger difference."
    if not 0.009 <= values["background_intensity"] <= 0.991:
        yield f"Background intensity {values['background_intensity']:g} must be in [0.009, 0.991]: flanker bands add/subtract 0.009."
    if values["background_intensity"] == 1:
        yield "Background intensity of 1 leaves no headroom for this bright-probe log staircase."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Threshold reversal count exceeds reversal termination."
    # Local overlap is checked on the resolved stimulus grid before acquisition.


    # Validate selected fixed strengths without disturbing monitor sampling checks.
    yield from validate_probe_fixed_settings(values, make_conditions)


def validate_monitor(settings, profile):
    """Check the selected inducing frequency on the physical display, not a preset default."""
    if profile.expected_resolution_px:
        import math
        from psychophysics_lab.stimuli.spatial_calibration import resolve_spatial_geometry, validate_requested_cpd
        geometry = resolve_spatial_geometry(profile, profile.expected_resolution_px)
        validate_requested_cpd([settings["flanker_cpd"]], geometry)
        validate_requested_cpd([settings["flanker_cpd"]], geometry, orientation_rad=math.pi / 2)


# 5. STOPPING AND RESULTS
# Require completed reversals for the primary adaptive result; a safety ceiling
# is incomplete. Fixed levels report responses/accuracy without a threshold fit.


TRIAL_COLUMN_MEANINGS = {
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
    "stimulus_condition": {"units_or_encoding": "horizontal probe coordinate in degrees"},
}


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
        instructions=f"Above: {run.responses.keys[0]}   Below: {run.responses.keys[1]}   Escape stops",
    )


def is_finished(run, conditions, state):
    return state["adaptive"].status != "running"


def primary_rule(settings, conditions):
    return {
            "version": 1,
            "value_column": "presented_display_contrast",
            "within_staircase": "geometric_mean",
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
        trial_events=trial_events,
        interpret_response=interpret_response,
    )


# 6. FRAMEWORK REGISTRATION — MINIMAL AND LAST
# Central compatibility for callers expecting make_trial(...).resolve(...).
make_trial = legacy_trial_factory(trial_events)


def definition(identity="line_position_flanker"):
    return experiment(
        id=identity,
        name="Line Position Flanker (software validation)",
        procedure=procedure,
        session_start=SESSION_START,
        stimulus_field_bindings={"ready_fixation": {"background": "background_intensity"}},
        description="Line Position Flanker",
        fields=FIELDS,
        scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        adaptive=ADAPTIVE_RULE,
        method_planner=lambda settings, seed: make_probe_fixed_schedule(settings, seed, make_conditions),
        validator=validate_settings,
        migrate_values=migrate_probe_intensity,
        monitor_validator=validate_monitor,
        supports_simulation=True,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        acquisition_block_reason="Scientific design implemented in degrees; measured luminance, effective contrast precision, frame timing and study-specific geometry must be qualified before human acquisition.",
        trial_column_overrides=TRIAL_COLUMN_MEANINGS,
        source_paths=("src/psychophysics_lab/experiments/line_position_flanker.py",),
    )


SPEC = definition()
