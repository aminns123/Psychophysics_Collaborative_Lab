"""Seeded repeated-observer recovery diagnostics; no hardware or acquisition IO.

The count/step operating point is derived from the stationary n-down/one-up
cycle: p**n * down = (1-p**n)*up. Other n-up settings require separate validation.
Intervals below describe the distribution of repeated estimates, not human CIs.
"""

import math
import random
from statistics import median
import numpy as np
from psychophysics_lab.adaptive import AdaptiveRun, StaircaseConfig
from .psychometric import PsychometricObserver


def operating_point(n_down, n_up, log_up, log_down):
    if (
        type(n_down) is not int or n_down < 1
        or type(n_up) is not int or n_up != 1
        or any(type(step) not in (int, float) or not math.isfinite(step) or step <= 0
               for step in (log_up, log_down))
    ):
        raise ValueError(
            "Recovery operating point requires finite positive numeric steps and n-down/one-up counts."
        )
    scale = max(log_up, log_down)
    up, down = log_up / scale, log_down / scale
    return (up / (up + down)) ** (1 / n_down)


def recover(
    *,
    threshold=0.02,
    lapse=0.02,
    seeds=200,
    n_down=4,
    n_up=1,
    log_up=0.36,
    log_down=0.30294,
    reversal_limit=10,
    retained=8,
    repeats=4,
    ceiling=10000,
    maximum=1.0,
    estimator="median",
):
    counts = (seeds, reversal_limit, retained, repeats, ceiling)
    if (
        any(type(count) is not int for count in counts)
        or seeds < 2 or reversal_limit < 1 or retained < 1
        or retained > reversal_limit or repeats < 1 or ceiling < 1
        or any(type(value) not in (float, int) or not math.isfinite(value)
               for value in (threshold, lapse, maximum))
        or threshold <= 0 or not 0 <= lapse < 1 or maximum <= 0
    ):
        raise ValueError("Invalid finite recovery replication, retention, observer or gamut settings.")
    from psychophysics_lab.experiments.contrast_sensitivity import change_contrast
    from psychophysics_lab.analysis.primary import estimate

    target = operating_point(n_down, n_up, log_up, log_down)
    observer = PsychometricObserver(
        threshold=threshold, lapse=lapse, threshold_probability=target
    )
    estimates = []
    boundary_runs = 0
    incomplete = 0
    responses = []
    for seed in range(seeds):
        rng = random.Random(seed)
        algorithm = AdaptiveRun(
            {i: StaircaseConfig(n_down, n_up, reversal_limit) for i in range(repeats)},
            ceiling,
            starting_values={i: threshold for i in range(repeats)},
        )
        contrasts = {i: threshold for i in range(repeats)}
        records = []
        boundary = False
        while algorithm.status == "running":
            identity = algorithm.select(rng.choice)
            contrast = contrasts[identity]
            correct = rng.random() < observer.probability(contrast)
            step = algorithm.expected_step(identity, correct)
            candidate = change_contrast(
                {"contrast": contrast, "log_up": log_up, "log_down": log_down,
                 "maximum_contrast": maximum}, {"correct": correct}, step)
            import sys
            boundary = boundary or candidate >= maximum or candidate <= sys.float_info.min
            previous = algorithm.states[identity].reversal_count
            algorithm.respond(identity, correct, lambda step: candidate)
            records.append(
                {
                    "staircase_id": identity,
                    "stimulus_condition": "threshold",
                    "reversal": int(
                        algorithm.states[identity].reversal_count > previous
                    ),
                    "staircase_complete": int(algorithm.states[identity].complete),
                    "presented_display_contrast": contrast,
                }
            )
            contrasts[identity] = candidate
        responses.append(algorithm.total_trials)
        if boundary:
            boundary_runs += 1
        elif algorithm.status != "completed":
            incomplete += 1
        else:
            result = estimate(
                records,
                {
                    "version": 1,
                    "value_column": "presented_display_contrast",
                    "retained_reversals": retained,
                    "within_staircase": estimator,
                    "across_staircases": "arithmetic_mean",
                },
                {"threshold": list(range(repeats))},
                algorithm.status,
            )
            estimates.append(result["condition_thresholds"]["threshold"]["threshold"])
    values = np.asarray(estimates, dtype=float)
    return {
        "threshold": threshold,
        "threshold_probability": target,
        "lapse": lapse,
        "seeds": seeds,
        "successful_runs": len(estimates),
        "boundary_runs": boundary_runs,
        "incomplete_runs": incomplete,
        "bias_population": "completed runs without bound contact only; boundary-affected/incomplete runs are separately reported",
        "starting_strength": "known model threshold (favourable recovery diagnostic, not an unknown-threshold study)",
        "median_estimate": float(np.median(values)) if len(values) else None,
        "median_log10_bias": (
            float(np.median(np.log10(values / threshold))) if len(values) else None
        ),
        "between_run_16_84_percentiles": (
            np.quantile(values, [0.16, 0.84]).tolist() if len(values) else []
        ),
        "median_responses": median(responses),
        "estimator": estimator,
        "qualification": "model-specific recovery diagnostic; not physical or human validation",
    }


def report():
    return {
        "scenarios": [
            recover(threshold=t, lapse=l)
            for t in (0.005, 0.02, 0.08)
            for l in (0.0, 0.05)
        ]
        + [recover(threshold=0.8, maximum=1.0)]
    }


if __name__ == "__main__":
    import json

    print(json.dumps(report(), indent=2))
