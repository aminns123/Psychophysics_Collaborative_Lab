"""THESIS CSF — which side contained the grating?

Read top to bottom: settings -> what is shown -> one trial -> contrast updates
-> the experiment. Thesis Chapter 4, Fig. 4.3A and Tables 4.3–4.4.
This is a new protocol (csf_thesis), not a reinterpretation of older CSF runs.
The software protocol is implemented; raster/photometric equivalence is unverified.
"""
import random
from statistics import median, mean
from psychophysics_lab.researcher import (
    ConfigField, experiment, ResponseParadigm, AdaptiveSelection, StaircaseConfig,
    Step, TrialTimeline, Show, Stimulus, CollectResponse, UpdateAdaptive, UpdateState,
)

# 1. THESIS DEFAULTS: the TUI supplies the selected settings for each run.
FIXATION_MS = 500
GRATING_MS = 300
GRATING_OFFSET_DEG = .5
GAUSSIAN_SIGMA_DEG = 1.
CORRECT_BEFORE_DECREASE = 4
LOG_INCREASE = .36
LOG_DECREASE = .30294
REVERSALS_TO_FINISH = 10
STAIRCASES_PER_FREQUENCY = 4  # thesis permits 2–4 independent CSF staircases


# 2. ONE TRIAL: fixation -> grating alone -> fixation while awaiting LEFT/RIGHT.
def one_trial(side):
    x = -GRATING_OFFSET_DEG if side == "left" else GRATING_OFFSET_DEG
    return TrialTimeline((
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("grating", stimuli=(Stimulus("grating", x_deg=x),), duration="grating_ms"),
        CollectResponse(actions=("left", "right"), slot="fixation"),
    ))


# 3. RESPONSE -> NEXT CONTRAST: use the log steps selected in the TUI.
# Shared AdaptiveRun owns counters so they are tested consistently across experiments:
# correct answers reset the incorrect streak and vice versa; a step resets its streak.
# Optional initial one-down ends at the first error or selected response count (0 = off).
# Reversals are changes between nonzero adjustments; holds are ignored. The first
# recorded next contrast seeds direction tracking; starting contrast is not another observation.
# This file owns the chosen settings, contrast equation, scheduling and estimator.
def change_contrast(state, response, step):
    exponent = -state["log_down"] if step == Step.DOWN else state["log_up"] if step == Step.UP else 0
    contrast = state["contrast"] * 10**exponent
    if not 0 < contrast <= state["maximum_contrast"]:
        raise ValueError("Next contrast exceeds the display range; stop and review starting contrast/background, without clipping.")
    return contrast


# 4. RUN: interleave independent staircases; randomise left/right on each trial.
def procedure(run):
    if not run.synthetic:
        raise ValueError(SPEC.acquisition_block_reason)
    settings = run.values
    frequencies = [float(f.strip()) for f in settings["frequencies_cpd"].split(",")]
    conditions = [(f, repeat+1) for f in frequencies for repeat in range(settings["staircases_per_condition"])]
    staircase = run.adaptive({i: StaircaseConfig(settings["n_down"], settings["n_up"], settings["reversal_termination"],
                                                        settings["initial_one_down_limit"])
                              for i in range(1, len(conditions)+1)}, settings["max_trials"])
    contrasts = {i: settings["starting_contrast"] for i in staircase.states}
    reversals = {i: [] for i in staircase.states}
    randomise = random.Random(run.seed)
    background = settings["background_intensity"]
    description = {
        "protocol": "thesis Chapter 4, Fig. 4.3A; fixation -> grating -> self-paced spatial response",
        "timings_ms": {"fixation": settings["fixation_ms"], "grating": settings["grating_ms"], "response": 0},
        "frequencies_cpd": frequencies, "staircases_per_condition": settings["staircases_per_condition"],
        "target_offset_deg": GRATING_OFFSET_DEG, "gaussian_sigma_deg": GAUSSIAN_SIGMA_DEG,
        "background_digital_intensity": background, "random_seed": run.seed,
        "adaptive_rule": {"algorithm": SPEC.adaptive.algorithm_id, "n_down": settings["n_down"], "n_up": settings["n_up"],
                          "log_up": settings["logUNIT_UP"], "log_down": settings["logUNIT_DW"],
                          "reversal_limit": settings["reversal_termination"],
                          "initial_one_down_limit": settings["initial_one_down_limit"], "max_trials": settings["max_trials"]},
        "reversal_contrast_convention": "presented contrast at a change in adjustment direction",
        "contrast_units": "digital peak-to-peak sinusoidal modulation; not calibrated optical Michelson contrast",
        "threshold_rule": "median final selected number of reversal contrasts per complete staircase, arithmetic mean across complete condition",
        "threshold_reversals": settings["threshold_reversals"],
        "hardware_equivalence": False,
    }
    run.initialise(expected_trials=settings["max_trials"], resolution=description, background_intensity=background)
    while staircase.status == "running":
        identity = staircase.select(randomise.choice)
        frequency, repeat = conditions[identity-1]
        target = randomise.randrange(2)  # 0 = left; 1 = right. Correctness is equality with the response.
        side = ("left", "right")[target]
        contrast = contrasts[identity]
        previous_reversals = staircase.states[identity].reversal_count
        def record_adjustment(state, response):
            current = staircase.states[identity]
            return dict(state) | {"reversal": int(current.reversal_count > previous_reversals),
                "reversal_count": current.reversal_count, "staircase_complete": int(current.complete)}
        trial = TrialTimeline(one_trial(side).phases + (
            UpdateAdaptive(staircase, identity, change_contrast, state_key="next_contrast"),
            UpdateState(record_adjustment, name="record_staircase_change"),
        ))
        run.play_trial(trial, target=target, condition=frequency, adaptive_record=staircase,
            parameters_by_slot={
                "grating": run.stimulus_parameters("grating", sigma_deg=GAUSSIAN_SIGMA_DEG,
                    spatial_frequency_cpd=frequency, contrast=contrast, background=background),
                "fixation": run.stimulus_parameters("fixation", background=background),
            },
            state={"contrast": contrast, "maximum_contrast": 2*min(background, 1-background),
                   "log_up": settings["logUNIT_UP"], "log_down": settings["logUNIT_DW"],
                   "next_contrast": None, "staircase_id": identity,
                   "staircase_trial_index": staircase.states[identity].trial_count+1,
                   "reversal": None, "reversal_count": None, "staircase_complete": None},
            record_from_state={"staircase_id": "staircase_id", "staircase_trial_index": "staircase_trial_index", "presented_display_contrast": "contrast",
                               "next_display_contrast": "next_contrast", "reversal": "reversal",
                               "reversal_count": "reversal_count", "staircase_complete": "staircase_complete"},
            measurements={"spatial_frequency_cpd": frequency, "staircase_repeat": repeat,
                          "grating_x_deg": -GRATING_OFFSET_DEG if target == 0 else GRATING_OFFSET_DEG},
            instructions=f"Left: {run.responses.keys[0]}   Right: {run.responses.keys[1]}")
        contrasts[identity] = run.trial_state["next_contrast"]
        if staircase.states[identity].reversal_count > previous_reversals:
            reversals[identity].append(contrast)
        run.save_adaptive(staircase, value_column="next_display_contrast")
    # Thesis point estimator. Incomplete conditions never receive a fabricated threshold.
    thresholds = {i: median(values[-settings["threshold_reversals"]:])
                  for i, values in reversals.items() if staircase.states[i].complete}
    condition_thresholds = {}
    for frequency in frequencies:
        ids = [i for i, condition in enumerate(conditions, 1) if condition[0] == frequency]
        if all(i in thresholds for i in ids):
            threshold = mean(thresholds[i] for i in ids)
            condition_thresholds[str(frequency)] = {"threshold": threshold, "sensitivity": 1/threshold}
    run.save_resolution(**(description | {"reversal_contrasts": {str(i): r for i, r in reversals.items()},
        "staircase_thresholds": {str(i): t for i, t in thresholds.items()}, "condition_thresholds": condition_thresholds}))
    run.complete_adaptive(staircase)


def validate_settings(values):
    try:
        frequencies = [float(f.strip()) for f in values["frequencies_cpd"].split(",")]
        import math
        if not frequencies or len(set(frequencies)) != len(frequencies) or any(not math.isfinite(f) or not .5 <= f <= 32 for f in frequencies):
            yield "Choose distinct finite spatial frequencies within 0.5–32 cycles/degree."
    except ValueError:
        yield "Enter spatial frequencies as comma-separated numbers in cycles/degree."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Threshold reversal count must not exceed the staircase reversal limit."
    if values["starting_contrast"] > 2*min(values["background_intensity"], 1-values["background_intensity"]):
        yield "Starting contrast exceeds the available digital range."


# 5. TUI CONNECTION: optional run overrides; no separate scientific JSON or registry edit.
SPEC = experiment(
    id="csf_thesis", name="CSF — thesis procedure (software validation)", procedure=procedure,
    description="500 ms fixation, 300 ms grating at +/-0.5 degrees, LEFT/RIGHT; thesis adaptive defaults, editable in the TUI.",
    fields=(
        ConfigField("frequencies_cpd", "Spatial frequencies (cpd; select at least 8 for a full thesis CSF)", "text", "2,8"),
        ConfigField("fixation_ms", "Fixation duration", "int", FIXATION_MS, minimum=1, units="ms"),
        ConfigField("grating_ms", "Grating duration", "int", GRATING_MS, minimum=1, units="ms"),
        ConfigField("staircases_per_condition", "Independent staircases per frequency", "int", STAIRCASES_PER_FREQUENCY, minimum=1),
        ConfigField("starting_contrast", "Starting digital modulation", "float", .1, minimum=.000001, maximum=1),
        ConfigField("background_intensity", "Digital background (requires measured calibration for acquisition)", "float", .5, minimum=.001, maximum=.999),
        ConfigField("n_down", "Consecutive correct answers before decreasing contrast", "int", CORRECT_BEFORE_DECREASE, minimum=1),
        ConfigField("n_up", "Consecutive incorrect answers before increasing contrast", "int", 1, minimum=1),
        ConfigField("logUNIT_UP", "Contrast increase (log10 units)", "float", LOG_INCREASE, minimum=.000001),
        ConfigField("logUNIT_DW", "Contrast decrease (log10 units)", "float", LOG_DECREASE, minimum=.000001),
        ConfigField("initial_one_down_limit", "Initial one-down responses (0 disables; thesis default)", "int", 0, minimum=0, maximum=1000),
        ConfigField("reversal_termination", "Reversals required per staircase", "int", REVERSALS_TO_FINISH, minimum=1),
        ConfigField("threshold_reversals", "Final reversals used for the threshold median", "int", 8, minimum=1),
        ConfigField("max_trials", "Software safety ceiling (not scientific completion)", "int", 10000, minimum=1),
    ),
    responses=ResponseParadigm("csf_spatial_location", ("left", "right"), ("LEFT", "RIGHT")),
    adaptive=AdaptiveSelection("consecutive_up_down",
        controls=("n_down", "n_up", "logUNIT_UP", "logUNIT_DW", "initial_one_down_limit",
                  "staircases_per_condition", "reversal_termination", "max_trials"),
        step_calculator="garcia_perez_1998", step_parameterization="log10_display_contrast"), validator=validate_settings, supports_simulation=True,
    stimulus_slots={"fixation": "thesis_fixation", "grating": "thesis_csf"},
    stimulus_defaults={"fixation": "thesis_gaussian_fixation", "grating": "thesis_csf_grating"},
    calibration_requirements=("geometry", "luminance", "timing"), monitor_capabilities=("display_binding", "resolution"),
    acquisition_block_reason="Thesis protocol implemented for software tests; raster aperture, grayscale precision, calibrated contrast/luminance and physical timing must be qualified before human acquisition. The 2,8 cpd defaults are a short software example, not the thesis frequency list.",
    source_paths=("src/psychophysics_lab/experiments/csf_thesis.py",),
)
