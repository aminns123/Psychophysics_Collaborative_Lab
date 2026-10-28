"""Gaussian CSF: which side contained the Gaussian-windowed grating?

Investigation example, not an official protocol replacement. Part A contains
the scientific decisions; Part B connects them to the existing execution path.
Default source/preset overrides still apply. See ../README.md.
"""
import math
import sys
import hashlib
from pathlib import Path
from psychophysics_lab.experiments import contrast_sensitivity as reference
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod, run_contrast_experiment,
)
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, Step, UpdateAdaptive, Show, Stimulus,
    CollectResponse, WaitForKey, Beep, experiment, legacy_trial_factory,
)

# PART A — SCIENTIFIC METHODS
# Question, parameters and units. Digital modulation is not optical contrast.
EXPERIMENT_ID = "demolab__csf_two_part"
GRATING_STIMULUS = "contrast_sensitivity_grating"  # Existing Gaussian renderer.
FIXATION_STIMULUS = "gaussian_fixation"
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


# Frequency x staircase repetition; uniformly select an unfinished staircase,
# then independently choose left/right. This retains the reference RNG order.
def make_conditions(settings):
    frequencies = [float(f.strip()) for f in settings["frequencies_cpd"].split(",")]
    return [
        {"id": i, "frequency_cpd": frequency, "repeat": repeat + 1}
        for i, (frequency, repeat) in enumerate(
            (
                (f, r)
                for f in frequencies
                for r in range(settings["staircases_per_condition"])
            ),
            1,
        )
    ]

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


# Constant stimuli: frequency x digital modulation x repetitions; targets
# balanced within each cell, then shuffled with seed+"constant-stimuli".
# Reuse the exact reference planner and its gamut/count validation.
fixed_conditions = reference.make_fixed_schedule


def interpret_response(condition, response):
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Target and recorded correctness disagree.")
    return dict(response) | {"correct": correct}


# Stop at each track's reversal limit; max_trials is incomplete termination.
# primary_rule above: median last threshold_reversals PRESENTED reversal
# contrasts, then arithmetic mean over all completed tracks of a frequency.
# Constant stimuli reports cell accuracy; it fits no threshold.
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


def validate_settings(settings):
    if hashlib.sha256(Path(reference.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != REFERENCE_SHA256:
        yield "The qualified CSF reference changed; review equivalence and update this investigation before Test/Ready."
    yield from reference.validate_settings(settings)
    if len(TARGETS) != 2 or len({t["name"] for t in TARGETS}) != 2:
        yield "This binary CSF design needs two distinct target alternatives."
    positions = [(t["x_sign"], t["y_sign"]) for t in TARGETS]
    if len(set(positions)) != 2 or any(x not in (-1, 0, 1) or y not in (-1, 0, 1) for x, y in positions):
        yield "Targets need distinct positions with coordinate signs -1, 0 or 1."


# PART B — EXISTING PSYCOLAB INTEGRATION
REFERENCE_SHA256 = "691ead34d8947acb79dbc880f115418a925cf2a489128434c3633378485d1de0"
# Official-experiment callbacks are not part of the generic extension readiness
# dependency list. Pin the reviewed reference (LF-normalised SHA256); fail
# closed after its changes. Git line-ending conversion is not a science change.
# No new runner, condition manager, recorder or TUI. Renderer mathematics and
# staircase initialisation remain in their established named implementations.
def _measurements(settings, condition):
    values = trial_measurements(settings, condition)
    if set(values) != set(MEASUREMENT_UNITS) or any(
        not isinstance(v, (str, int, float, bool)) or
        (isinstance(v, (int, float)) and not math.isfinite(v)) for v in values.values()
    ):
        raise ValueError("trial_measurements must supply every declared finite scalar measurement.")
    return values


def _record(run, condition, state=None):
    entry = (reference.trial_record(run, condition, state) if state is not None
             else reference.fixed_trial_record(run, condition))
    entry["measurements"] = _measurements(run.values, condition)
    entry["instructions"] = "   ".join(f"{a}: {k}" for a, k in zip(run.responses.alternatives, run.responses.keys))
    return entry


def _start(run, conditions):
    state = reference.initialise_experiment(run, conditions)
    state["description"]["measurement_units"] = MEASUREMENT_UNITS
    return state


def _finish(run, conditions, state):
    run.save_resolution(**(state["description"] | {
        "reversal_contrasts": {str(i): v for i, v in state["reversals"].items()}}))
    run.complete_adaptive(state["adaptive"])
    run.save_primary(primary_rule(run.values, conditions), conditions)


def _fixed(run):
    schedule = fixed_conditions(run.values, run.seed)
    return ConstantContrastMethod(run, schedule=schedule, record=_record,
        resolution={"trial_selection_method": "constant_stimuli", "schedule": schedule,
                    "planned_trials": len(schedule), "random_seed": run.seed,
                    "measurement_units": MEASUREMENT_UNITS,
                    "response_analysis": "Per-frequency/per-level accuracy; no threshold"})


def procedure(run):
    return run_contrast_experiment(run,
        methods={"adaptive": lambda: AdaptiveContrastMethod(run,
            make_conditions=make_conditions, initialise=_start, select=choose_condition,
            record=_record, update=update_experiment, finished=is_finished, finish=_finish),
            "constant_stimuli": lambda: _fixed(run)},
        prepare_stimuli=reference.prepare_stimuli, trial_events=trial_events,
        interpret_response=interpret_response)


prepare_stimuli = reference.prepare_stimuli
initialise_experiment = _start  # Existing generic Review planning names.
make_trial = legacy_trial_factory(trial_events)
SPEC = experiment(
    id=EXPERIMENT_ID, name="Scientist-first Gaussian CSF investigation",
    description=__doc__,
    procedure=procedure, fields=FIELDS, responses=RESPONSES, session_start=SESSION_START,
    adaptive=reference.ADAPTIVE_RULE, method_planner=fixed_conditions,
    validator=validate_settings, monitor_validator=reference.validate_monitor,
    stimulus_slots=reference.STIMULUS_SLOTS,
    stimulus_defaults={"grating": GRATING_STIMULUS, "fixation": FIXATION_STIMULUS,
                       "ready_fixation": FIXATION_STIMULUS},
    stimulus_parameter_controls=reference.SPEC.stimulus_parameter_controls,
    stimulus_field_bindings=reference.SPEC.stimulus_field_bindings,
    scientific_spec=dict(reference.SCIENTIFIC_SPEC) | {
        "version": "csf-spatial-two-part-investigation-1", "measurements": MEASUREMENT_UNITS},
    trial_column_overrides=reference.TRIAL_COLUMN_MEANINGS,
    calibration_requirements=reference.SPEC.calibration_requirements,
    monitor_capabilities=reference.SPEC.monitor_capabilities, supports_simulation=True,
    acquisition_block_reason="Investigation prototype; protocol qualification has not been accepted.",
    source_paths=(f"experiments/{EXPERIMENT_ID}.py",),
)
