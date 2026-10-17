"""Report which interval contains the line: first (1) or second (2).

This file owns settings, geometry, conditions, ordering, timing, responses,
adaptive choices and recorded measurements. Read scenes(), timeline(), procedure()
and SPEC below. Correctness is equality of the target/response alternative index.
The TUI may override declared defaults and response keys; it cannot change meanings.

Development reconstruction from 1c317759, not qualified human acquisition.
No beeps are requested. Source audio/RNG/delayed termination parity is unproven.
The ellipse decision display and condition positions must be explicitly supplied.
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

SOURCE_COMMIT = "1c3177594e00f0b26fa361238db0f4db5de403fa"
BLOCK_REASON = "Development reconstruction only: legacy ellipse source is incomplete; shader/alpha, audio, RNG and delayed termination parity remain unproven. See docs/LEGACY_STIMULUS_MIGRATION.md. Retained CSF is unchanged."


def positions(values):
    try:
        result = json.loads(values["condition_positions_deg"])
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Supply an explicit JSON list of probe x positions in degrees"
        ) from exc
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
        raise ValueError(
            "Condition positions must be distinct positive degrees (up to 10)"
        )
    return result


def validate(values):
    if values["condition_positions_deg"].strip() == "[]":
        return
    try:
        positions(values)
    except ValueError as exc:
        yield str(exc)


# Source: fixation 200 px above centre; 1 x 3 px probe; 250 px ellipse radii.
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


def scenes(values, geometry, *, position, target, intensity):
    bg, fy = (values["background"], geometry["fixation_y_deg"])
    dot = gaussian_dot(
        sigma_deg=geometry["fixation_sigma_deg"],
        intensity=(bg + 0.09) * 254 / 255,
        y_deg=fy,
    )
    fixation = Scene(dot, background=bg)
    surround = annulus(
        radius_x_deg=geometry["ellipse_rx_deg"],
        radius_y_deg=geometry["ellipse_ry_deg"],
        inner_ratio=math.sqrt(1 - 0.02),
        intensity=bg + 0.6,
        y_deg=fy,
    )
    probe = line(
        length_deg=geometry["probe_length_deg"],
        width_deg=geometry["probe_width_deg"],
        intensity=intensity,
        x_deg=position,
        y_deg=fy + geometry["ellipse_probe_y_offset_deg"],
    )
    mask = Scene(surround, dot, background=bg)
    present = Scene(surround, probe, dot, background=bg)
    return {
        "fixation": fixation,
        "first": present if target == 0 else mask,
        "second": mask if target == 0 else present,
        "decision": fixation,
    }
    probe = line(
        length_deg=geometry["probe_length_deg"],
        width_deg=geometry["probe_width_deg"],
        intensity=intensity,
        x_deg=position,
        y_deg=fy + (0.6 if target == 0 else -0.6),
    )
    surround = (
        grating(
            size_deg=5.0,
            spatial_frequency_cpd=31.5
            * values["legacy_frequency_label"]
            / (2 * math.pi * 5),
            amplitude=0.018 / 2,
            mean=bg,
            x_deg=values["flanker_x_deg"],
            y_deg=fy,
        ),
    )
    return {
        "fixation": fixation,
        "stimulus": Scene(*surround, probe, dot, background=bg),
    }


# Durations below are ms; first trial has an extra 250 ms fixation.
def timeline(*, first_trial=False, adaptive=None, identity=None):
    phases = (
        [Show("leading_fixation", slot="fixation", duration=250)] if first_trial else []
    )
    phases += [
        Show("fixation", slot="fixation", duration=250),
        Show("pre_interval", slot="fixation", duration=250),
    ]
    phases += [
        Show("decision", slot="decision", duration=250),
        Show("interval_one", slot="first", duration=250),
        Show("inter_interval", slot="fixation", duration=250),
        Show("interval_two", slot="second", duration=250),
    ]
    phases += [
        Show("delay", slot="fixation", duration=500),
        CollectResponse(actions=("first", "second"), slot="fixation"),
        RecordState("accepted_response"),
    ]
    if adaptive is not None:
        phases += [
            UpdateAdaptive(
                adaptive, identity, next_intensity, state_key="next_intensity"
            ),
            RecordState("after_adaptation"),
        ]
    return TrialTimeline(tuple(phases))


def next_intensity(state, response, step):
    return (
        state["candidate_correct"]
        if response["correct"]
        else state["candidate_incorrect"]
    )


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


# Independent seeded target stream, uniformly selected active conditions,
# shared response ceiling; retire each condition at 10 reversals or 101 responses.
def procedure(run):
    if not run.synthetic:
        raise ValueError(BLOCK_REASON)
    v = run.values
    conditions = positions(v)
    if v["decision_scene"] != "fixation_only_development":
        raise ValueError(
            "Legacy expALL_decsison is undefined: explicitly select fixation_only_development for a virtual reconstruction"
        )
    geometry = pixel_geometry(run)
    ceiling = v["trials_per_condition"] * len(conditions)
    rng = random.Random(run.seed)
    targets = source_targets(ceiling, rng)
    targets = [rng.randrange(2) for _ in range(ceiling)]
    adaptive = run.adaptive(
        range(1, len(conditions) + 1),
        background=v["background"],
        start_contrast=v["start_contrast"],
        max_trials=ceiling,
        n_down=3,
        trial_point=9,
        reverse_point=1,
        log_up=0.19,
        log_down=0.7393 * 0.19,
        initial_log_down=0.2,
        reversal_limit=10,
        condition_trial_limit=101,
    )
    run.initialise(
        expected_trials=ceiling,
        resolution={
            "source_commit": SOURCE_COMMIT,
            "family": "ellipse",
            "migration_status": BLOCK_REASON,
            "geometry": geometry,
            "condition_positions_deg": conditions,
            "targets": targets,
            "response_ceiling": ceiling,
            "adaptive_policy": {
                "n_down": 3,
                "trial_point": 9,
                "reverse_point": 1,
                "log_up": 0.19,
                "log_down": 0.7393 * 0.19,
                "initial_log_down": 0.2,
                "reversal_limit": 10,
                "condition_trial_limit": 101,
                "retirement": "immediate after accepted update; historical delay unproven",
            },
            "source_condition_status": "explicit researcher supplied",
            "decision_scene": v.get("decision_scene"),
            "contrast_units": "(digital_intensity-background)/(1-background); legacy name Weber is not optical Weber contrast",
            "rng_parity": False,
            "audio_reproduced": False,
            "pixel_parity": False,
        },
    )
    while adaptive.status == "running":
        identity = adaptive.select(rng.choice)
        position = conditions[identity - 1]
        target = targets[run.accepted_trials]
        intensity = adaptive.states[identity].next_intensity
        if not 0 <= intensity <= 1:
            raise ValueError(
                "Legacy adaptive step exceeds digital range; preserved accepted data, no silent clamp"
            )
        drawings = scenes(
            v, geometry, position=position, target=target, intensity=intensity
        )
        parameters = {
            slot: scene.parameters(v["scene_size_deg"])
            for slot, scene in drawings.items()
        }
        plan = timeline(
            first_trial=run.accepted_trials == 0, adaptive=adaptive, identity=identity
        )
        old_reversals = adaptive.states[identity].reversal_count

        def record_adaptation(state, response):
            after = adaptive.states[identity]
            return dict(state) | {
                "next_contrast": (after.next_intensity - v["background"])
                / (1 - v["background"]),
                "step": (
                    "down"
                    if after.next_intensity < intensity
                    else "up" if after.next_intensity > intensity else "hold"
                ),
                "reversal_count": after.reversal_count,
                "reversal": int(after.reversal_count > old_reversals),
                "staircase_complete": int(after.complete),
            }

        plan = TrialTimeline(
            plan.phases
            + (UpdateState(record_adaptation, name="canonical_adaptive_state"),)
        )
        state = {
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
        run.play_trial(
            plan,
            target=target,
            condition=position,
            parameters_by_slot=parameters,
            adaptive_record=adaptive,
            state=state,
            record_from_state={
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
            measurements={
                "probe_x_deg": position,
                "presented_screen_intensity": intensity,
                "presented_display_contrast": (intensity - v["background"])
                / (1 - v["background"]),
                "staircase_id": identity,
            },
        )
        run.save_adaptive(adaptive)
    run.complete_adaptive(adaptive)


def definition():
    fields = (
        ConfigField(
            "condition_positions_deg", "Probe x positions (JSON degrees)", "text", "[]"
        ),
        ConfigField(
            "trials_per_condition",
            "Trial ceiling multiplier",
            "int",
            10,
            minimum=1,
            maximum=1000,
        ),
        ConfigField(
            "background", "Digital background", "float", 0.24, minimum=0.01, maximum=0.4
        ),
        ConfigField(
            "start_contrast",
            "Starting digital contrast",
            "float",
            1.0,
            minimum=1e-06,
            maximum=1,
        ),
        ConfigField(
            "scene_size_deg", "Scene aperture", "float", 18.0, minimum=1, maximum=60
        ),
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
    fields += (
        ConfigField(
            "decision_scene",
            "Undefined legacy decision display",
            "choice",
            "unresolved",
            choices=("unresolved", "fixation_only_development"),
        ),
    )
    slots = ("fixation", "first", "second", "decision")
    return experiment(
        id="ellipse_2d",
        name="DEVELOPMENT: " + "ellipse_2d".replace("_", " ").title(),
        description="Source-based virtual reconstruction; human acquisition blocked pending parity review.",
        procedure=procedure,
        fields=fields,
        validator=validate,
        responses=ResponseParadigm("ellipse_2d", ("first", "second"), ("1", "2")),
        adaptive=AdaptiveSelection("legacy_flanker_log"),
        supports_simulation=True,
        stimulus_slots={s: "scene" for s in slots},
        stimulus_defaults={s: "composed_scene" for s in slots},
        calibration_requirements=("geometry", "luminance", "timing"),
        monitor_capabilities=("display_binding", "resolution"),
        acquisition_block_reason=BLOCK_REASON,
        default_config="configs/experiments/ellipse_2d.json",
        source_paths=(
            "src/psychophysics_lab/experiments/ellipse_2d.py",
            "src/psychophysics_lab/stimulus_library.py",
            "src/psychophysics_lab/adaptive/legacy_flanker.py",
        ),
    )


SPEC = definition()
