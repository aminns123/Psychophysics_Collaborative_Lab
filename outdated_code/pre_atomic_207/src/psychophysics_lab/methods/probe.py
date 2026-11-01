"""Reusable contrast-method declarations for the DetectionScene probe family.

Scientific conditions, geometry, stimulus composition and response timing remain
in each experiment file. This module handles only fixed-strength scheduling,
metadata and canonical recording for a digital *probe increment*.

Never equate this increment to optical contrast or a grating's peak-to-peak
modulation. The actual DetectionScene composition must still be validated for
every relevant target/condition, including ring or flanker overlap.
"""

from __future__ import annotations

from types import SimpleNamespace

from psychophysics_lab.experiments._internal.spec import ConfigField
from .contrast import (
    ConstantContrastMethod,
    fixed_level_schedule,
    parse_fixed_strengths,
)


def probe_contrast_fields():
    """Declare a method selector for any existing DetectionScene experiment."""
    return (
        ConfigField(
            "contrast_method", "Contrast selection method", "choice", "adaptive",
            choices=("adaptive", "constant_stimuli"),
            section="Experiment", allow_legacy_default=True,
            help_text="Adaptive retains the study's original staircase; constant stimuli presents preselected digital probe increments."
        ),
        ConfigField(
            "fixed_contrasts", "Fixed digital probe increments", "text",
            "0.005,0.01,0.02", section="Constant stimuli", allow_legacy_default=True,
            units="increment above digital background",
            help_text="Comma-separated absolute digital increments I_probe-I_background, not measured optical contrast or absolute intensity."
        ),
        ConfigField(
            "fixed_repetitions", "Trials per level per scientific condition",
            "int", 10, minimum=1, section="Constant stimuli", allow_legacy_default=True,
            units="presentations",
            help_text="Condition means probe position/ellipse/ring configuration, not independent staircase replicate. Target intervals/sides are seeded and balanced."
        ),
    )


def unique_probe_conditions(rows):
    """Deduplicate independent staircase replicas without losing the science."""
    seen = set()
    unique = []
    for condition in rows:
        identity = condition["value"]
        if identity not in seen:
            seen.add(identity)
            unique.append({
                k: v for k, v in condition.items()
                if k not in {"id", "repeat"}
            })
    if not unique:
        raise ValueError("At least one independent scientific condition is required.")
    return unique


def fixed_contrast_levels(values):
    maximum = 1 - values["background_intensity"]
    try:
        return parse_fixed_strengths(
            values["fixed_contrasts"], minimum=0, maximum=maximum
        )
    except ValueError as exc:
        if "between" in str(exc):
            raise ValueError(
                f"Fixed probe increments must lie between 0 and {maximum:g} "
                f"at background command {values['background_intensity']:g}. "
                "Additional ring/flanker overlap constraints are checked separately."
            ) from exc
        raise


def make_probe_fixed_schedule(values, seed, make_conditions):
    """A named condition x strength x repeat trial plan, same RNG every seed."""
    conditions = unique_probe_conditions(make_conditions(values))
    strengths = fixed_contrast_levels(values)
    count = len(conditions) * len(strengths) * values["fixed_repetitions"]
    if count > values["max_trials"]:
        raise ValueError(
            f"Constant stimuli plans {count} trials, exceeding the selected "
            f"max_trials ceiling ({values['max_trials']}). "
            "Increase the ceiling deliberately or reduce levels/repetitions."
        )
    return fixed_level_schedule(
        conditions,
        strengths,
        values["fixed_repetitions"],
        seed=seed,
        condition_field="value",
        strength_field="contrast",
    )


def validate_probe_fixed_settings(values, make_conditions):
    if values.get("contrast_method", "adaptive") != "constant_stimuli":
        return ()
    try:
        make_probe_fixed_schedule(values, 0, make_conditions)
    except (ValueError, TypeError, KeyError) as exc:
        return (str(exc),)
    return ()


def fixed_probe_trial_record(run, selection):
    """Use the *same* column semantics as adaptive: a digital probe increment."""
    measurements = {
        "fixed_repeat": selection["repeat"],
        "presented_display_contrast": selection["contrast"],
    }
    for key in ("x_deg", "aspect_ratio", "ring"):
        if key in selection:
            measurements[{"x_deg": "probe_x_deg"}.get(key, key)] = selection[key]
    return {
        "state": {"contrast": selection["contrast"]},
        "record_from_state": {"presented_display_contrast": "contrast"},
        "measurements": measurements,
        "instructions": "   ".join(
            f"{alt}: {key}" for alt, key in zip(
                run.responses.alternatives, run.responses.keys
            )
        ),
    }


def probe_constant_method(run, make_conditions, prepare_stimuli, *, scientific_spec=None):
    """Construct a nonadaptive method for a specific scene-based experiment."""
    conditions = unique_probe_conditions(make_conditions(run.values))
    schedule = make_probe_fixed_schedule(run.values, run.seed, make_conditions)
    settings = run.values
    # Same screen-grid and local pixel-overlap headroom as adaptive detection.
    # Validate at the highest selected fixed strength on a temporary settings
    # view; the actual saved settings and scientific source remain unchanged.
    from psychophysics_lab.experiments._internal.detection_limits import resolve_probe_limits
    check_values = dict(settings)
    check_values["starting_probe_intensity"] = (
        settings["background_intensity"] + max(fixed_contrast_levels(settings))
    )
    preflight = SimpleNamespace(
        values=check_values, display=run.display,
        synthetic=run.synthetic, stimulus_parameters=run.stimulus_parameters,
    )
    resolve_probe_limits(preflight, schedule, prepare_stimuli)
    resolution = {
        "trial_selection_method": "constant_stimuli",
        "scientific_quantity": "digital_probe_increment",
        "intensity_mapping": "DetectionScene adds probe increment above digital background with local ring/flanker/gamut validation.",
        "protocol": dict(scientific_spec or {}),
        "condition_definitions": conditions,
        "fixed_contrast_levels": list(fixed_contrast_levels(settings)),
        "fixed_repetitions_per_level_per_condition": settings["fixed_repetitions"],
        "planned_trials": len(schedule),
        "random_seed": run.seed,
        "schedule_algorithm": "Python random MT19937; seed+constant-stimuli; target balance within each condition/level then shuffled interleaving",
        "schedule": [
            {
                "trial_index": i,
                "scientific_condition": item["value"],
                "presented_display_contrast": item["contrast"],
                "target_alternative": item["target"],
                "repeat": item["repeat"],
            } for i, item in enumerate(schedule, 1)
        ],
        "response_analysis": "Per-condition/level counts and accuracy, no staircase reversals or adaptive thresholds.",
        "hardware_equivalence": False,
    }
    return ConstantContrastMethod(
        run,
        schedule=schedule,
        resolution=resolution,
        record=fixed_probe_trial_record,
        condition_field="value",
    )
