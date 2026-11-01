"""Modular Ellipse Centre — a readable two-interval psychophysics experiment.

A1: Which stimuli, which conditions, where and when?
A2: How is probe contrast selected, how do staircases stop and what is saved?
B: The small reusable PsyCoLab execution and registration connection.

The rendered mark uses bright display contrast C=(I_mark-I_background)/(1-I_background).
This is a digital command convention, not Weber luminance contrast.
A new, opt-in protocol: do not compare its thresholds directly with historical
ellipse_centre runs, which used raw digital probe increments and additive layers.
"""
import math
import random
import sys

from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.analysis.primary import expected_staircases
from psychophysics_lab.methods.contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod, run_contrast_experiment,
    fixed_level_schedule, parse_fixed_strengths,
)
from psychophysics_lab.methods.probe import unique_probe_conditions, fixed_probe_trial_record
from psychophysics_lab.researcher import (
    AdaptiveSelection, Beep, CollectResponse, ConfigField, ResponseParadigm,
    Show, StaircaseConfig, Step, Stimulus, UpdateAdaptive, WaitForKey,
    experiment,
)


# ── A1 — SCIENTIFIC DESIGN ────────────────────────────────────────────────
EXPERIMENT_ID = "ellipse_modular_centre"
EXPERIMENT_NAME = "Modular Ellipse Centre (software validation)"

# One map, one name per object. No separate slot and default declarations.
# The order and positions in trial_events() decide how these are combined.
STIMULI = {
    "ellipse": "ellipse_ring",
    "probe": "probe_line",
    "fixation": "gaussian_fixation_spot",
}

RESPONSES = ResponseParadigm(EXPERIMENT_ID, ("first", "second"), ("1", "2"))

# Scientific controls below are editable in Configure / Review. Sizes and
# positions are visual DEGREES; the ring radius is a SEMI-AXIS, not diameter.
# "Contrast" means fraction of remaining bright digital headroom above background.
FIELDS = (
    # Background and ellipse
    ConfigField("background_intensity", "Background digital intensity", "float", .5,
                minimum=0, maximum=.999999, units="digital command 0–1", section="Display",
                help_text="Contrast uses (mark-background)/(1-background). Luminance calibration remains separate."),
    ConfigField("ring_present", "Present ellipse ring", "choice", True,
                choices=(True, False), section="Ellipse",
                help_text="Show the ring in both intervals. False produces a no-ring comparison."),
    ConfigField("ring_radius_deg", "Ellipse outer horizontal semi-axis", "float", 6.,
                minimum=.17, maximum=20, units="degrees", section="Ellipse",
                help_text="The full horizontal diameter is twice this radius before orientation."),
    ConfigField("aspect_ratios", "Ellipse vertical/horizontal ratios", "text", ".5,.75,1",
                units="b/a, unitless", section="Ellipse",
                help_text="Comma-separated distinct ratios; each ratio is a separate scientific condition."),
    ConfigField("ring_inset_deg", "Inner ring axial inset", "float", .16,
                minimum=.001, maximum=5, units="degrees", section="Ellipse",
                help_text="Both semi-axes are reduced by this amount; not uniform normal stroke thickness."),
    ConfigField("ring_display_contrast", "Ellipse ring display contrast", "float", .2,
                minimum=0, maximum=1, units="upper-headroom fraction", section="Ellipse"),
    ConfigField("ring_orientation_deg", "Ellipse orientation", "float", 0.,
                minimum=-180, maximum=180, units="degrees anticlockwise", section="Ellipse"),
    ConfigField("ring_centre_x_deg", "Ellipse centre X", "float", 0.,
                minimum=-20, maximum=20, units="degrees from fixation", section="Ellipse"),
    ConfigField("ring_centre_y_deg", "Ellipse centre Y", "float", .6,
                minimum=-20, maximum=20, units="degrees from fixation", section="Ellipse"),

    # Probe: one interval only. These offsets are RELATIVE to the ring centre.
    ConfigField("probe_offset_x_deg", "Probe X offset from ellipse centre", "float", 0.,
                minimum=-20, maximum=20, units="degrees", section="Probe"),
    ConfigField("probe_offset_y_deg", "Probe Y offset from ellipse centre", "float", 0.,
                minimum=-20, maximum=20, units="degrees", section="Probe"),
    ConfigField("probe_length_deg", "Vertical probe length", "float", 1.,
                minimum=.001, maximum=20, units="degrees", section="Probe"),
    ConfigField("probe_width_deg", "Vertical probe width", "float", .013,
                minimum=.0001, maximum=5, units="degrees", section="Probe",
                help_text="Subpixel line visibility is represented using pixel-area coverage."),
    ConfigField("starting_probe_contrast", "Starting probe display contrast", "float", .04,
                minimum=0, maximum=1, units="upper-headroom fraction", section="Probe",
                help_text="Adaptive strength begins here; a log staircase needs a positive value."),

    # Fixation (the same class for session start and each trial).
    ConfigField("fixation_x_deg", "Trial fixation X", "float", 0.,
                minimum=-20, maximum=20, units="degrees", section="Fixation",
                help_text="Trial fixation moves here; once-only session readiness is centred on the screen."),
    ConfigField("fixation_y_deg", "Trial fixation Y", "float", 0.,
                minimum=-20, maximum=20, units="degrees", section="Fixation",
                help_text="Trial fixation moves here; once-only session readiness is centred on the screen."),
    ConfigField("fixation_sigma_deg", "Gaussian fixation sigma", "float", .035,
                minimum=.005, maximum=.1, units="degrees", section="Fixation"),
    ConfigField("fixation_display_contrast", "Fixation display contrast", "float", .18,
                minimum=0, maximum=1, units="upper-headroom fraction", section="Fixation"),

    # Event timeline, presentation and response options.
    ConfigField("ready_key", "Session-start key", "text", "SPACE", section="Timing",
                help_text="Once per session; set SESSION_START=[] in Python to disable."),
    ConfigField("session_settle_ms", "Once-only post-key fixation", "int", 1000,
                minimum=1, units="ms", section="Timing"),
    ConfigField("fixation_ms", "Trial fixation", "int", 500,
                minimum=1, units="ms", section="Timing"),
    ConfigField("stimulus_ms", "Each stimulus interval", "int", 250,
                minimum=1, units="ms", section="Timing"),
    ConfigField("isi_ms", "Gap between intervals", "int", 250,
                minimum=1, units="ms", section="Timing"),
    ConfigField("auditory_cues", "Beep at stimulus onset", "choice", True,
                choices=(True, False), section="Timing"),
    ConfigField("cue_hz", "Beep frequency", "int", 550,
                minimum=37, maximum=32767, units="Hz", section="Timing"),
    ConfigField("cue_ms", "Beep duration", "int", 35,
                minimum=1, maximum=1000, units="ms", section="Timing"),

    # One shared selection interface; each method retains its own semantics.
    ConfigField("contrast_method", "Contrast selection method", "choice", "adaptive",
                choices=("adaptive", "constant_stimuli"), section="Contrast method",
                allow_legacy_default=True),
    ConfigField("fixed_contrasts", "Fixed probe display contrasts", "text", ".01,.02,.04",
                section="Constant stimuli", units="upper-headroom fraction",
                allow_legacy_default=True),
    ConfigField("fixed_repetitions", "Trials per contrast per condition", "int", 10,
                minimum=1, section="Constant stimuli", allow_legacy_default=True),

    # Adaptive staircase parameters are scientific decisions, never hidden in B.
    ConfigField("staircases_per_condition", "Independent staircases per condition", "int", 4,
                minimum=1, section="Adaptive"),
    ConfigField("n_down", "Consecutive correct to decrease", "int", 4,
                minimum=1, section="Adaptive"),
    ConfigField("n_up", "Consecutive incorrect to increase", "int", 1,
                minimum=1, section="Adaptive"),
    ConfigField("logUNIT_UP", "Log10 contrast increase", "float", .36,
                minimum=.000001, units="log10", section="Adaptive"),
    ConfigField("logUNIT_DW", "Log10 contrast decrease", "float", .30294,
                minimum=.000001, units="log10", section="Adaptive"),
    ConfigField("initial_one_down_limit", "Initial one-down responses (0 disables)", "int", 0,
                minimum=0, maximum=1000, section="Adaptive"),
    ConfigField("reversal_termination", "Reversals per staircase", "int", 10,
                minimum=1, section="Adaptive"),
    ConfigField("threshold_reversals", "Final reversals retained", "int", 8,
                minimum=1, section="Adaptive"),
    ConfigField("max_trials", "Global accepted-response safety ceiling", "int", 10000,
                minimum=1, section="Safety",
                help_text="Reaching this ceiling is incomplete, not threshold convergence."),
)

# Only this one opening is executed per session.
SESSION_START = [
    WaitForKey("ready", key="ready_key", slot="fixation", instructions="Press the start key when ready"),
    Show("settle", slot="fixation", duration="session_settle_ms"),
]


def interval_stimuli(settings, condition, interval):
    """Declared order is back → front, not 'opaque rectangles'."""
    result = []
    if condition["ring"]:
        result.append(Stimulus(
            "ellipse", x_deg=settings["ring_centre_x_deg"],
            y_deg=settings["ring_centre_y_deg"],
        ))
    if condition["target"] == interval:
        result.append(Stimulus(
            "probe", x_deg=condition["probe_x_deg"], y_deg=condition["probe_y_deg"],
        ))
    result.append(Stimulus(
        "fixation", x_deg=settings["fixation_x_deg"], y_deg=settings["fixation_y_deg"],
    ))
    return tuple(result)


def trial_events(settings, condition):
    """Two ring intervals; ONLY the target interval contains the probe."""
    cue = Beep(settings["cue_hz"], settings["cue_ms"]) if settings["auditory_cues"] else None
    return [
        Show("fixation", duration="fixation_ms",
             stimuli=(Stimulus("fixation", settings["fixation_x_deg"], settings["fixation_y_deg"]),)),
        Show("interval_one", duration="stimulus_ms",
             stimuli=interval_stimuli(settings, condition, 0), beep=cue),
        Show("inter_interval", duration="isi_ms",
             stimuli=(Stimulus("fixation", settings["fixation_x_deg"], settings["fixation_y_deg"]),)),
        Show("interval_two", duration="stimulus_ms",
             stimuli=interval_stimuli(settings, condition, 1), beep=cue),
        CollectResponse(actions=("first", "second"), slot="fixation"),
    ]


# ── A2 — SCIENTIFIC METHODS AND RESULTS ───────────────────────────────────
# Both methods use headroom-normalized bright display contrast, not optical
# luminance contrast or the historical raw digital probe increment.
SCIENTIFIC_SPEC = {
    "version": "ellipse_modular_centre-2",
    "quantity": "C_disp=(I_probe-I_background)/(1-I_background), same for ring/fixation.",
    "conditions": "Selected ellipse b/a ratio and optional ring; relative probe position is held fixed.",
    "response": "Two intervals: which contains the probe? Exactly one target interval.",
    "layers": "Independent ordered floating-point pixels: ellipse, probe (if target), fixation.",
    "boundary_policy": "Clamp staircase UPDATES at C=1; never clip displayed pixels; boundary holds are not reversals.",
    "stopping": "Target reversal count per staircase; safety ceiling is incomplete.",
    "estimator": "Median of last retained presented reversals, then mean across completed staircases.",
    "physical_qualification": "Display precision, luminance, geometry, timing and input latency not established by simulation.",
}
ADAPTIVE_RULE = AdaptiveSelection(
    "consecutive_up_down",
    controls=("n_down", "n_up", "logUNIT_UP", "logUNIT_DW", "initial_one_down_limit",
              "staircases_per_condition", "reversal_termination", "max_trials"),
    step_calculator="garcia_perez_1998",
    step_parameterization="log10_display_contrast",
)


def make_conditions(settings):
    """Each ratio is a condition; staircase repetitions remain independent."""
    rows = []
    probe_x = settings["ring_centre_x_deg"] + settings["probe_offset_x_deg"]
    probe_y = settings["ring_centre_y_deg"] + settings["probe_offset_y_deg"]
    for ratio in (float(text) for text in settings["aspect_ratios"].split(",")):
        for repeat in range(settings["staircases_per_condition"]):
            rows.append({
                "id": len(rows)+1,
                "value": f"ratio={ratio:g};ring={int(settings['ring_present'])};"
                         f"probe_x={probe_x:g};probe_y={probe_y:g}",
                "aspect_ratio": ratio, "ring": settings["ring_present"],
                "x_deg": probe_x, "probe_x_deg": probe_x, "probe_y_deg": probe_y,
                "repeat": repeat+1,
            })
    return rows


def prepare_stimuli(run, condition, state):
    """One slot per atomic stimulus, with values explicitly from A1 settings."""
    v = run.values
    common = {"background": v["background_intensity"]}
    return {
        "ellipse": run.stimulus_parameters(
            "ellipse", **common, outer_radius_deg=v["ring_radius_deg"],
            aspect_ratio=condition["aspect_ratio"],
            inner_inset_deg=v["ring_inset_deg"],
            orientation_deg=v["ring_orientation_deg"],
            display_contrast=v["ring_display_contrast"],
        ),
        "probe": run.stimulus_parameters(
            "probe", **common, display_contrast=condition["contrast"],
            width_deg=v["probe_width_deg"], length_deg=v["probe_length_deg"],
        ),
        "fixation": run.stimulus_parameters(
            "fixation", **common, sigma_deg=v["fixation_sigma_deg"],
            display_contrast=v["fixation_display_contrast"],
        ),
    }


def validate_settings(values):
    """Also keep invalid draft fields visible in Review; refuse invalid science."""
    try:
        ratios = [float(value) for value in values["aspect_ratios"].split(",")]
        if not ratios or len(set(ratios)) != len(ratios) or any(
            not math.isfinite(r) or not .5 <= r <= 1 for r in ratios
        ):
            yield "Choose distinct finite ellipse b/a ratios from 0.5 to 1."
        elif values["ring_present"] and any(
            values["ring_radius_deg"]*r <= values["ring_inset_deg"] for r in ratios
        ):
            yield "Each inner ellipse semi-axis must exceed the selected axial inset."
    except (ValueError, TypeError, OverflowError):
        yield "Ellipse ratios must be finite comma-separated numbers."
    if values["contrast_method"] == "adaptive" and values["starting_probe_contrast"] <= 0:
        yield "Adaptive log staircases need starting probe contrast above zero."
    if values["threshold_reversals"] > values["reversal_termination"]:
        yield "Threshold reversals cannot exceed staircase reversal termination."
    if values["contrast_method"] == "constant_stimuli":
        try:
            make_fixed_schedule(values, 0)
        except (ValueError, TypeError, KeyError) as exc:
            yield str(exc)


def interpret_response(condition, response):
    correct = response["alternative"] == condition["target"]
    if correct != response["correct"]:
        raise ValueError("Response interpretation disagrees with recorded target.")
    return dict(response) | {"correct": correct}


def fixed_levels(values):
    return parse_fixed_strengths(values["fixed_contrasts"], minimum=0, maximum=1)


def make_fixed_schedule(values, seed):
    cells = unique_probe_conditions(make_conditions(values))
    levels = fixed_levels(values)
    if len(cells)*len(levels)*values["fixed_repetitions"] > values["max_trials"]:
        raise ValueError("Fixed-stimuli plan exceeds the selected max_trials ceiling.")
    return fixed_level_schedule(
        cells, levels, values["fixed_repetitions"], seed=seed,
        condition_field="value", strength_field="contrast",
    )


def select_adaptive(run, conditions, state):
    identity = state["adaptive"].select(state["rng"].choice)
    c = dict(conditions[identity-1])
    c.update(target=state["rng"].randrange(2),
             contrast=state["contrasts"][identity],
             previous_reversals=state["adaptive"].states[identity].reversal_count)
    return c


def primary_rule(settings, conditions):
    return {
        "version": 1, "value_column": "presented_display_contrast",
        "within_staircase": "median", "across_staircases": "arithmetic_mean",
        "retained_reversals": settings["threshold_reversals"],
        "completion": "all configured staircases complete",
        "strength_bounds": {str(c["id"]): [sys.float_info.min, 1.] for c in conditions},
        "units": "headroom_normalized_bright_display_contrast",
    }


def begin_adaptive(run, conditions):
    s = run.values
    tracks = run.adaptive(
        {c["id"]: StaircaseConfig(
            s["n_down"], s["n_up"], s["reversal_termination"], s["initial_one_down_limit"],
        ) for c in conditions},
        s["max_trials"],
        starting_values={c["id"]: s["starting_probe_contrast"] for c in conditions},
    )
    step_scale = max(s["logUNIT_UP"], s["logUNIT_DW"])
    up, down = s["logUNIT_UP"]/step_scale, s["logUNIT_DW"]/step_scale
    target_accuracy = ((up/(up+down))**(1/s["n_down"])) if s["n_up"] == 1 else None
    info = {
        "protocol": dict(SCIENTIFIC_SPEC),
        "asymptotic_accuracy_target": target_accuracy,
        "condition_definitions": conditions,
        "staircases_per_condition": s["staircases_per_condition"],
        "hardware_equivalence": False,
    }
    run.initialise(
        expected_trials=s["max_trials"],
        resolution=info | {
            "primary_estimator": primary_rule(s, conditions),
            "expected_staircases": expected_staircases(conditions),
        },
        background_intensity=s["background_intensity"],
    )
    return {
        "adaptive": tracks, "rng": random.Random(f"{run.seed}:conditions"),
        "contrasts": {c["id"]: s["starting_probe_contrast"] for c in conditions},
        "reversals": {c["id"]: [] for c in conditions}, "description": info,
    }


def trial_record(run, condition, state):
    v = run.values
    return run.adaptive_trial_record(
        state["adaptive"], condition["id"], contrast=condition["contrast"],
        maximum=1., log_up=v["logUNIT_UP"], log_down=v["logUNIT_DW"],
        measurements={
            "probe_x_deg": condition["probe_x_deg"],
            "probe_y_deg": condition["probe_y_deg"],
            "aspect_ratio": condition["aspect_ratio"],
            "ring": condition["ring"],
            "staircase_repeat": condition["repeat"],
        },
        instructions=f"First interval: {run.responses.keys[0]}   Second interval: {run.responses.keys[1]}",
    )


def change_contrast(state, response, step):
    exponent = -state["log_down"] if step == Step.DOWN else (
        state["log_up"] if step == Step.UP else 0
    )
    # Saturate at C=1; flat holds do not count as reversals.
    return bounded_log_step(state["contrast"], exponent, maximum=state["maximum_contrast"])


def update_adaptive(run, condition, state, response, trial):
    staircase, identity = state["adaptive"], condition["id"]
    trial.apply(
        UpdateAdaptive(staircase, identity, change_contrast, state_key="next_contrast"),
        run.staircase_record_action(staircase, identity),
    )
    state["contrasts"][identity] = trial.state["next_contrast"]
    if staircase.states[identity].reversal_count > condition["previous_reversals"]:
        state["reversals"][identity].append(condition["contrast"])
    return state


def finish_adaptive(run, conditions, state):
    run.save_resolution(**state["description"], reversal_contrasts={
        str(identity): values for identity, values in state["reversals"].items()
    })
    run.complete_adaptive(state["adaptive"])
    run.save_primary(primary_rule(run.values, conditions), conditions)


def adaptive_method(run):
    return AdaptiveContrastMethod(
        run, make_conditions=make_conditions, initialise=begin_adaptive,
        select=select_adaptive, record=trial_record, update=update_adaptive,
        finished=lambda _run, _conditions, state: state["adaptive"].status != "running",
        finish=finish_adaptive,
    )


def constant_method(run):
    schedule = make_fixed_schedule(run.values, run.seed)
    return ConstantContrastMethod(
        run, schedule=schedule, record=fixed_probe_trial_record,
        condition_field="value",
        resolution={
            "trial_selection_method": "constant_stimuli",
            "scientific_quantity": "headroom_normalized_bright_display_contrast",
            "protocol": dict(SCIENTIFIC_SPEC),
            "condition_definitions": unique_probe_conditions(make_conditions(run.values)),
            "fixed_contrast_levels": list(fixed_levels(run.values)),
            "fixed_repetitions_per_level_per_condition": run.values["fixed_repetitions"],
            "planned_trials": len(schedule),
            "schedule": [
                {"trial_index": i, "scientific_condition": item["value"],
                 "presented_display_contrast": item["contrast"],
                 "target_alternative": item["target"], "repeat": item["repeat"]}
                for i, item in enumerate(schedule, 1)
            ],
            "response_analysis": "Counts and accuracy by contrast, no adaptive threshold.",
            "hardware_equivalence": False,
        },
    )


# ── B — SMALL FRAMEWORK CONNECTION (normally leave this alone) ──────────
def procedure(run):
    return run_contrast_experiment(
        run, methods={"adaptive": lambda: adaptive_method(run),
                      "constant_stimuli": lambda: constant_method(run)},
        prepare_stimuli=prepare_stimuli, trial_events=trial_events,
        interpret_response=interpret_response,
    )


SPEC = experiment(
    id=EXPERIMENT_ID, name=EXPERIMENT_NAME,
    description="Independent ring, probe and Gaussian fixation with ordered occlusion.",
    procedure=procedure, fields=FIELDS, stimuli=STIMULI,
    responses=RESPONSES, adaptive=ADAPTIVE_RULE,
    session_start=SESSION_START,
    validator=validate_settings,
    method_planner=make_fixed_schedule,
    method_reviewer={"constant_stimuli": constant_method},
    stimulus_field_bindings={"fixation": {
        "background": "background_intensity", "sigma_deg": "fixation_sigma_deg",
        "display_contrast": "fixation_display_contrast",
    }},
    stimulus_parameter_controls={
        "ellipse": {"background": "background_intensity",
                    "display_contrast": "ring_display_contrast",
                    "outer_radius_deg": "ring_radius_deg",
                    "aspect_ratio": "aspect_ratios",
                    "inner_inset_deg": "ring_inset_deg",
                    "orientation_deg": "ring_orientation_deg"},
        "probe": {"background": "background_intensity",
                  "width_deg": "probe_width_deg", "length_deg": "probe_length_deg"},
        "fixation": {"background": "background_intensity",
                     "sigma_deg": "fixation_sigma_deg",
                     "display_contrast": "fixation_display_contrast"},
    },
    scientific_spec=SCIENTIFIC_SPEC, supports_simulation=True,
    calibration_requirements=("geometry", "luminance", "timing"),
    monitor_capabilities=("display_binding", "resolution"),
    acquisition_block_reason=(
        "Software validation only: display geometry, luminance, precision, timing and "
        "response latency require independent qualification before human acquisition."
    ),
    trial_column_overrides={
        "presented_display_contrast": {
            "units_or_encoding": "headroom_normalized_bright_display_contrast",
            "meaning": "Presented digital bright-probe contrast fraction of upper headroom.",
        },
        "next_display_contrast": {
            "units_or_encoding": "headroom_normalized_bright_display_contrast",
            "meaning": "Post-response adaptive contrast, same normalized digital quantity.",
        },
    },
    source_paths=("src/psychophysics_lab/experiments/ellipse_modular_centre.py",),
)
