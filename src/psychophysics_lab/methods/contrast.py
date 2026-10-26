"""Small, stimulus-independent contrast selection strategies.

Experiments own the scientific definition of contrast, valid digital bounds,
conditions, stimulus rendering and response meaning. These policies handle
*selection*, state and stopping without a second experiment runner.

AdaptiveContrastMethod delegates to an experiment's existing tested staircase
functions, so moving to this interface does not change any update equation,
RNG, reversal count or primary estimator. ConstantContrastMethod consumes a
pre-planned schedule and records accepted-response accuracy without inventing
adaptive fields or fitting an unvalidated threshold.

Use the same run.trial() and canonical trial table regardless of method.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
import math
import random
from typing import Any



def parse_fixed_strengths(raw: str, *, minimum: float = 0., maximum: float = 1.) -> tuple[float, ...]:
    """Scientific units/bounds are supplied by the experiment, never assumed.

    E.g. CSF supplies digital peak-to-peak modulation with a symmetric gamut
    limit; a bright probe supplies digital increment and one-sided headroom.
    """
    if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum > maximum:
        raise ValueError("Invalid scientific strength bounds.")
    parts = str(raw).split(",")
    if not parts or any(not part.strip() for part in parts):
        raise ValueError("Enter one or more comma-separated strength values.")
    try:
        levels = tuple(float(part.strip()) for part in parts)
    except ValueError as exc:
        raise ValueError("Strength levels must be comma-separated numbers.") from exc
    if any(not math.isfinite(v) for v in levels):
        raise ValueError("Strength levels must be finite.")
    if len(set(levels)) != len(levels):
        raise ValueError("Strength levels must be distinct; repeat using the repetition count.")
    if any(v < minimum or v > maximum for v in levels):
        raise ValueError(f"Fixed strengths must be between {minimum:g} and {maximum:g}.")
    return levels


def select_contrast_method(name: str, factories: Mapping[str, Callable[[], Any]]):
    """Instantiate only the selected strategy; inactive methods do no work.

    Passing factories (rather than constructed instances) avoids creating an
    adaptive staircase when fixed levels are selected and vice versa.
    """
    try:
        factory = factories[name]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unsupported contrast method: {name!r}") from exc
    return factory()


def fixed_level_schedule(
    conditions: Sequence[float],
    levels: Sequence[float],
    repetitions: int,
    *,
    seed: int,
    condition_field: str = "frequency_cpd",
    strength_field: str = "contrast",
):
    """Generate independent, balanced condition×level repetitions.

    Reproduces the original CSF constant-stimuli RNG and order exactly.
    The caller validates scientific ranges, contrast conventions and the
    trial-count ceiling. This planner does not assume anything about pixels.
    """
    if not conditions or not levels:
        raise ValueError("Fixed levels require at least one condition and strength.")
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) for v in levels):
        raise ValueError("Fixed strengths must be finite numeric quantities.")
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("Fixed repetitions must be a positive whole number.")
    if not condition_field.isidentifier() or not strength_field.isidentifier():
        raise ValueError("Fixed trial field names must be identifiers.")
    if (condition_field == strength_field
            or condition_field in {"target", "repeat"}
            or strength_field in {"target", "repeat", "value"}):
        raise ValueError("Fixed trial fields cannot overwrite schedule keys.")
    rng = random.Random(f"{seed}:constant-stimuli")
    schedule: list[dict] = []
    for condition in conditions:
        if isinstance(condition, Mapping):
            if "value" not in condition:
                raise ValueError("Scientific condition mappings must include a saved 'value'.")
            # Generic experiments may require x_deg, aspect_ratio, ring, etc.
            # Preserve that scientific description in each scheduled trial.
            scientific = dict(condition)
            scientific.pop("id", None)
            scientific.pop("repeat", None)
            value = scientific["value"]
        else:
            scientific = {condition_field: condition}
            value = condition
        for level in levels:
            targets = [0, 1] * (repetitions // 2)
            if repetitions % 2:
                targets.append(rng.randrange(2))
            rng.shuffle(targets)
            for repeat, target in enumerate(targets, 1):
                schedule.append({
                    **scientific,
                    strength_field: level,
                    "repeat": repeat,
                    "target": target,
                    "value": value,
                })
    rng.shuffle(schedule)
    return schedule


def run_contrast_experiment(
    run,
    *,
    methods: Mapping[str, Callable[[], Any]],
    prepare_stimuli: Callable,
    make_trial: Callable,
    interpret_response: Callable,
    prepare_selection: Callable | None = None,
):
    """One scientific trial sequence for every registered contrast method.

    The experiment still declares its conditions, stimuli, timings and
    correctness. Only the strength-selection method has interchangeable
    state/next-trial/update/stop behavior. The same RunContext writes every
    response to the established canonical trial schema.

    Explicit mapping of supported method factories prevents changing another
    experiment's protocol merely because a new method exists in the package.
    """
    method = select_contrast_method(
        run.values.get("contrast_method", "adaptive"), methods
    )
    while not method.is_finished:
        condition = method.next_trial()
        if prepare_selection is not None:
            # Enrich the same scheduled object with target-dependent geometry;
            # preserve policy identity, deterministic ordering and provenance.
            prepare_selection(run, condition)
        stimuli = prepare_stimuli(run, condition, method.state)
        with run.trial(
            make_trial(run.values, condition),
            target=condition["target"],
            condition=condition["value"],
            parameters_by_slot=stimuli,
            **method.trial_record(condition),
        ) as trial:
            response = interpret_response(condition, trial.response)
            method.accept_response(condition, response, trial)
    method.complete()


class AdaptiveContrastMethod:
    """Thin adapter around a *study's existing* adaptive functions.

    No staircase mathematics, stepping, state structure or record logic is
    reimplemented. The callbacks and call sequence mirror the prior procedure.
    """

    def __init__(
        self,
        run,
        *,
        make_conditions: Callable,
        initialise: Callable,
        select: Callable,
        record: Callable,
        update: Callable,
        finished: Callable,
        finish: Callable,
    ):
        self.run = run
        self.conditions = make_conditions(run.values)
        self.state = initialise(run, self.conditions)
        self._select = select
        self._record = record
        self._update = update
        self._finished = finished
        self._finish = finish

    @property
    def is_finished(self) -> bool:
        return self._finished(self.run, self.conditions, self.state)

    def next_trial(self) -> dict:
        if self.is_finished:
            raise ValueError("Adaptive contrast method has finished.")
        return self._select(self.run, self.conditions, self.state)

    def trial_record(self, selection: dict) -> dict:
        return self._record(self.run, selection, self.state)

    def accept_response(self, selection: dict, response: dict, trial):
        self.state = self._update(self.run, selection, self.state, response, trial)

    def complete(self):
        self._finish(self.run, self.conditions, self.state)


class ConstantContrastMethod:
    """Finite, pre-scheduled strengths with no adaptive staircase.

    The experiment supplies its own scientific schedule, canonical record
    projection and run-resolution declaration; the method owns progression
    and per-condition/per-level accepted-response accuracy.
    """

    def __init__(
        self,
        run,
        *,
        schedule: Sequence[dict],
        resolution: Mapping[str, Any],
        record: Callable,
        condition_field: str = "frequency_cpd",
        strength_field: str = "contrast",
    ):
        if not schedule:
            raise ValueError("Constant stimuli require at least one scheduled trial.")
        self.run = run
        self.schedule = schedule
        self.index = 0
        self.state = {}  # Shared prepare_stimuli signature; no adaptive state.
        self._record = record
        self._condition_field = condition_field
        self._strength_field = strength_field
        self._counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
        self._resolution = dict(resolution)
        run.initialise(
            expected_trials=len(schedule),
            resolution=self._resolution,
            **({"background_intensity": run.values["background_intensity"]}
           if "background_intensity" in run.values else {}),
        )

    @property
    def is_finished(self) -> bool:
        return self.index >= len(self.schedule)

    def next_trial(self) -> dict:
        if self.is_finished:
            raise ValueError("Constant-stimuli schedule has finished.")
        return self.schedule[self.index]

    def trial_record(self, selection: dict) -> dict:
        return self._record(self.run, selection)

    def accept_response(self, selection: dict, response: dict, trial):
        if self.is_finished or selection is not self.schedule[self.index]:
            raise ValueError("Constant-stimuli responses must follow the selected schedule.")
        key = (selection[self._condition_field], selection[self._strength_field])
        cell = self._counts[key]
        cell[0] += 1
        cell[1] += int(response["correct"])
        self.index += 1

    def complete(self):
        if not self.is_finished:
            raise ValueError("Cannot complete an unfinished constant-stimuli schedule.")
        # Names are scientific metadata labels; the canonical 20 TSV columns
        # and all previous adaptive result formats stay unchanged.
        completed_resolution = dict(self._resolution)
        completed_resolution["observed_level_accuracy"] = [
            {
                self._condition_field: condition,
                "presented_display_contrast": strength,
                "accepted_trials": counts[0],
                "correct_trials": counts[1],
                "proportion_correct": counts[1] / counts[0],
            }
            for (condition, strength), counts in sorted(self._counts.items())
        ]
        self.run.save_resolution(**completed_resolution)
        self.run.complete()
