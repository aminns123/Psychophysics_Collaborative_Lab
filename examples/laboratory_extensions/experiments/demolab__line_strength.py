"""Line-side discrimination at two eccentricities using installed methods.

Strength is a digital increment above grey 0.5: I_line = 0.5 + strength.
It is neither absolute intensity nor a calibrated luminance contrast. The
finite adaptive demonstration has no threshold estimator. Fixed repetitions
are per eccentricity and level; left/right alternatives are balanced there.
Copy this example with the laboratory folder, then Test and mark Ready.
"""
from psychophysics_lab.stimulus_library import LinePatch
from psychophysics_lab.methods.contrast import (
    ConstantContrastMethod, fixed_level_schedule, parse_fixed_strengths,
    run_contrast_experiment,
)
from psychophysics_lab.methods.teaching import (
    TeachingAdaptiveMethod, fixed_teaching_record, review_teaching_adaptive,
    teaching_method_fields, teaching_adaptive_fields,
)
from psychophysics_lab.researcher import (
    AdaptiveSelection, ConfigField, ResponseParadigm, experiment,
    TrialTimeline, Show, Stimulus, CollectResponse,
)


# 1. SETTINGS AND STIMULI
FIELDS = (
    ConfigField("eccentricities_deg", "Line eccentricities", "text", "1,2",
                units="degrees", section="Stimulus conditions",
                help_text="Positive distances from fixation; each is one scientific condition."),
    ConfigField("trial_count", "Accepted adaptive responses", "int", 8, minimum=1),
    ConfigField("fixation_ms", "Fixation", "int", 300, minimum=1, units="ms", section="Timing"),
    ConfigField("stimulus_ms", "Line duration", "int", 200, minimum=1, units="ms", section="Timing"),
) + teaching_method_fields(strengths="0,0.1,0.3", label="Line increment above grey 0.5") + teaching_adaptive_fields()
RESPONSES = ResponseParadigm("line_side", ("left", "right"), ("F", "J"))


def eccentricities(settings):
    return parse_fixed_strengths(settings["eccentricities_deg"], minimum=.1, maximum=5)


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(settings):
    positions = eccentricities(settings)
    return [{"value": positions[i % len(positions)], "target": (i // len(positions)) % 2}
            for i in range(settings["trial_count"])]


def choose_condition(run, conditions, state):
    return conditions[run.accepted_trials]


def make_fixed_schedule(settings, seed):
    levels = parse_fixed_strengths(settings["fixed_contrasts"], maximum=.5)
    positions = eccentricities(settings)
    count = len(positions) * len(levels) * settings["fixed_repetitions"]
    if count > settings["max_trials"]:
        raise ValueError("Planned presentations exceed the selected max_trials safety ceiling.")
    return fixed_level_schedule(positions, levels, settings["fixed_repetitions"],
                                seed=seed, condition_field="eccentricity_deg")


# 3. PREPARE STIMULI
def prepare_stimuli(run, condition, state):
    return {"target": run.stimulus_parameters(intensity=.5 + condition["contrast"])}


# 4. ONE TRIAL
def make_trial(settings, condition):
    x = (-1 if condition["target"] == 0 else 1) * condition["value"]
    return TrialTimeline((
        Show("fixation", duration="fixation_ms", instructions="+"),
        Show("line", stimuli=(Stimulus("target", x_deg=x),), duration="stimulus_ms"),
        CollectResponse(actions=RESPONSES.alternatives, instructions="Left: {left}   Right: {right}"),
    ))


# 5. RESPONSE INTERPRETATION
def interpret_response(condition, response):
    if response["correct"] != (response["alternative"] == condition["target"]):
        raise ValueError("Recorded response disagrees with the scientific target.")
    return response


def validate_settings(settings):
    try:
        eccentricities(settings)
        if settings["contrast_method"] == "constant_stimuli":
            make_fixed_schedule(settings, 0)
        elif settings["starting_strength"] > .5 or settings["trial_count"] > settings["max_trials"]:
            raise ValueError("Adaptive strength must be <=0.5 and trial_count <= max_trials.")
    except ValueError as exc:
        yield str(exc)


# 6. RUN AND FINISH — installed policies own bookkeeping and update equations.
def fixed_method(run):
    schedule = make_fixed_schedule(run.values, run.seed)
    return ConstantContrastMethod(run, schedule=schedule, condition_field="value",
        record=fixed_teaching_record, resolution={
            "trial_selection_method": "constant_stimuli", "controlled_quantity": "digital_line_increment",
            "digital_intensity_mapping": "I_line = 0.5 + increment; background = 0.5",
            "fixed_repetitions_per_level_per_condition": run.values["fixed_repetitions"],
            "planned_trials": len(schedule), "random_seed": run.seed, "schedule": schedule,
            "response_analysis": "Accuracy per eccentricity and level; no threshold fit.",
        })


def procedure(run):
    return run_contrast_experiment(run, methods={
        "adaptive": lambda: TeachingAdaptiveMethod(run, make_conditions=make_conditions,
                                                   choose=choose_condition, maximum=.5),
        "constant_stimuli": lambda: fixed_method(run),
    }, prepare_stimuli=prepare_stimuli, make_trial=make_trial, interpret_response=interpret_response)


# 7. FRAMEWORK CONNECTION
SPEC = experiment(
    id="demolab__line_strength", name="Line strength at two eccentricities",
    description=__doc__, procedure=procedure, fields=FIELDS, responses=RESPONSES,
    adaptive=AdaptiveSelection("consecutive_up_down", controls=("n_down", "n_up", "down_factor", "up_factor", "max_trials")),
    method_planner=make_fixed_schedule, validator=validate_settings,
    method_reviewer=lambda run: review_teaching_adaptive(run, make_conditions, choose_condition),
    calibration_requirements=("geometry",), monitor_capabilities=("display_binding", "resolution"),
    stimulus_slots={"target": "line"}, stimulus_defaults={"target": LinePatch.SPEC.id},
    supports_simulation=True, source_paths=("experiments/demolab__line_strength.py",),
)
