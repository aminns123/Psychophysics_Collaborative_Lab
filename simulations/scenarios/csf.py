"""CSF-specific virtual-observer scenarios and scientific diagnostics.

The retained CSF condition values (e.g. 63, 252) have NOT been verified as
cycles/degree. The observer midpoint is not the guaranteed convergence
criterion of the historical fixed-step staircase. Recovery errors are reported
as diagnostics, never silently interpreted as calibration failures.
"""
from __future__ import annotations

import math

from .core import SimulationScenario


def evaluate_csf(observer, records):
    """Compare recovered reversal estimates with observer-defined model midpoints.

    This is a description of estimator bias at the chosen model/seed/counts,
    NOT proof that the estimator asymptotically targets a model midpoint.
    """
    cases = []
    for record in records:
        points = []
        if record.analysis is not None:
            for item in record.analysis.condition_thresholds:
                condition = float(item.condition)
                offset = math.log2(condition / observer.preferred_condition) / observer.tuning_width_octaves
                true_midpoint = observer.threshold * math.exp(0.5 * offset * offset)
                found = item.threshold
                points.append({
                    "condition_legacy_units": condition,
                    "model_midpoint_contrast": true_midpoint,
                    "estimated_reversal_contrast": found,
                    "estimated_to_model_midpoint_ratio": found / true_midpoint,
                    "absolute_log10_ratio": abs(math.log10(found / true_midpoint)) if found > 0 else None,
                })
        predicted = min(points, key=lambda item: item["model_midpoint_contrast"])["condition_legacy_units"] if points else None
        estimated = min(points, key=lambda item: item["estimated_reversal_contrast"])["condition_legacy_units"] if points else None
        cases.append({
            "seed": record.seed,
            "status": record.artifacts.status,
            "accepted_responses": record.artifacts.accepted_trials,
            "model_preferred_condition": observer.preferred_condition,
            "lowest_model_midpoint_at_sampled_condition": predicted,
            "lowest_estimated_threshold_at_sampled_condition": estimated,
            "sampled_preference_direction_matches": predicted == estimated if points else None,
            "conditions": points,
        })
    plausible = all(
        math.isfinite(point["estimated_reversal_contrast"]) and point["estimated_reversal_contrast"] > 0
        and math.isfinite(point["model_midpoint_contrast"]) and point["model_midpoint_contrast"] > 0
        for run in cases for point in run["conditions"]
    )
    return {
        "checks": [{
            "name": "CSF observer midpoint and recovered estimates are finite positive values",
            "passed": plausible,
            "detail": "Scientific consistency check; does not require exact numerical convergence.",
        }],
        "units": "legacy CSF condition values, not calibrated cycles/degree",
        "estimator": "mean of final 80% of post-update reversal observations; not a model midpoint estimator",
        "comparison_interpretation": "diagnostic, not a strict numerical recovery guarantee",
        "runs": cases,
    }


SCENARIOS = (
    SimulationScenario(
        id="csf_baseline",
        experiment_id="contrast_sensitivity",
        description="Seeded full CSF pipeline with a known synthetic contrast midpoint and preferred condition.",
        observer_parameters={"threshold": 0.10, "preferred_condition": 63.0, "tuning_width_octaves": 2.0, "slope": 3.0, "lapse": 0.02},
        experiment_values={"max_trials": 120},
        seeds=(123,),
        expect_analysis=True,
        evaluate=evaluate_csf,
    ),
    SimulationScenario(
        id="csf_short_censored",
        experiment_id="contrast_sensitivity",
        description="One accepted response: record data and final status, but do not invent a threshold estimate.",
        observer_parameters={"threshold": 0.10, "preferred_condition": 63.0},
        experiment_values={"max_trials": 1},
        seeds=(3,),
        expect_analysis=False,
        evaluate=evaluate_csf,
    ),
    SimulationScenario(
        id="csf_shifted_preference",
        experiment_id="contrast_sensitivity",
        description="Shift the virtual preferred condition and compare estimator results across independent seeds.",
        observer_parameters={"threshold": 0.08, "preferred_condition": 252.0, "tuning_width_octaves": 1.0},
        experiment_values={"max_trials": 160},
        seeds=(11, 12),
        expect_analysis=None,
        evaluate=evaluate_csf,
    ),
)
