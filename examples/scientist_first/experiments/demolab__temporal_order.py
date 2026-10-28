"""Did the peripheral line appear BEFORE or AFTER the central visual cue?

Fixed temporal-order teaching prototype. This is a new declared protocol, not
an established temporal threshold test or an official experiment replacement.
Only software-scheduled onset asynchrony is claimed; no photon/audio timing.
"""
import math
import random
from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, Show, Stimulus, WaitForKey, CollectResponse,
    Beep, UpdateState, TrialTimeline, experiment, legacy_trial_factory,
)

# PART A1 — EXPERIMENTAL CHOICES
# Everyday edits; a changed value/order changes this declared scientific protocol.
# Factor: signed target-onset minus cue-onset, ms. Negative = before cue.
# Conditions must be distinct +/- pairs. Every condition repeats equally;
# shuffle the complete schedule once using this run's recorded seed.
EXPERIMENT_ID = "demolab__temporal_order"
TARGET_STIMULUS = "oriented_line"
FIXATION_STIMULUS = "fixation_cross"
CALIBRATION_REQUIREMENTS = ("geometry", "timing")
MONITOR_CAPABILITIES = ("display_binding", "resolution")
ACQUISITION_BLOCK_REASON = "New teaching protocol; independent scientific and physical qualification outstanding."
STIMULUS_SLOTS = {"fixation": "fixation", "cue": "fixation", "target": "line"}
STIMULUS_DEFAULTS = {"fixation": FIXATION_STIMULUS, "cue": FIXATION_STIMULUS, "target": TARGET_STIMULUS}
FIELDS = (
    ConfigField("soa_ms", "Target onset minus visual cue onset", "text", "-200,-100,100,200", units="ms"),
    ConfigField("repetitions", "Presentations per signed SOA", "int", 2, minimum=1, maximum=100, units="presentations"),
    ConfigField("fixation_ms", "Pre-trial fixation", "int", 500, minimum=1, units="ms"),
    ConfigField("target_ms", "Peripheral line duration", "int", 30, minimum=1, units="ms"),
    ConfigField("cue_ms", "Central visual cue duration", "int", 30, minimum=1, units="ms"),
    ConfigField("target_x_deg", "Line horizontal position", "float", 2., minimum=-10., maximum=10., units="degrees"),
    ConfigField("auditory_cues", "Optional tone at visual cue onset", "choice", False, choices=(True, False)),
    ConfigField("response_audio", "Optional accepted-answer tone", "choice", False, choices=(True, False)),
    ConfigField("max_trials", "Accepted-response safety ceiling", "int", 1000, minimum=1, maximum=10000, units="responses"),
)
RESPONSES = ResponseParadigm("temporal_order", ("before", "after"), ("F", "J"))
FIXATION_ARM_DEG = .2
CUE_ARM_DEG = .7  # A visible enlargement, distinguishable from ordinary fixation.
# Alternatives describe temporal order, not two spatial targets. The peripheral
# line has constant appearance/strength/position across both alternatives.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="fixation", instructions="Press SPACE when ready"),
    Show("settle", slot="fixation", duration=1000),
]  # Set [] to disable this once-only opening.



def trial_events(settings, condition):
    fixation = Show("fixation", slot="fixation", duration="fixation_ms")
    target = Show("target", duration="target_ms",
                  stimuli=(Stimulus("target", x_deg=settings["target_x_deg"], y_deg=0),))
    cue = Show("cue", slot="cue", duration="cue_ms",
               beep=Beep(550, 35) if settings["auditory_cues"] else None)
    # Non-overlapping displays; the first display's duration is PART of SOA.
    first, second = (target, cue) if condition["target"] == 0 else (cue, target)
    first_ms = settings["target_ms"] if condition["target"] == 0 else settings["cue_ms"]
    return [fixation, first,
            Show("gap", slot="fixation", duration=abs(condition["soa_ms"]) - first_ms),
            second, CollectResponse(actions=("before", "after"), slot="fixation",
                                    beep=Beep(750, 35) if settings["response_audio"] else None)]


MEASUREMENT_UNITS = {
    "scheduled_target_minus_cue_ms": "ms, software schedule",
    "target_x_deg": "degrees", "target_y_deg": "degrees", "target_duration_ms": "ms",
    "visual_cue_duration_ms": "ms", "repeat": "count, 1-based", "target_order": "category",
    "cue_audio_requested": "boolean, not measured acoustic onset",
    "fixation_arm_deg": "degrees", "visual_cue_arm_deg": "degrees",
}


def trial_measurements(settings, condition):
    return {"scheduled_target_minus_cue_ms": condition["soa_ms"],
            "target_x_deg": settings["target_x_deg"], "target_y_deg": 0,
            "target_duration_ms": settings["target_ms"], "visual_cue_duration_ms": settings["cue_ms"],
            "repeat": condition["repeat"], "target_order": RESPONSES.alternatives[condition["target"]],
            "cue_audio_requested": settings["auditory_cues"],
            "fixation_arm_deg": FIXATION_ARM_DEG, "visual_cue_arm_deg": CUE_ARM_DEG}


# PART A2 — SCIENTIFIC METHODS
# Condition validation, seeded selection, scoring, updates, stopping and estimators.
def signed_soas(settings):
    return [float(value.strip()) for value in settings["soa_ms"].split(",")]


def validate_settings(settings):
    try:
        soas = signed_soas(settings)
    except ValueError:
        yield "SOAs must be comma-separated numbers in milliseconds."
        return
    if (not soas or any(not math.isfinite(s) or not s.is_integer() or abs(s) > 5000 for s in soas)
            or len(set(soas)) != len(soas)):
        yield "Use distinct finite whole-millisecond SOAs within +/-5000 ms."
        return
    if set(soas) != {-s for s in soas} or 0 in soas:
        yield "Use nonzero +/- SOA pairs to balance before/after alternatives."
    if any(abs(s) <= max(settings["target_ms"], settings["cue_ms"]) for s in soas):
        yield "Absolute SOA must exceed both display durations, leaving a positive gap."
    if len(soas) * settings["repetitions"] > settings["max_trials"]:
        yield "The complete fixed schedule exceeds max_trials; reduce it deliberately."


def make_conditions(settings, seed=0):
    errors = list(validate_settings(settings))
    if errors:
        raise ValueError(" ".join(errors))
    schedule = [{"soa_ms": int(soa), "target": 0 if soa < 0 else 1, "repeat": repeat,
                 "value": int(soa)}
                for soa in signed_soas(settings)
                for repeat in range(1, settings["repetitions"] + 1)]
    random.Random(f"{seed}:temporal-order").shuffle(schedule)
    return schedule


def prepare_stimuli(run, condition=None, state=None):
    return {"fixation": run.stimulus_parameters("fixation", arm_length_deg=FIXATION_ARM_DEG),
            "cue": run.stimulus_parameters("cue", arm_length_deg=CUE_ARM_DEG)}


def interpret_response(condition, response):
    correct = response["alternative"] == (0 if condition["soa_ms"] < 0 else 1)
    if correct != response["correct"]:
        raise ValueError("Temporal scoring and recorded target disagree.")
    return dict(response) | {"correct": correct}


def update_counts(state, response):
    # Per-SOA scientific updates, after one accepted scientific response.
    counts = {key: dict(value) for key, value in state["counts"].items()}
    cell = counts.setdefault(str(state["soa_ms"]), {"accepted": 0, "correct": 0, "after": 0})
    cell["accepted"] += 1
    cell["correct"] += int(response["correct"])
    cell["after"] += int(response["alternative"] == 1)
    return dict(state) | {"counts": counts}


def results(counts):
    # No adaptive strength, reversal stopping, fitted PSE or JND is claimed.
    # Stop after all scheduled accepted answers; no timeout exclusions/imputation.
    return [{"soa_ms": int(soa), **cell,
             "proportion_correct": cell["correct"] / cell["accepted"],
             "proportion_after": cell["after"] / cell["accepted"]}
            for soa, cell in sorted(counts.items(), key=lambda row: int(row[0]))]


def choose_condition(run, conditions, state):
    return conditions[run.accepted_trials]


def is_finished(run, conditions, state):
    """Accepted-response stopping; interrupted/timeout trials are not invented."""
    return run.accepted_trials >= len(conditions)


# PART B — FRAMEWORK INTEGRATION
def initialise_experiment(run, conditions):
    resolution = {"schedule": conditions, "measurement_units": MEASUREMENT_UNITS,
                  "trial_selection_method": "fixed_signed_soa", "random_seed": run.seed,
                  "estimators": "Accuracy and fraction after per SOA; no fitted threshold"}
    run.initialise(expected_trials=len(conditions), resolution=resolution)
    return {"counts": {}}, resolution


def _record(settings, condition):
    values = trial_measurements(settings, condition)
    if set(values) != set(MEASUREMENT_UNITS) or any(
        not isinstance(v, (str, int, float, bool)) or
        (isinstance(v, (int, float)) and not math.isfinite(v)) for v in values.values()
    ):
        raise ValueError("trial_measurements must supply every declared finite scalar measurement.")
    return values


def procedure(run):
    conditions = make_conditions(run.values, run.seed)
    (state, resolution) = initialise_experiment(run, conditions)
    while not is_finished(run, conditions, state):
        condition = choose_condition(run, conditions, state)
        with run.trial(trial_events(run.values, condition), target=condition["target"],
                       condition=condition["soa_ms"], state=state | {"soa_ms": condition["soa_ms"]},
                       parameters_by_slot=prepare_stimuli(run),
                       measurements=_record(run.values, condition),
                       instructions="   ".join(f"{a}: {k}" for a, k in zip(run.responses.alternatives, run.responses.keys))) as trial:
            interpret_response(condition, trial.response)
            trial.apply(UpdateState(update_counts))
            state = dict(trial.state)
    run.save_resolution(**(resolution | {"observed_temporal_accuracy": results(state["counts"])}))
    run.complete()


make_trial = legacy_trial_factory(trial_events)
SPEC = experiment(
    id=EXPERIMENT_ID, name="Scientist-first temporal before/after cue investigation",
    description=__doc__,
    procedure=procedure, fields=FIELDS, responses=RESPONSES, session_start=SESSION_START,
    validator=validate_settings, method_planner=make_conditions,
    stimulus_slots=STIMULUS_SLOTS,
    stimulus_defaults=STIMULUS_DEFAULTS,
    scientific_spec={"version": "temporal-order-investigation-1",
        "quantity": "Signed target-minus-visual-cue scheduled onset, ms",
        "response": "Before/after visual cue; target index follows SOA sign",
        "conditions": "Equal repetitions of distinct signed +/- SOA pairs; seeded shuffle",
        "adaptive": "None; fixed schedule only", "stopping": "All scheduled accepted responses",
        "estimator": "Accuracy and fraction after per SOA; no fitted PSE/JND",
        "exclusions": "No retrospective exclusion; abort/timeout retained by existing runner",
        "measurements": MEASUREMENT_UNITS},
    calibration_requirements=CALIBRATION_REQUIREMENTS, monitor_capabilities=MONITOR_CAPABILITIES,
    supports_simulation=True,
    acquisition_block_reason=ACQUISITION_BLOCK_REASON,
    source_paths=(f"experiments/{EXPERIMENT_ID}.py",),
)
