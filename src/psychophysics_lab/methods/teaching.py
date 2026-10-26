"""Reusable strength policies for short teaching and example experiments.

The declared strength is a *digital* quantity (not necessarily optical
contrast). Each experiment keeps its own target placement, timeline and
renderer mapping. Fixed trials share the canonical acquisition/TSV runner.
Existing teaching procedures can be adapted without changing their defaults.
"""

from __future__ import annotations

from math import log10
import sys

from psychophysics_lab.adaptive import StaircaseConfig, Step
from psychophysics_lab.adaptive.steps import bounded_log_step
from psychophysics_lab.core.timeline import UpdateAdaptive
from psychophysics_lab.experiments._internal.spec import ConfigField
from .contrast import (
    AdaptiveContrastMethod, ConstantContrastMethod,
    fixed_level_schedule, parse_fixed_strengths,
)


def teaching_method_fields(*, default="adaptive", strengths="0.05,0.1,0.2",
                           label="Digital modulation or increment"):
    """Explicitly offer the two methods; optionally preserve a legacy default.

    The 'original' mode is only needed when adapting historical teaching
    procedures that had no contrast-selection choice or adaptive semantics.
    """
    choices = ("adaptive", "constant_stimuli") if default != "original" else (
        "original", "adaptive", "constant_stimuli",
    )
    return (
        ConfigField("contrast_method", "Contrast selection method", "choice",
                    default, choices=choices, section="Experiment",
                    help_text="Original (if offered) preserves the previous teaching task. Adaptive updates strength; constant stimuli draws fixed strength levels."),
        ConfigField("fixed_contrasts", label + " levels", "text", strengths,
                    section="Constant stimuli",
                    help_text="Comma-separated digital modulation/increment levels, not measured optical luminance contrast."),
        ConfigField("fixed_repetitions", "Repetitions per fixed strength",
                    "int", 5, minimum=1, section="Constant stimuli"),
        ConfigField("starting_strength", "Starting adaptive digital strength",
                    "float", 0.2, minimum=0, maximum=1,
                    section="Adaptive settings",
                    help_text="Digital modulation or increment as declared by the experiment."),
        ConfigField("max_trials", "Maximum planned responses (safety ceiling)",
                    "int", 1000, minimum=1, section="Experiment"),
    )


def teaching_adaptive_fields():
    """Controls for studies that did not previously have an adaptive method."""
    return (
        ConfigField("n_down", "Correct answers before decreasing strength", "int", 2,
                    minimum=1, section="Adaptive settings"),
        ConfigField("n_up", "Incorrect answers before increasing strength", "int", 1,
                    minimum=1, section="Adaptive settings"),
        ConfigField("down_factor", "Down-step multiplier", "float", 0.8,
                    minimum=0.000001, maximum=1, section="Adaptive settings"),
        ConfigField("up_factor", "Up-step multiplier", "float", 1.25,
                    minimum=1, section="Adaptive settings"),
    )


def fixed_teaching_schedule(values, seed, *, maximum=1.0, condition="task"):
    levels = parse_fixed_strengths(values["fixed_contrasts"], minimum=0, maximum=maximum)
    repetitions = values["fixed_repetitions"]
    count = len(levels) * repetitions
    if count > values["max_trials"]:
        raise ValueError(
            f"Fixed method plans {count} trials, exceeding max_trials "
            f"({values['max_trials']}). Change the explicit safety ceiling "
            "or reduce strengths/repetitions."
        )
    return fixed_level_schedule(
        [{"value": condition}], levels, repetitions, seed=seed,
        condition_field="value", strength_field="contrast",
    )


def fixed_teaching_record(run, selection):
    return {
        "state": {"contrast": selection["contrast"]},
        "record_from_state": {"presented_display_contrast": "contrast"},
        "measurements": {"fixed_repeat": selection["repeat"],
                         "presented_display_contrast": selection["contrast"]},
        "instructions": "   ".join(f"{alt}: {key}" for alt, key in zip(
            run.responses.alternatives, run.responses.keys
        )),
    }


def constant_teaching_method(run, planner, *, units, display_mapping):
    schedule = planner(run.values, run.seed)
    resolution = {
        "trial_selection_method": "constant_stimuli",
        "controlled_quantity": units,
        "digital_intensity_mapping": display_mapping,
        "fixed_levels": list(dict.fromkeys(c["contrast"] for c in schedule)),
        "fixed_repetitions_per_level": run.values["fixed_repetitions"],
        "planned_trials": len(schedule),
        "random_seed": run.seed,
        "schedule": [
            {"trial_index": i, "scientific_condition": c["value"],
             "presented_display_contrast": c["contrast"],
             "repeat": c["repeat"], "target_alternative": c["target"]}
            for i, c in enumerate(schedule, 1)
        ],
        "response_analysis": "Per-level accepted counts and accuracy, no staircase threshold estimator.",
        "hardware_equivalence": False,
    }
    return ConstantContrastMethod(
        run, schedule=schedule, resolution=resolution,
        record=fixed_teaching_record, condition_field="value",
    )


class OriginalTeachingMethod:
    """Wrap an original fixed-count teaching procedure unchanged by default."""

    def __init__(self, run, *, make_conditions, initialise, choose, record,
                 update, finish):
        self.run = run
        self.conditions = make_conditions(run.values)
        self.state = initialise(run, self.conditions)
        self._choose = choose
        self._record = record
        self._update = update
        self._finish = finish

    @property
    def is_finished(self):
        return self.run.accepted_trials >= len(self.conditions)

    def next_trial(self):
        if self.is_finished:
            raise ValueError("Original teaching procedure already finished.")
        return self._choose(self.run, self.conditions, self.state)

    def trial_record(self, selection):
        return self._record(self.run, selection, self.state)

    def accept_response(self, selection, response, trial):
        if self._update is not None:
            self.state = self._update(self.run, selection, self.state, response, trial)

    def complete(self):
        self._finish(self.run, self.conditions, self.state)


def review_teaching_adaptive(run, make_conditions, choose):
    """Describe a future trial without creating a live staircase or response."""
    conditions = make_conditions(run.values)
    state = {"contrast": run.values["starting_strength"]}
    condition = choose(run, conditions, state)
    condition = dict(condition, contrast=state["contrast"])
    run.initialise(expected_trials=len(conditions), resolution={
        "trial_selection_method": "adaptive",
        "planned_trials": len(conditions),
        "starting_strength": state["contrast"],
        "scientific_estimator": None,
        "note": "Illustrative finite-response teaching adaptation. No threshold estimator.",
    })
    return conditions, condition, state




class TeachingAdaptiveMethod:
    """Finite-trial n-down/n-up teaching rule using the owned adaptive engine.

    This is NOT a threshold estimator. It stops after the scientific teaching
    task's response count, irrespective of reversal convergence.
    """

    def __init__(self, run, *, make_conditions, choose, maximum):
        self.run = run
        self.conditions = make_conditions(run.values)
        self._choose = choose
        start = run.values["starting_strength"]
        if not 0 <= start <= maximum or maximum <= 0:
            raise ValueError(
                f"Starting digital strength {start:g} must lie within "
                f"0 to {maximum:g} for this stimulus."
            )
        run.initialise(
            expected_trials=len(self.conditions),
            resolution={
                "trial_selection_method": "adaptive",
                "adaptive_algorithm": "consecutive_up_down",
                "response_goal": len(self.conditions),
                "scientific_quantity": "study-defined digital strength",
                "starting_strength": start,
                "maximum_strength": maximum,
                "adaptive_parameters": {
                    key: run.values[key] for key in
                    ("n_down", "n_up", "down_factor", "up_factor")
                },
                "scientific_estimator": None,
                "note": "Teaching-only finite-response adaptation; no threshold estimate.",
            },
        )
        self.algorithm = run.adaptive(
            {0: StaircaseConfig(run.values["n_down"], run.values["n_up"],
                                len(self.conditions) + 1)},
            run.values["max_trials"], starting_values={0: start},
        )
        self.maximum = maximum
        self.state = {"contrast": start}
        self._up = log10(run.values["up_factor"])
        self._down = -log10(run.values["down_factor"])

    @property
    def is_finished(self):
        return self.run.accepted_trials >= len(self.conditions)

    def next_trial(self):
        if self.is_finished:
            raise ValueError("The teaching adaptive procedure has finished.")
        chosen = self._choose(self.run, self.conditions, self.state)
        return dict(chosen, contrast=self.state["contrast"])

    def trial_record(self, selection):
        return self.run.adaptive_trial_record(
            self.algorithm, 0, contrast=self.state["contrast"],
            maximum=self.maximum, log_up=self._up, log_down=self._down,
            instructions="   ".join(f"{alt}: {key}" for alt, key in zip(
                self.run.responses.alternatives, self.run.responses.keys
            )),
        )

    @staticmethod
    def _step(values, response, step):
        exponent = (-values["log_down"] if step == Step.DOWN
                    else values["log_up"] if step == Step.UP else 0)
        return bounded_log_step(values["contrast"], exponent,
                                maximum=values["maximum_contrast"])

    def accept_response(self, selection, response, trial):
        trial.apply(
            UpdateAdaptive(self.algorithm, 0, self._step,
                           state_key="next_contrast"),
            self.run.staircase_record_action(self.algorithm, 0),
        )
        self.state["contrast"] = trial.state["next_contrast"]

    def complete(self):
        if not self.is_finished:
            raise ValueError("Teaching adaptive procedure is incomplete.")
        self.run.complete()
