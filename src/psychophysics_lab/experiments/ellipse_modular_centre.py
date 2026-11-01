"""Modular Ellipse Centre: independent ring, probe and fixation, ordered by trial.

This is a NEW study ID, not historical Ellipse Centre replay. A1 defines
scientific parameters and visible trial events; A2 defines the adaptive and
constant methods; B is the small, existing framework connection.

Bright display contrast C=(I_mark-I_background)/(1-I_background).
Order in Show(..., stimuli=...) defines transparent visual occlusion.
Neither digital values nor software tests establish measured photometry.
"""

from psychophysics_lab.analysis.primary import expected_staircases
import random
import sys
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod, run_contrast_experiment,
    parse_fixed_strengths, fixed_level_schedule,
)
from psychophysics_lab.methods.probe import unique_probe_conditions, fixed_probe_trial_record
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
    Stimulus,
    CollectResponse,
    UpdateAdaptive,
    Beep,
)

# PART A1 — EXPERIMENTAL CHOICES
# Question: which of the two ring intervals contains the bright probe line?
# Geometry/ring settings define conditions; first/second are target alternatives.
# Independent adaptive repeats are tracks; fixed repeats are cell presentations.
# Probe strength is headroom-normalized DISPLAY contrast, NOT a digital increment.
# Read fixation -> interval one -> ISI -> interval two -> response below.
# Both requested onset cues remain in the event list; they do not identify target.
# Study-specific values are editable; these defaults are illustrative only.

FIELDS = (
    ConfigField("fixation_ms", "Fixation duration", "int", 500, minimum=1, units="ms", help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.'),
    ConfigField(
        "stimulus_ms", "Stimulus interval duration", "int", 250, minimum=1, units="ms",
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
        "starting_probe_contrast", "Starting probe display contrast",
        "float", .04, minimum=0, maximum=1,
        units="fraction of upper digital headroom",
        help_text="C=(I_probe-I_background)/(1-I_background). Adaptive steps apply to C, not absolute pixel intensity.",
    ),
    ConfigField(
        "background_intensity",
        "Background intensity",
        "float",
        0.5,
        minimum=0,
        maximum=1,
        units='digital intensity, 0 to 1',
        help_text='Digital background command on the normalized zero-to-one scale. It changes available stimulus headroom; photometric calibration is required to interpret emitted luminance.',
    ),
    ConfigField(
        "n_down", "Consecutive correct answers before a decrease", "int", 4, minimum=1,
        units='consecutive correct responses',
        help_text='Consecutive correct responses required before a downward strength step. Increasing this count delays downward steps; it does not change the selected step magnitude.',
    ),
    ConfigField("n_up", "Consecutive errors before an increase", "int", 1, minimum=1, units='consecutive incorrect responses', help_text='Consecutive incorrect responses required before an upward strength step. Increasing this count delays upward steps; it does not change the selected step magnitude.'),
    ConfigField("logUNIT_UP", "Increase in probe display contrast", "float", 0.36, minimum=0.000001, units='log10 units', help_text="Multiply normalized probe display contrast by 10**step; hold at one."),
    ConfigField("logUNIT_DW", "Decrease in probe display contrast", "float", 0.30294, minimum=0.000001, units='log10 units', help_text="Multiply normalized display contrast by 10**(-step); a lower strength approaches background."),
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
        8,
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
    ConfigField("isi_ms", "Gap between intervals", "int", 250, minimum=1, units="ms", help_text='Scheduled silent/blank gap between the two stimulus intervals, in milliseconds; it changes their temporal separation.'),
    ConfigField(
        "ring_display_contrast", "Ellipse ring display contrast",
        "float", .2, minimum=0, maximum=1,
        units="fraction of upper digital headroom",
        help_text="C=(I_ring-I_background)/(1-I_background); not measured optical contrast.",
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
        "float", 6.0, minimum=0.17, maximum=20, units="degrees",
        help_text="Outer semi-major axis of the ellipse; aspect ratio sets the vertical semi-axis.",
    ),
    ConfigField(
        "ring_inset_deg", "Ring inner axial inset", "float", .16,
        minimum=.001, maximum=5, units="degrees",
        help_text="Subtract from BOTH ellipse semi-axes to form the inner boundary; not constant-width normal stroke.",
    ),
    ConfigField(
        "probe_length_deg", "Probe length", "float", 1.0,
        minimum=.001, maximum=20, units="degrees",
    ),
    ConfigField(
        "probe_width_deg", "Probe width", "float", .013,
        minimum=.0001, maximum=5, units="degrees",
    ),
    ConfigField(
        "auditory_cues", "Interval onset cues", "choice", True, choices=(True, False),
        help_text='Enable the experiment-declared auditory interval cues. This does not establish measured audio/display synchronization.',
    ),
    ConfigField(
        "cue_hz", "Cue frequency (study choice)", "int", 550, minimum=37, maximum=32767,
        units='Hz',
        help_text='Requested tone frequency of the auditory cue, in hertz; it changes the cue pitch.',
    ),
    ConfigField(
        "cue_ms",
        "Cue duration (study choice)",
        "int",
        35,
        minimum=1,
        maximum=1000,
        units="ms",
        help_text='Requested auditory cue duration in milliseconds; physical audio onset and duration require independent qualification.',
    ),
)
RESPONSES = ResponseParadigm("ellipse_modular_centre", ("first", "second"), ("1", "2"))
# An experiment chooses which atomic stimuli appear together and when.
STIMULUS_SLOTS = {
    "ring": "ellipse_ring",
    "probe": "probe_line",
    "fixation": "fixation",
    "ready_fixation": "fixation",
}
STIMULUS_DEFAULTS = {
    "ring": "ellipse_ring",
    "probe": "probe_line",
    "fixation": "gaussian_fixation_spot",
    "ready_fixation": "gaussian_fixation_spot",
}
PARADIGM = "two_interval_forced_choice"
FIELDS += (
    ConfigField(
        "contrast_method", "Contrast selection method", "choice", "adaptive",
        choices=("adaptive", "constant_stimuli"),
        section="Experiment", allow_legacy_default=True,
    ),
    ConfigField(
        "fixed_contrasts", "Fixed probe display contrasts", "text",
        "0.01,0.02,0.04", section="Constant stimuli",
        units="fraction of upper digital headroom", allow_legacy_default=True,
    ),
    ConfigField(
        "fixed_repetitions", "Trials per level per condition", "int", 10,
        minimum=1, section="Constant stimuli", allow_legacy_default=True,
    ),
)


# Session opening — once; readiness is not an accepted scientific response
# Edit the Python list directly. SESSION_START = [] disables the opening.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


# Chronological events — repeated from the current condition and strength
# One fresh flat event list per selected condition; effective strengths are prepared below.


def interval_stimuli(settings, condition, interval):
    """Source order = back to front; probe appears in only one interval."""
    placements = [
        Stimulus("ring", y_deg=settings["ellipse_centre_y_deg"]),
    ]
    if condition["target"] == interval:
        placements.append(Stimulus(
            "probe", x_deg=condition["x_deg"],
            y_deg=settings["ellipse_centre_y_deg"],
        ))
    # Fixation is visually on top of ring/probe at the centre of the display.
    placements.append(Stimulus("fixation"))
    return tuple(placements)


def trial_events(settings, condition):
    cue = Beep(settings["cue_hz"], settings["cue_ms"]) if settings["auditory_cues"] else None
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("interval_one", duration="stimulus_ms",
             stimuli=interval_stimuli(settings, condition, 0), beep=cue),
        Show("inter_interval", slot="fixation", duration="isi_ms"),
        Show("interval_two", duration="stimulus_ms",
             stimuli=interval_stimuli(settings, condition, 1), beep=cue),
        CollectResponse(actions=("first", "second"), slot="fixation"),
    ]


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


TRIAL_COLUMN_MEANINGS = {
    "presented_display_contrast": {
        "units_or_encoding": "headroom_normalized_bright_display_contrast",
        "meaning": "Presented headroom-normalized bright probe display contrast.",
        "notes": "C=(I_probe-I_background)/(1-I_background); new protocol only, not historical increment units or measured luminance.",
    },
    "next_display_contrast": {
        "units_or_encoding": "headroom_normalized_bright_display_contrast",
        "meaning": "Post-response headroom-normalized bright probe display contrast.",
        "notes": "C=(I_probe-I_background)/(1-I_background); new protocol only, not historical increment units or measured luminance.",
    },
    "stimulus_condition": {"units_or_encoding": "x=degrees;ratio=minor/major axis;ring=0 or 1"},
}


MEASUREMENT_UNITS = {
    "probe_x_deg": "degrees from fixation",
    "staircase_repeat": "1-based staircase repeat",
    "fixed_repeat": "1-based fixed repetition",
    "presented_display_contrast": "headroom-normalized bright display contrast",
    "aspect_ratio": "minor/major semi-axis ratio (unitless)",
    "ring": "boolean; False absent, True present",
}


REVIEW_INACTIVE_FIELDS = {
    "adaptive": ("fixed_contrasts", "fixed_repetitions"),
    "constant_stimuli": tuple(key for key in ADAPTIVE_RULE.controls if key != "max_trials")
                        + ("starting_probe_contrast", "threshold_reversals"),
}

CALIBRATION_REQUIREMENTS = ("geometry", "luminance", "timing")

MONITOR_CAPABILITIES = ("display_binding", "resolution")

ACQUISITION_BLOCK_REASON = "Scientific design implemented in degrees; measured luminance, effective contrast precision, frame timing and study-specific geometry must be qualified before human acquisition."


def trial_measurements(settings, condition):
    """Existing requested journal values; no new canonical columns."""
    return {
        "probe_x_deg": condition["x_deg"],
        "staircase_repeat": condition["repeat"],
    }


def response_instructions(responses):
    return f"First interval: {responses.keys[0]}   Second interval: {responses.keys[1]}   Escape stops"


# PART A2 — SCIENTIFIC METHODS

def prepare_stimuli(run, condition, state):
    """Atomic slot parameters; positions and occlusion belong to trial_events."""
    settings = run.values
    background = settings["background_intensity"]
    fixation = run.stimulus_parameters("fixation", background=background)
    return {
        "fixation": fixation,
        "ready_fixation": run.stimulus_parameters("ready_fixation", background=background),
        "ring": run.stimulus_parameters(
            "ring", background=background,
            display_contrast=settings["ring_display_contrast"],
            outer_radius_deg=settings["ring_radius_deg"],
            aspect_ratio=condition["aspect_ratio"],
            inner_inset_deg=settings["ring_inset_deg"],
        ),
        "probe": run.stimulus_parameters(
            "probe", background=background,
            display_contrast=condition["contrast"],
            length_deg=settings["probe_length_deg"],
            width_deg=settings["probe_width_deg"],
        ),
    }


SCIENTIFIC_SPEC = {
    "boundary_policy": "Saturate adaptive strength at the digital gamut bound; flat holds are not reversals. Positive float floor prevents log underflow. Boundary-affected estimates are flagged, not qualified thresholds.",
    "version": "ellipse_modular_centre-1",
    "response": "Which temporal interval contains the line; first/second.",
    "quantity": "Headroom-normalized bright probe and ring display contrasts; optical luminance unqualified.",
    "conditions": "TUI-selected aspect ratios and ellipse vertical centre; line is at ellipse centre x=0; independently interleaved repeat staircases and equiprobable first/second targets.",
    "adaptive": "TUI n-down/n-up and log10 steps; reversal direction starts at the actual initial presentation, holds ignored.",
    "stopping": "Reversal completion; global ceiling is incomplete, not a successful threshold.",
    "exclusions": "No post-hoc deletion; abort/timeout/errors preserved.",
    "estimator": "Median final retained presented reversals; mean across all complete repeats.",
    "geometry": "Independent ring/probe/fixation stimulus classes; ring inset is a researcher input in degrees; rendered in explicit back-to-front order.",
}


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


def interpret_response(condition, response):
    """Score the chosen alternative against this trial's assigned target."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


def maximum_contrast(settings, condition):
    """Probe increment bounded by resolved local pixel overlap, never remote layers."""
    return 1.0  # New bright display-contrast convention; overwrite, not additive, ring.


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
        starting_values={c["id"]: settings["starting_probe_contrast"] for c in conditions},
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
        # Staircase state and thresholds are normalized display contrasts.
        "contrasts": {c["id"]: settings["starting_probe_contrast"] for c in conditions},
        "reversals": {c["id"]: [] for c in conditions},
        "description": description,
    }


def fixed_levels(values):
    return parse_fixed_strengths(values["fixed_contrasts"], minimum=0, maximum=1)


def make_fixed_schedule(values, seed):
    conditions = unique_probe_conditions(make_conditions(values))
    levels = fixed_levels(values)
    planned = len(conditions)*len(levels)*values["fixed_repetitions"]
    if planned > values["max_trials"]:
        raise ValueError("Fixed-level plan exceeds the selected max_trials ceiling.")
    return fixed_level_schedule(
        conditions, levels, values["fixed_repetitions"], seed=seed,
        condition_field="value", strength_field="contrast",
    )


def validate_settings(values):
    import math
    try:
        ratios = [float(x) for x in values["aspect_ratios"].split(",")]
        if (not ratios or len(set(ratios)) != len(ratios)
                or any(not math.isfinite(r) or not .5 <= r <= 1 for r in ratios)):
            yield "Choose distinct finite ellipse ratios between 0.5 and 1."
        elif any(values["ring_radius_deg"]*ratio <= values["ring_inset_deg"] for ratio in ratios):
            yield "Both inner ellipse semi-axes must exceed the selected axial ring inset."
    except (ValueError, TypeError, OverflowError):
        yield "Enter finite comma-separated numeric ellipse ratios."
    if values["background_intensity"] >= 1:
        yield "Bright display contrast requires background below 1."
    if values["starting_probe_contrast"] <= 0:
        yield "Log staircases require strictly positive starting probe contrast."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Retained threshold reversal count exceeds the termination count."
    if values["contrast_method"] == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except (ValueError, TypeError, KeyError) as exc:
            yield str(exc)


# Stopping, scientific estimators and results
# Reversal completion is the adaptive goal; the global response ceiling is
# incomplete termination. Fixed levels have no staircase threshold estimator.


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
            "units": "headroom_normalized_bright_display_contrast",
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
    schedule = make_fixed_schedule(run.values, run.seed)
    return ConstantContrastMethod(
        run, schedule=schedule, condition_field="value",
        record=fixed_probe_trial_record,
        resolution={
            "trial_selection_method": "constant_stimuli",
            "scientific_quantity": "headroom_normalized_bright_display_contrast",
            "protocol": dict(SCIENTIFIC_SPEC),
            "condition_definitions": unique_probe_conditions(make_conditions(run.values)),
            "fixed_contrast_levels": list(fixed_levels(run.values)),
            "fixed_repetitions_per_level_per_condition": run.values["fixed_repetitions"],
            "planned_trials": len(schedule),
            "schedule": [
                {"trial_index": i, "scientific_condition": trial["value"],
                 "presented_display_contrast": trial["contrast"],
                 "target_alternative": trial["target"], "repeat": trial["repeat"]}
                for i, trial in enumerate(schedule, 1)
            ],
            "response_analysis": "Accuracy by display contrast; no staircase estimator.",
            "hardware_equivalence": False,
        },
    )


# PART B — FRAMEWORK INTEGRATION
# FRAMEWORK CONNECTION: same runner, recorder, Review hooks and public identity.
# Scientific choices/measurements are above; normally leave these bindings alone.
def trial_record(run, condition, state):
    settings = run.values
    return run.adaptive_trial_record(
        state["adaptive"],
        condition["id"],
        contrast=condition["contrast"],
        maximum=maximum_contrast(settings, condition),
        log_up=settings["logUNIT_UP"],
        log_down=settings["logUNIT_DW"],
        measurements=trial_measurements(settings, condition),
        instructions=response_instructions(run.responses),
    )

def procedure(run):
    # Scientific timeline and stimulus conversion stay above. The method
    # chooses the probe display contrast; RunContext still records the same TSV.
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

# Compatibility and registration
# Central compatibility for callers expecting make_trial(...).resolve(...).
make_trial = legacy_trial_factory(trial_events)


def definition(identity="ellipse_modular_centre"):
    return experiment(
        id=identity,
        name="Modular Ellipse Centre (software validation)",
        procedure=procedure,
        session_start=SESSION_START,
        stimulus_field_bindings={"ready_fixation": {"background": "background_intensity"}},
        description="Independent ellipse ring, probe and fixation; ordered transparent layers.",
        fields=FIELDS,
        scientific_spec=SCIENTIFIC_SPEC,
        responses=RESPONSES,
        adaptive=ADAPTIVE_RULE,
        method_planner=make_fixed_schedule,
        method_reviewer={"constant_stimuli": constant_contrast_method},
        # Review-only control links; acquisition bindings remain unchanged.
        stimulus_parameter_controls={
            "ring": {
                "background": "background_intensity",
                "display_contrast": "ring_display_contrast",
                "outer_radius_deg": "ring_radius_deg",
                "inner_inset_deg": "ring_inset_deg",
                "aspect_ratio": "aspect_ratios",
            },
            "probe": {
                "background": "background_intensity",
                "length_deg": "probe_length_deg",
                "width_deg": "probe_width_deg",
            },
            "fixation": {"background": "background_intensity"},
            "ready_fixation": {"background": "background_intensity"},
        },
        # End Review-only control links.
        validator=validate_settings,
        supports_simulation=True,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=CALIBRATION_REQUIREMENTS,
        monitor_capabilities=MONITOR_CAPABILITIES,
        acquisition_block_reason=ACQUISITION_BLOCK_REASON,
        trial_column_overrides=TRIAL_COLUMN_MEANINGS,
        source_paths=("src/psychophysics_lab/experiments/ellipse_modular_centre.py",),
    )


SPEC = definition()
