"""Gaussian CSF: which side contained the Gaussian-windowed grating?

Investigation example, not an official protocol replacement. Part A contains
the scientific decisions; Part B connects them to the existing execution path.
Default source/preset overrides still apply. See ../README.md.
"""
import math
import random
from psychophysics_lab.analysis.primary import expected_staircases
import sys
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod, run_contrast_experiment,
    fixed_level_schedule, parse_fixed_strengths,
)
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, AdaptiveSelection, StaircaseConfig, Step, UpdateAdaptive, Show, Stimulus,
    CollectResponse, WaitForKey, Beep, experiment, legacy_trial_factory,
)

# PART A1 — EXPERIMENTAL CHOICES
# Everyday edits: declared values, conditions, targets, events and measurements.
EXPERIMENT_ID = "demolab__csf_two_part"
GRATING_STIMULUS = "contrast_sensitivity_grating"  # Existing Gaussian renderer.
FIXATION_STIMULUS = "gaussian_fixation"
CALIBRATION_REQUIREMENTS = ("geometry", "luminance", "timing")
MONITOR_CAPABILITIES = ("display_binding", "resolution")
ACQUISITION_BLOCK_REASON = "Reference candidate; independent researcher and protocol acceptance outstanding."
STIMULUS_SLOTS = {"grating": "contrast_sensitivity_grating", "fixation": "gaussian_fixation", "ready_fixation": "gaussian_fixation"}
STIMULUS_DEFAULTS = {"grating": GRATING_STIMULUS, "fixation": FIXATION_STIMULUS, "ready_fixation": FIXATION_STIMULUS}
FIXATION_MS = 500
GRATING_MS = 300
DEFAULT_GRATING_OFFSET_DEG = 1.0
GAUSSIAN_SIGMA_DEG = 0.5
CORRECT_BEFORE_DECREASE = 4
CORRECT_BEFORE_INCREASE = 1
LOG_INCREASE = 0.36
LOG_DECREASE = 0.30294
REVERSALS_TO_FINISH = 10
STAIRCASES_PER_FREQUENCY = 4
PARADIGM = 'two_alternative_forced_choice'
FIELDS = (
    ConfigField('frequencies_cpd', 'Spatial frequencies (cpd; select at least 8 for a full CSF)', 'text', '2,8',
        units='cycles/degree', help_text='Carrier spatial frequencies to test, in cycles per visual degree. Each selected frequency is a scientific condition; larger values require finer display sampling.'),
    ConfigField('contrast_method', 'Contrast selection method', 'choice', 'adaptive',
        allow_legacy_default=True, choices=('adaptive', 'constant_stimuli'), help_text='Select adaptive staircases (unchanged) or fixed contrast levels. Both use the same spatial-frequency conditions and saved trial table.', section='Experiment'),
    ConfigField('fixed_contrasts', 'Fixed digital peak-to-peak contrast levels', 'text', '0.02,0.04,0.08,0.16',
        allow_legacy_default=True, help_text="Constant stimuli only. Comma-separated digital grating modulation (not calibrated luminance contrast). Zero is an intentional catch level; levels must be distinct and within the selected background's digital gamut.", section='Constant stimuli'),
    ConfigField('fixed_repetitions', 'Presentations per contrast level per scientific condition', 'int', 10,
        minimum=1, section='Constant stimuli', allow_legacy_default=True, help_text='Each selected spatial frequency is a scientific condition. Each condition and contrast-level pair receives this many presentations; conditions can mean something else in other experiments. The max_trials field is a configurable safety ceiling.', units='trials'),
    ConfigField('fixation_ms', 'Fixation duration', 'int', FIXATION_MS,
        minimum=1, units='ms', help_text='Scheduled fixation phase duration before the stimulus, in milliseconds; this is not a measured photon-onset duration.'),
    ConfigField('grating_ms', 'Grating duration', 'int', GRATING_MS,
        minimum=1, units='ms', help_text='Scheduled grating exposure duration in milliseconds; changing it changes the stimulus phase, not measured photon timing.'),
    ConfigField('grating_offset_deg', 'Grating centre eccentricity (left/right)', 'float', DEFAULT_GRATING_OFFSET_DEG,
        minimum=sys.float_info.min, units='degrees', help_text='Positive angular distance from fixation. Left and right targets use opposite signs.'),
    ConfigField('grating_sigma_deg', 'Gaussian grating envelope sigma', 'float', GAUSSIAN_SIGMA_DEG,
        minimum=0.001, maximum=5.0, units='degrees', help_text='Gaussian standard deviation, not a hard radius; the grating smoothly fades to background at the separately selected cutoff.'),
    ConfigField('grating_cutoff_sigmas', 'Grating outer edge (multiples of sigma)', 'float', 3.0,
        minimum=1.0, maximum=5.0, units='multiples of sigma', help_text='Support radius = sigma × cutoff; diameter = 2 × sigma × cutoff. The taper occupies the outer one sigma, so 1.5 is valid (radius 1.5° and width 3° at sigma 1°). Exact background outside support.'),
    ConfigField('staircases_per_condition', 'Independent staircases per frequency', 'int', STAIRCASES_PER_FREQUENCY,
        minimum=1, units='staircases', help_text='Number of independently updated adaptive staircases in each scientific condition. More staircases divide accepted responses across more adaptive tracks.'),
    ConfigField('starting_contrast', 'Starting digital modulation', 'float', 0.1,
        minimum=sys.float_info.min, maximum=1, units='digital peak-to-peak modulation', help_text='Initial digital peak-to-peak grating modulation for adaptive tracks. The carrier amplitude before its envelope is half this value; it is not measured optical contrast.'),
    ConfigField('background_intensity', 'Digital background (requires measured calibration for acquisition)', 'float', 0.5,
        minimum=0.001, maximum=0.999, units='digital intensity, 0 to 1', help_text='Digital background command on the normalized zero-to-one scale. It changes available stimulus headroom; photometric calibration is required to interpret emitted luminance.'),
    ConfigField('n_down', 'Consecutive correct answers before decreasing contrast', 'int', CORRECT_BEFORE_DECREASE,
        minimum=1, units='consecutive correct responses', help_text='Consecutive correct responses required before a downward strength step. Increasing this count delays downward steps; it does not change the selected step magnitude.'),
    ConfigField('n_up', 'Consecutive incorrect answers before increasing contrast', 'int', CORRECT_BEFORE_INCREASE,
        minimum=1, units='consecutive incorrect responses', help_text='Consecutive incorrect responses required before an upward strength step. Increasing this count delays upward steps; it does not change the selected step magnitude.'),
    ConfigField('logUNIT_UP', 'Contrast increase (log10 units)', 'float', LOG_INCREASE,
        minimum=1e-06, units='log10 units', help_text='Upward step in base-10 logarithmic strength units: multiply the controlled strength by 10 raised to this value, subject to the method bounds.'),
    ConfigField('logUNIT_DW', 'Contrast decrease (log10 units)', 'float', LOG_DECREASE,
        minimum=1e-06, units='log10 units', help_text='Downward step in base-10 logarithmic strength units: divide the controlled strength by 10 raised to this value, subject to the method bounds.'),
    ConfigField('initial_one_down_limit', 'Initial one-down responses (0 disables; default)', 'int', 0,
        minimum=0, maximum=1000, units='responses', help_text='Maximum initial accepted responses per staircase using a one-correct downward rule. The first incorrect response ends this phase early; subsequent responses use the selected consecutive-correct rule. Zero disables the initial phase.'),
    ConfigField('reversal_termination', 'Reversals required per staircase', 'int', REVERSALS_TO_FINISH,
        minimum=1, units='reversals', help_text='Reversal count required to complete each adaptive staircase. A reversal is a change of step direction; the safety ceiling can stop the run before this goal.'),
    ConfigField('threshold_reversals', 'Final reversals used for the threshold median', 'int', 8,
        minimum=1, units='reversals', help_text='Number of final eligible reversal values included in the declared threshold summary. Too few eligible reversals makes that estimator unavailable.'),
    ConfigField('max_trials', 'Software safety ceiling (not scientific completion)', 'int', 10000,
        minimum=1, units='responses', help_text='Accepted-response safety ceiling used by the selected adaptive/fixed method. Fixed plans exceeding it are rejected; adaptive stopping at this ceiling does not establish threshold convergence.'),
)

# Target alternatives are positions, not frequency conditions. Index is the
# correct response code. Selected response_keys may override these defaults.
TARGETS = (
    {"name": "left", "key": "LEFT", "x_sign": -1, "y_sign": 0},
    {"name": "right", "key": "RIGHT", "x_sign": 1, "y_sign": 0},
)
RESPONSES = ResponseParadigm("csf_spatial", tuple(t["name"] for t in TARGETS),
                            tuple(t["key"] for t in TARGETS))
ONSET_BEEP = None  # Optional Beep(550, 35); deliberate protocol change.
RESPONSE_BEEP = None  # Optional accepted-response Beep(750, 35).

SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation", instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]  # Write [] to disable; never a scientific response or random draw.


def target_position(settings, condition):
    option = TARGETS[condition["target"]]
    return {"x_deg": settings["grating_offset_deg"] * option["x_sign"],
            "y_deg": settings["grating_offset_deg"] * option["y_sign"]}


def trial_events(settings, condition):
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("grating", stimuli=(Stimulus("grating", **target_position(settings, condition)),),
             duration="grating_ms", beep=ONSET_BEEP),
        CollectResponse(actions=RESPONSES.alternatives, slot="fixation", beep=RESPONSE_BEEP),
    ]




def scientific_conditions(settings):
    """Factor levels, not response sides or independent staircase tracks."""
    return [{"frequency_cpd": float(value.strip())}
            for value in settings["frequencies_cpd"].split(",")]


MEASUREMENT_UNITS = {
    "spatial_frequency_cpd": "cycles/degree", "staircase_repeat": "count, 1-based",
    "target_name": "category", "target_x_deg": "degrees", "target_y_deg": "degrees",
    "requested_digital_peak_to_peak": "normalised digital modulation",
    "gaussian_sigma_deg": "degrees",
}


def trial_measurements(settings, condition):
    return {"spatial_frequency_cpd": condition["frequency_cpd"],
            "staircase_repeat": condition["repeat"],
            "target_name": TARGETS[condition["target"]]["name"],
            "target_x_deg": target_position(settings, condition)["x_deg"],
            "target_y_deg": target_position(settings, condition)["y_deg"],
            "requested_digital_peak_to_peak": condition["contrast"],
            "gaussian_sigma_deg": settings["grating_sigma_deg"]}


TRIAL_COLUMN_MEANINGS = {
    "presented_display_contrast": {
        "units_or_encoding": "digital_peak_to_peak",
        "meaning": "Presented digital peak-to-peak sinusoidal modulation.",
        "notes": "Stored before Gaussian weighting: background + (strength/2) * Gaussian * sine. Not historical C_disp or calibrated optical contrast.",
    },
    "next_display_contrast": {
        "units_or_encoding": "digital_peak_to_peak",
        "meaning": "Post-response digital peak-to-peak sinusoidal modulation.",
        "notes": "Stored before Gaussian weighting: background + (strength/2) * Gaussian * sine. Not historical C_disp or calibrated optical contrast.",
    },
    "stimulus_condition": {"units_or_encoding": "cycles/degree"},
}


# PART A2 — SCIENTIFIC METHODS
# Inspectable methods; deliberate edits require renewed scientific validation.
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


SCIENTIFIC_SPEC = {
    "boundary_policy": "Saturate adaptive strength at the digital gamut bound; flat holds are not reversals. Positive float floor prevents log underflow. Boundary-affected estimates are flagged, not qualified thresholds.",
    "version": "csf-spatial-3",
    "response": "Left or right grating location; researcher-selected offset and target/response alternative equality.",
    "quantity": "Digital peak-to-peak grating modulation; not optical Michelson contrast.",
    "conditions": "TUI frequency list; independent staircases, uniform active selection, independent equiprobable target sides.",
    "adaptive": "TUI-selected consecutive n-down/n-up log10 changes, initial phase and reversal limit. No guaranteed target probability for arbitrary settings.",
    "stopping": "Each staircase completes at its reversal limit; global response ceiling is incomplete termination.",
    "exclusions": "No post-hoc response exclusion. Timeout/abort/errors preserve accepted input. Adaptive strength saturates at the declared digital bound (flat holds are not reversals); invalid physical renderer commands are rejected without silent clipping.",
    "estimator": "Median final TUI-selected presented reversal contrasts per complete staircase; mean across all configured staircases of a complete frequency.",
}


def make_conditions(settings):
    """Legacy planning hook: independent TRACKS, frequency x repeat.

    Frequency is the scientific condition; id is a 1-based staircase identity.
    The target side is selected independently for each presentation.
    """
    return [
        {"id": i, "frequency_cpd": condition["frequency_cpd"], "repeat": repeat + 1}
        for i, (condition, repeat) in enumerate(
            ((condition, repeat) for condition in scientific_conditions(settings)
             for repeat in range(settings["staircases_per_condition"])), 1)
    ]


def fixed_contrast_levels(settings):
    """Parse experiment-selected digital grating modulation, not physical luminance contrast."""
    maximum = 2 * min(settings["background_intensity"], 1-settings["background_intensity"])
    try:
        return parse_fixed_strengths(
            settings["fixed_contrasts"], minimum=0, maximum=maximum
        )
    except ValueError as exc:
        if "between" in str(exc):
            raise ValueError(
                f"Fixed digital peak-to-peak contrasts must be between 0 and {maximum:g} "
                f"at background intensity {settings['background_intensity']:g}. No silent clipping."
            ) from exc
        raise


def fixed_conditions(settings, seed):
    """Deterministic condition x contrast x repeat schedule; independent of responses.

    Condition is spatial frequency, exactly as for adaptive CSF. Within each
    frequency/contrast cell, targets are balanced for even repeats and differ
    by at most one for odd repeats. Shuffle before presenting any trial.
    """
    frequencies = [c["frequency_cpd"] for c in scientific_conditions(settings)]
    levels = fixed_contrast_levels(settings)
    repetitions = settings["fixed_repetitions"]
    count = len(frequencies) * len(levels) * repetitions
    if count > settings["max_trials"]:
        raise ValueError(
            f"Constant stimuli plans {count} trials, exceeding the selected "
            f"max_trials safety ceiling ({settings['max_trials']}). Increase the "
            "ceiling deliberately or reduce conditions/levels/repetitions."
        )
    return fixed_level_schedule(frequencies, levels, repetitions, seed=seed)


def choose_condition(run, conditions, state):
    staircase, randomise = state["adaptive"], state["rng"]
    identity = staircase.select(randomise.choice)
    condition = dict(conditions[identity - 1])
    condition.update(
        target=randomise.randrange(2),
        value=condition["frequency_cpd"],
        contrast=state["contrasts"][identity],
        previous_reversals=staircase.states[identity].reversal_count,
    )
    return condition


def interpret_response(condition, response):
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Target and recorded correctness disagree.")
    return dict(response) | {"correct": correct}


def prepare_stimuli(run, condition, state):
    background = run.values["background_intensity"]
    return {
        "grating": run.stimulus_parameters(
            "grating",
            sigma_deg=run.values["grating_sigma_deg"],
            cutoff_sigmas=run.values["grating_cutoff_sigmas"],
            spatial_frequency_cpd=condition["frequency_cpd"],
            contrast=condition["contrast"],
            background=background,
        ),
        "fixation": run.stimulus_parameters("fixation", background=background),
    }


def maximum_contrast(settings, condition):
    return 2 * min(settings["background_intensity"], 1 - settings["background_intensity"])


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


def initialise_experiment(run, conditions, *, grating_resolution=None):
    settings = run.values
    frequencies = list(dict.fromkeys(c["frequency_cpd"] for c in conditions))
    staircase = run.adaptive(
        {
            i: StaircaseConfig(
                settings["n_down"],
                settings["n_up"],
                settings["reversal_termination"],
                settings["initial_one_down_limit"],
            )
            for i in range(1, len(conditions) + 1)
        },
        settings["max_trials"],
        starting_values={c["id"]: settings["starting_contrast"] for c in conditions},
    )
    contrasts = {i: settings["starting_contrast"] for i in staircase.states}
    reversals = {i: [] for i in staircase.states}
    randomise = random.Random(f"{run.seed}:conditions")
    background = settings["background_intensity"]
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
        "protocol": "fixation -> grating -> self-paced spatial response",
        "measurement_units": MEASUREMENT_UNITS,
        "timings_ms": {
            "fixation": settings["fixation_ms"],
            "grating": settings["grating_ms"],
            "response": 0,
        },
        "frequencies_cpd": frequencies,
        "staircases_per_condition": settings["staircases_per_condition"],
        "target_offset_deg": settings["grating_offset_deg"],
        **({
            "gaussian_sigma_deg": settings["grating_sigma_deg"],
            "grating_cutoff_sigmas": settings["grating_cutoff_sigmas"],
            "grating_taper": "raised cosine over outer 1 Gaussian sigma; zero modulation outside cutoff radius",
            "grating_support_radius_deg": settings["grating_sigma_deg"] * settings["grating_cutoff_sigmas"],
        } if grating_resolution is None else grating_resolution),
        "background_digital_intensity": background,
        "random_seed": run.seed,
        "adaptive_rule": {
            "algorithm": SPEC.adaptive.algorithm_id,
            "n_down": settings["n_down"],
            "n_up": settings["n_up"],
            "log_up": settings["logUNIT_UP"],
            "log_down": settings["logUNIT_DW"],
            "reversal_limit": settings["reversal_termination"],
            "initial_one_down_limit": settings["initial_one_down_limit"],
            "max_trials": settings["max_trials"],
        },
        "reversal_contrast_convention": "presented contrast at a change in adjustment direction",
        "contrast_units": "digital peak-to-peak sinusoidal modulation; not calibrated optical Michelson contrast",
        "threshold_rule": "median final selected number of reversal contrasts per complete staircase, arithmetic mean across complete condition",
        "threshold_reversals": settings["threshold_reversals"],
        "hardware_equivalence": False,
    }
    run.initialise(
        expected_trials=settings["max_trials"],
        resolution=description | {"primary_estimator": primary_rule(settings, conditions),
                                  "expected_staircases": expected_staircases(conditions)},
        background_intensity=background,
    )
    return {
        "adaptive": staircase,
        "rng": randomise,
        "contrasts": contrasts,
        "reversals": reversals,
        "description": description,
    }


def validate_settings(values):
    try:
        frequencies = [float(f.strip()) for f in values["frequencies_cpd"].split(",")]
        import math

        if (
            not frequencies
            or len(set(frequencies)) != len(frequencies)
            or any(not math.isfinite(f) or not 0.5 <= f <= 32 for f in frequencies)
        ):
            yield "Choose distinct finite spatial frequencies within 0.5-32 cycles/degree."
    except ValueError:
        yield "Enter spatial frequencies as comma-separated numbers in cycles/degree."
    if values.get("contrast_method", "adaptive") == "constant_stimuli":
        try:
            # Seed-independent validation; scheduling uses the recorded run seed.
            fixed_conditions(values, 0)
        except ValueError as exc:
            yield str(exc)
    else:
        if values["threshold_reversals"] > values["reversal_termination"]:
            yield "Threshold reversal count must not exceed the staircase reversal limit."
        if values["starting_contrast"] > 2 * min(
            values["background_intensity"], 1 - values["background_intensity"]
        ):
            yield "Starting contrast exceeds the available digital range."
    if len(TARGETS) != 2 or len({t["name"] for t in TARGETS}) != 2:
        yield "This binary CSF design needs two distinct target alternatives."
    positions = [(t["x_sign"], t["y_sign"]) for t in TARGETS]
    if len(set(positions)) != 2 or any(x not in (-1, 0, 1) or y not in (-1, 0, 1) for x, y in positions):
        yield "Targets need distinct positions with coordinate signs -1, 0 or 1."



def validate_monitor(settings, profile):
    """Check actual condition frequencies before physical presentation.

    Editing and simulation remain available with display feedback at Review.
    """
    if profile.expected_resolution_px:
        import math
        from psychophysics_lab.stimuli.spatial_calibration import resolve_spatial_geometry, validate_requested_cpd
        frequencies = [condition["frequency_cpd"] for condition in make_conditions(settings)]
        geometry = resolve_spatial_geometry(profile, profile.expected_resolution_px)
        # Match the raster backend's conservative limit on both pixel axes.
        validate_requested_cpd(frequencies, geometry)
        validate_requested_cpd(frequencies, geometry, orientation_rad=math.pi / 2)


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
            "units": "digital_peak_to_peak",
        }


def finish_experiment(run, conditions, state):
    run.save_resolution(**(state["description"] | {
        "reversal_contrasts": {str(i): v for i, v in state["reversals"].items()}}))
    run.complete_adaptive(state["adaptive"])
    run.save_primary(primary_rule(run.values, conditions), conditions)


def fixed_resolution(settings, schedule, seed):
    """Fixed-level results are accuracy by frequency/level; no threshold fit."""
    return {"trial_selection_method": "constant_stimuli", "schedule": schedule,
            "planned_trials": len(schedule), "random_seed": seed,
            "measurement_units": MEASUREMENT_UNITS,
            "response_analysis": "Per-frequency/per-level accuracy; no threshold"}


# PART B — FRAMEWORK INTEGRATION
# Connect the declared science to existing execution, recording and registration.


def _measurements(settings, condition):
    values = trial_measurements(settings, condition)
    if set(values) != set(MEASUREMENT_UNITS) or any(
        not isinstance(v, (str, int, float, bool)) or
        (isinstance(v, (int, float)) and not math.isfinite(v)) for v in values.values()
    ):
        raise ValueError("trial_measurements must supply every declared finite scalar measurement.")
    return values


def _record(run, condition, state=None):
    measurements = _measurements(run.values, condition)
    instructions = "   ".join(f"{a}: {k}" for a, k in zip(run.responses.alternatives, run.responses.keys))
    if state is not None:
        return run.adaptive_trial_record(state["adaptive"], condition["id"],
            contrast=condition["contrast"], maximum=maximum_contrast(run.values, condition),
            log_up=run.values["logUNIT_UP"], log_down=run.values["logUNIT_DW"],
            measurements=measurements, instructions=instructions)
    return {"state": {"contrast": condition["contrast"]},
            "record_from_state": {"presented_display_contrast": "contrast"},
            "measurements": measurements, "instructions": instructions}


def _fixed(run):
    schedule = fixed_conditions(run.values, run.seed)
    return ConstantContrastMethod(run, schedule=schedule, record=_record,
                                  resolution=fixed_resolution(run.values, schedule, run.seed))


def procedure(run):
    return run_contrast_experiment(run,
        methods={"adaptive": lambda: AdaptiveContrastMethod(run,
            make_conditions=make_conditions, initialise=initialise_experiment, select=choose_condition,
            record=_record, update=update_experiment, finished=is_finished, finish=finish_experiment),
            "constant_stimuli": lambda: _fixed(run)},
        prepare_stimuli=prepare_stimuli, trial_events=trial_events,
        interpret_response=interpret_response)


make_trial = legacy_trial_factory(trial_events)
SPEC = experiment(
    id=EXPERIMENT_ID, name="Scientist-first Gaussian CSF reference candidate",
    description=__doc__, procedure=procedure, fields=FIELDS, responses=RESPONSES,
    session_start=SESSION_START, adaptive=ADAPTIVE_RULE, method_planner=fixed_conditions,
    validator=validate_settings, monitor_validator=validate_monitor,
    stimulus_slots=STIMULUS_SLOTS,
    stimulus_defaults=STIMULUS_DEFAULTS,
    stimulus_parameter_controls={
        "grating": {"sigma_deg": "grating_sigma_deg", "cutoff_sigmas": "grating_cutoff_sigmas", "background": "background_intensity"},
        "fixation": {"background": "background_intensity"}},
    stimulus_field_bindings={"ready_fixation": {"background": "background_intensity"}},
    scientific_spec=SCIENTIFIC_SPEC | {"version": "csf-spatial-authoring-standard-candidate-1", "measurements": MEASUREMENT_UNITS},
    trial_column_overrides=TRIAL_COLUMN_MEANINGS,
    calibration_requirements=CALIBRATION_REQUIREMENTS,
    monitor_capabilities=MONITOR_CAPABILITIES, supports_simulation=True,
    acquisition_block_reason=ACQUISITION_BLOCK_REASON,
    source_paths=(f"experiments/{EXPERIMENT_ID}.py",),
)
