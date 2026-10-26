"""Reusable strength policies for short teaching and example experiments.

The declared strength is a *digital* quantity (not necessarily optical
contrast). Each experiment keeps its own target placement, timeline and
renderer mapping. Fixed trials share the canonical acquisition/TSV runner.
Existing teaching procedures can be adapted without changing their defaults.
"""

from __future__ import annotations

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
        ConfigField("max_trials", "Maximum planned responses (safety ceiling)",
                    "int", 1000, minimum=1, section="Experiment"),
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
