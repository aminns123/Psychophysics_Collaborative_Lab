"""Report whether the line is above (UP) or below (DOWN) fixation; no grating.

This file owns settings, geometry, conditions, ordering, timing, responses,
adaptive choices and recorded measurements. Read make_conditions(), prepare_stimuli(), make_trial(), procedure()
and SPEC below. Correctness is equality of the target/response alternative index.
The TUI may override declared defaults and response keys; it cannot change meanings.

Development reconstruction from 1c317759, not qualified human acquisition.
No beeps are requested. Source audio/RNG/delayed termination parity is unproven.
Literal pixel geometry is converted with the run profile, including the historical
ellipse degree-number subtracted from pixel-y quirk. Do not silently repair it.

Shared services: Scene primitives implement rendering once; RunContext executes,
collects and saves; adaptive/legacy_flanker.py implements the fixture-backed log
algorithm once. Its parameters and immediate retirement policy are explicit here.
Matched experiments intentionally repeat scientific policy, not display/input/IO
mechanisms, so each can be read and changed independently. Tests protect pairing.
"""

import json
import math
import random
from ..researcher import (
    ConfigField,
    experiment,
    ResponseParadigm,
    AdaptiveSelection,
    TrialTimeline,
    Show,
    CollectResponse,
    RecordState,
    UpdateAdaptive,
    UpdateState,
)
from ..stimulus_library import Scene, gaussian_dot, line, grating, annulus

# 1. SETTINGS AND STIMULI
# Defaults below populate the TUI; run.values contains the selections for this run.
SOURCE_COMMIT = "1c3177594e00f0b26fa361238db0f4db5de403fa"
BLOCK_REASON = "Development reconstruction only: legacy ellipse source is incomplete; shader/alpha, audio, RNG and delayed termination parity remain unproven. See docs/LEGACY_STIMULUS_MIGRATION.md. Retained CSF is unchanged."
FIELDS = (
    ConfigField(
        "condition_positions_deg",
        "Probe x positions (JSON degrees)",
        "text",
        "[0.25, 0.3333333333333333, 0.4166666666666667, 0.5]",
    ),
    ConfigField(
        "trials_per_condition",
        "Trial ceiling multiplier",
        "int",
        10,
        minimum=1,
        maximum=1000,
    ),
    ConfigField("background", "Digital background", "float", 0.24, minimum=0.01, maximum=0.4),
    ConfigField(
        "start_contrast",
        "Starting digital contrast",
        "float",
        1.0,
        minimum=1e-06,
        maximum=1,
    ),
    ConfigField("scene_size_deg", "Scene aperture", "float", 18.0, minimum=1, maximum=60),
    ConfigField(
        "reference_width_px",
        "Synthetic reference width if profile has none",
        "int",
        0,
        minimum=0,
        maximum=16384,
    ),
    ConfigField(
        "reference_height_px",
        "Synthetic reference height if profile has none",
        "int",
        0,
        minimum=0,
        maximum=16384,
    ),
)


FIELDS += (
    ConfigField(
        "flanker_x_deg",
        "Flanker x (literal source is left)",
        "float",
        -3.0,
        minimum=-10,
        maximum=10,
    ),
    ConfigField(
        "legacy_frequency_label",
        "Legacy nominal SF label (not calibrated cpd)",
        "float",
        1.0,
        minimum=0.01,
        maximum=20,
    ),
)


FIELDS += (
    ConfigField(
        "n_down",
        "Correct-answer count for a down step (legacy counter)",
        "int",
        3,
        minimum=1,
        section="Adaptive settings",
    ),
    ConfigField(
        "trial_point",
        "Initial-phase response boundary",
        "int",
        9,
        minimum=1,
        section="Adaptive settings",
    ),
    ConfigField(
        "reverse_point",
        "Initial-phase reversal boundary",
        "int",
        1,
        minimum=1,
        section="Adaptive settings",
    ),
    ConfigField(
        "log_up",
        "Incorrect-answer increase (log10 units)",
        "float",
        0.19,
        minimum=0,
        section="Adaptive settings",
    ),
    ConfigField(
        "log_down",
        "Correct-answer decrease (log10 units)",
        "float",
        0.7393 * 0.19,
        minimum=0,
        section="Adaptive settings",
    ),
    ConfigField(
        "initial_log_down",
        "Initial-phase decrease (log10 units)",
        "float",
        0.2,
        minimum=0,
        section="Adaptive settings",
    ),
    ConfigField(
        "reversal_limit",
        "Reversals required per condition",
        "int",
        10,
        minimum=1,
        section="Adaptive settings",
    ),
    ConfigField(
        "condition_trial_limit",
        "Response limit per condition",
        "int",
        101,
        minimum=1,
        section="Adaptive settings",
    ),
)


SLOTS = ("fixation", "stimulus")
RESPONSES = ResponseParadigm("base_flanker", ("up", "down"), ("UP", "DOWN"))
STIMULUS_SLOTS = {s: "scene" for s in SLOTS}
STIMULUS_DEFAULTS = {s: "composed_scene" for s in SLOTS}

PARADIGM = "two_alternative_forced_choice"


# 2. CONDITIONS AND TRIAL ORDER
def make_conditions(settings):
    try:
        result = json.loads(settings["condition_positions_deg"])
    except (ValueError, TypeError) as exc:
        raise ValueError("Supply an explicit JSON list of probe x positions in degrees") from exc
    if (
        not isinstance(result, list)
        or not result
        or len(result) > 100
        or any(
            (
                type(x) not in (int, float) or not math.isfinite(x) or (not 0 < x <= 10)
                for x in result
            )
        )
        or (len(set(result)) != len(result))
    ):
        raise ValueError("Condition positions must be distinct positive degrees (up to 10)")
    return [
        {"id": i, "position_deg": position, "value": position}
        for i, position in enumerate(result, 1)
    ]


def source_targets(count, rng):
    """Translate randomIndex_ADMs + random.choice([-1,1,nNew]) sign schedule."""
    positive = negative = 0
    targets = []
    for _ in range(count):
        r = rng.uniform(0, 1)
        if positive < 3 and negative < 3:
            sign = 1 if r > 0.5 else -1
            positive, negative = (positive + 1, 0) if sign == 1 else (0, negative + 1)
        elif positive == 3:
            sign, positive = (-1, 0)
        else:
            sign, negative = (1, 0)
        targets.append(0 if rng.choice([-1, 1, sign]) > 0 else 1)
    return targets


def choose_condition(run, conditions, state):
    adaptive = state["adaptive"]
    identity = adaptive.select(state["rng"].choice)
    condition = dict(conditions[identity - 1])
    condition.update(
        target=state["targets"][run.accepted_trials],
        intensity=adaptive.states[identity].next_intensity,
        previous_reversals=adaptive.states[identity].reversal_count,
        first_trial=run.accepted_trials == 0,
    )
    if not 0 <= condition["intensity"] <= 1:
        raise ValueError(
            "Legacy adaptive step exceeds digital range; preserved accepted data, no silent clamp"
        )
    return condition


# 3. PREPARE STIMULI
def pixel_geometry(run):
    """Resolve literal source pixel quantities using this run's monitor profile.

    Synthetic dimensions must be supplied when a reference profile has none;
    do not silently assert a historical framebuffer resolution.
    """
    resolution = run.display.expected_resolution_px
    if resolution is None:
        resolution = (
            run.values["reference_width_px"],
            run.values["reference_height_px"],
        )
    if min(resolution) < 1:
        raise ValueError(
            "Supply reference_width_px/reference_height_px for this synthetic run; historical resolution is unknown"
        )
    pitch_x = run.display.physical_width_m / resolution[0]
    pitch_y = run.display.physical_height_m / resolution[1]
    distance = run.display.viewing_distance_m

    def angle(px, pitch):
        return math.degrees(math.atan(px * pitch / distance))

    return {
        "resolution_px": list(resolution),
        "fixation_y_deg": angle(200, pitch_y),
        "probe_width_deg": 2 * angle(0.5, pitch_x),
        "probe_length_deg": 2 * angle(1.5, pitch_y),
        "ellipse_rx_deg": angle(250, pitch_x),
        "ellipse_ry_deg": angle(250, pitch_y),
        "fixation_sigma_deg": angle(31.5 * 0.035, pitch_x),
        "ellipse_probe_y_offset_deg": angle(
            -math.degrees(2 * math.atan(1.5 * pitch_x / distance)) / 2, pitch_y
        ),
    }


def prepare_stimuli(run, condition, state):
    values, geometry = run.values, state["geometry"]
    position, target, intensity = (
        condition["position_deg"],
        condition["target"],
        condition["intensity"],
    )
    bg, fy = (values["background"], geometry["fixation_y_deg"])
    dot = gaussian_dot(
        sigma_deg=geometry["fixation_sigma_deg"],
        intensity=(bg + 0.09) * 254 / 255,
        y_deg=fy,
    )
    fixation = Scene(dot, background=bg)
    probe = line(
        length_deg=geometry["probe_length_deg"],
        width_deg=geometry["probe_width_deg"],
        intensity=intensity,
        x_deg=position,
        y_deg=fy + (0.6 if target == 0 else -0.6),
    )
    surround = ()
    drawings = {
        "fixation": fixation,
        "stimulus": Scene(*surround, probe, dot, background=bg),
    }
    return {slot: scene.parameters(values["scene_size_deg"]) for slot, scene in drawings.items()}


# 4. ONE TRIAL
def make_trial(settings, condition):
    """Durations are milliseconds; the first trial adds 250 ms fixation. No audio."""
    phases = (
        [Show("leading_fixation", slot="fixation", duration=250)]
        if condition["first_trial"]
        else []
    )
    phases += [
        Show("fixation", slot="fixation", duration=250),
        Show("pre_interval", slot="fixation", duration=250),
    ]
    phases += [Show("stimulus", slot="stimulus", duration=250)]
    phases += [
        Show("delay", slot="fixation", duration=500),
        CollectResponse(actions=("up", "down"), slot="fixation"),
        RecordState("accepted_response"),
    ]
    return TrialTimeline(tuple(phases))


# 5. RESPONSES AND ADAPTATION
def interpret_response(condition, response):
    """Both categories score the chosen spatial/property alternative or interval."""
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with the recorded target.")
    return dict(response) | {"correct": correct}


# The fixture-tested legacy engine owns counters/history, not experiment policy.
# Errors reset correct ticks and increase by log_up. During the initial phase,
# each correct answer decreases by initial_log_down; that phase requires BOTH
# current presentation count < trial_point AND history reversals < reverse_point.
# Thereafter n_down correct answers trigger log_down, holding between steps.
# Its history-based reversal count is evaluated before this response's update,
# retaining the historical short-history convention (different from the CSF).
# Numeric rule: I_next = background + (I - background) * 10**delta, rounded to
# eight decimals. preview() supplies the two pure candidates below. No clipping.
# All parameters come from run.values. Sharing the tested engine avoids copying
# its historical counter quirks; geometry, choices, limits and measurements stay here.
def next_intensity(state, response, step):
    return state["candidate_correct"] if response["correct"] else state["candidate_incorrect"]


def update_experiment(run, condition, state, response, trial):
    adaptive, v = state["adaptive"], run.values
    intensity = condition["intensity"]
    identity = condition["id"]
    old_reversals = condition["previous_reversals"]

    def record_adaptation(state, response):
        after = adaptive.states[identity]
        return dict(state) | {
            "next_contrast": (after.next_intensity - v["background"]) / (1 - v["background"]),
            "step": (
                "down"
                if after.next_intensity < intensity
                else "up" if after.next_intensity > intensity else "hold"
            ),
            "reversal_count": after.reversal_count,
            "reversal": int(after.reversal_count > old_reversals),
            "staircase_complete": int(after.complete),
        }

    trial.apply(
        UpdateAdaptive(adaptive, identity, next_intensity, state_key="next_intensity"),
        RecordState("after_adaptation"),
        UpdateState(record_adaptation, name="canonical_adaptive_state"),
    )
    return state


def trial_record(run, condition, state):
    v, adaptive = run.values, state["adaptive"]
    identity, intensity, position = (
        condition["id"],
        condition["intensity"],
        condition["position_deg"],
    )
    trial_state = {
        "staircase_id": identity,
        "presented_intensity": intensity,
        "presented_contrast": (intensity - v["background"]) / (1 - v["background"]),
        "staircase_trial_index": len(adaptive.states[identity].presented) + 1,
        "candidate_correct": adaptive.preview(identity, True)[1],
        "candidate_incorrect": adaptive.preview(identity, False)[1],
        **dict.fromkeys(
            (
                "next_intensity",
                "next_contrast",
                "step",
                "reversal",
                "reversal_count",
                "staircase_complete",
            )
        ),
    }
    return {
        "state": trial_state,
        "adaptive_record": adaptive,
        "record_from_state": {
            "staircase_id": "staircase_id",
            "staircase_trial_index": "staircase_trial_index",
            "presented_screen_intensity": "presented_intensity",
            "presented_display_contrast": "presented_contrast",
            "next_screen_intensity": "next_intensity",
            "next_display_contrast": "next_contrast",
            "step": "step",
            "reversal": "reversal",
            "reversal_count": "reversal_count",
            "staircase_complete": "staircase_complete",
        },
        "measurements": {
            "probe_x_deg": position,
            "presented_screen_intensity": intensity,
            "presented_display_contrast": (intensity - v["background"]) / (1 - v["background"]),
            "staircase_id": identity,
        },
    }


# 6. RUN AND FINISH
def initialise_experiment(run, conditions):
    if not run.synthetic:
        raise ValueError(BLOCK_REASON)
    v = run.values
    geometry = pixel_geometry(run)
    ceiling = v["trials_per_condition"] * len(conditions)
    rng = random.Random(run.seed)
    targets = source_targets(ceiling, rng)
    adaptive = run.adaptive(
        range(1, len(conditions) + 1),
        background=v["background"],
        start_contrast=v["start_contrast"],
        max_trials=ceiling,
        n_down=v["n_down"],
        trial_point=v["trial_point"],
        reverse_point=v["reverse_point"],
        log_up=v["log_up"],
        log_down=v["log_down"],
        initial_log_down=v["initial_log_down"],
        reversal_limit=v["reversal_limit"],
        condition_trial_limit=v["condition_trial_limit"],
    )
    run.initialise(
        expected_trials=ceiling,
        resolution={
            "source_commit": SOURCE_COMMIT,
            "family": "base",
            "migration_status": BLOCK_REASON,
            "geometry": geometry,
            "condition_positions_deg": [c["position_deg"] for c in conditions],
            "targets": targets,
            "response_ceiling": ceiling,
            "adaptive_policy": {
                "n_down": v["n_down"],
                "trial_point": v["trial_point"],
                "reverse_point": v["reverse_point"],
                "log_up": v["log_up"],
                "log_down": v["log_down"],
                "initial_log_down": v["initial_log_down"],
                "reversal_limit": v["reversal_limit"],
                "condition_trial_limit": v["condition_trial_limit"],
                "retirement": "immediate after accepted update; historical delay unproven",
            },
            "source_condition_status": "source position array",
            "decision_scene": v.get("decision_scene"),
            "contrast_units": "(digital_intensity-background)/(1-background); legacy name Weber is not optical Weber contrast",
            "rng_parity": False,
            "audio_reproduced": False,
            "pixel_parity": False,
        },
    )
    return {"adaptive": adaptive, "rng": rng, "targets": targets, "geometry": geometry}


def is_finished(run, conditions, state):
    return state["adaptive"].status != "running"


def finish_experiment(run, conditions, state):
    run.complete_adaptive(state["adaptive"])


def procedure(run):
    if not getattr(run, "synthetic", False) and SPEC.acquisition_block_reason:
        raise ValueError(SPEC.acquisition_block_reason)
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
def validate(values):
    if values["condition_positions_deg"].strip() == "[]":
        return
    try:
        make_conditions(values)
    except ValueError as exc:
        yield str(exc)


def definition():
    return experiment(
        id="base_flanker",
        name="DEVELOPMENT: " + "base_flanker".replace("_", " ").title(),
        description="Source-based virtual reconstruction; human acquisition blocked pending parity review.",
        procedure=procedure,
        fields=FIELDS,
        validator=validate,
        responses=RESPONSES,
        adaptive=AdaptiveSelection(
            "legacy_flanker_log",
            controls=(
                "n_down",
                "trial_point",
                "reverse_point",
                "log_up",
                "log_down",
                "initial_log_down",
                "reversal_limit",
                "condition_trial_limit",
            ),
        ),
        supports_simulation=True,
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        acquisition_block_reason=BLOCK_REASON,
        default_config="configs/experiments/base_flanker.json",
        source_paths=(
            "src/psychophysics_lab/experiments/base_flanker.py",
            "src/psychophysics_lab/stimulus_library.py",
            "src/psychophysics_lab/adaptive/legacy_flanker.py",
        ),
    )


SPEC = definition()
