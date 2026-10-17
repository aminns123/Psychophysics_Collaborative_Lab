"""Pure translation of the legacy condRule=2 response mathematics.

Source: functionUSE.conditions/conditionRateUPDW at 1c3177594e00f0b26fa361238db0f4db5de403fa.
This is NOT the current CSF staircase: its initial phase and reversal history
are different. Development replay only; see LEGACY_STIMULUS_MIGRATION.md.
"""
from dataclasses import dataclass, field, asdict
import math
from .registry import AdaptiveAlgorithm
from .staircase import Step


def legacy_reversals(values):
    """Literal historical high/low detector, including its short-history quirk."""
    if len(values) <= 1:
        return 1
    direction = 1 if values[1] > values[0] else -1
    count = 0
    for previous, current in zip(values[1:], values[2:]):
        new_direction = 1 if current > previous else -1 if current < previous else direction
        count += new_direction != direction
        direction = new_direction
    return count


@dataclass
class State:
    next_intensity: float
    presented: list = field(default_factory=list)
    correct_ticks: int = 0
    reversal_count: int = 0
    complete: bool = False


class LegacyFlankerAdaptive:
    """Independent condition histories; pure updates via RunContext.adaptive.

    Termination is explicit modern replay policy: retire after the accepted
    response meets the source >9 reversals / >100 trials bounds. The original
    next-trial removal, last-condition wait counter and blocking beeps are not
    reproduced. No result from this adapter qualifies human acquisition.
    """
    def __init__(self, identities, *, background=.24, start_contrast=1., max_trials=40,
                 n_down=3, trial_point=9, reverse_point=1, log_up=.19,
                 log_down=.7393*.19, initial_log_down=.2,
                 reversal_limit=10, condition_trial_limit=101):
        identities = tuple(identities)
        if not identities or len(set(identities)) != len(identities) or any(type(i) is not int or i < 1 for i in identities):
            raise ValueError("Condition identities must be unique positive integers")
        for name, value in locals().copy().items():
            if name in {"max_trials", "n_down", "trial_point", "reverse_point", "reversal_limit", "condition_trial_limit"}:
                if type(value) is not int or value < 1:
                    raise ValueError(f"{name} must be a positive integer")
        for value in (background, start_contrast, log_up, log_down, initial_log_down):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Adaptive parameters must be finite and nonnegative")
        if not 0 <= background < 1 or not 0 < start_contrast <= 1:
            raise ValueError("Invalid background or starting digital contrast")
        self.background, self.max_trials = background, max_trials
        self.n_down, self.trial_point, self.reverse_point = n_down, trial_point, reverse_point
        self.log_up, self.log_down, self.initial_log_down = log_up, log_down, initial_log_down
        self.reversal_limit, self.condition_trial_limit = reversal_limit, condition_trial_limit
        self.states = {i: State(round(background+(1-background)*start_contrast, 8)) for i in identities}
        self.total_trials = 0

    @property
    def active_ids(self):
        return tuple(i for i, state in self.states.items() if not state.complete)

    @property
    def status(self):
        return "completed" if not self.active_ids else "max_trials_reached" if self.total_trials >= self.max_trials else "running"

    def select(self, choose):
        if self.status != "running":
            raise RuntimeError(f"Adaptive run ended: {self.status}")
        identity = choose(self.active_ids)
        if identity not in self.active_ids:
            raise ValueError("Selection must be an active condition")
        return identity

    def preview(self, identity, correct):
        if type(correct) is not bool or identity not in self.active_ids or self.status != "running":
            raise ValueError("Expected an active condition and boolean correctness")
        s = self.states[identity]
        history = s.presented + [s.next_intensity]
        # Original conditions forces totalReverses=0 when count < zero-based nDW.
        reversals = legacy_reversals(history) if len(history) >= self.n_down-1 else 0
        initial = len(history) < self.trial_point and reversals < self.reverse_point
        if not correct:
            step, ticks, delta = Step.UP, 0, self.log_up
        elif initial:
            step, ticks, delta = Step.DOWN, 0, -self.initial_log_down
        elif s.correct_ticks >= self.n_down-1:
            step, ticks, delta = Step.DOWN, 0, -self.log_down
        else:
            step, ticks, delta = Step.HOLD, s.correct_ticks+1, 0.
        contrast = (s.next_intensity-self.background)/(1-self.background)
        value = round(self.background+(1-self.background)*contrast*10**delta, 8)
        return step, value, ticks, reversals, initial

    def respond(self, identity, correct, update_value):
        step, expected, ticks, reversals, initial = self.preview(identity, correct)
        value = update_value(step)
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value-expected) > 1e-12:
            raise ValueError("Update must use the declared legacy log-step candidate")
        s = self.states[identity]
        s.presented.append(s.next_intensity)
        s.next_intensity, s.correct_ticks, s.reversal_count = value, ticks, reversals
        s.complete = reversals >= self.reversal_limit or len(s.presented) >= self.condition_trial_limit
        self.total_trials += 1
        return step, value

    def snapshot(self):
        return {"status": self.status, "total_trials": self.total_trials, "max_trials": self.max_trials,
                "canonical_trial_log": "trials.tsv",
                "completion_rule": "reversals_or_trials",
                "active_staircase_ids": list(self.active_ids),
                "unfinished_staircase_ids": list(self.active_ids),
                "completed_staircase_ids": [i for i,s in self.states.items() if s.complete],
                "stop_policy": "development immediate retirement; legacy delayed termination not reproduced",
                "staircases": {str(i): asdict(s) | {"trial_count": len(s.presented), "last_value": s.next_intensity,
                    "config": {"reversal_limit": self.reversal_limit, "condition_trial_limit": self.condition_trial_limit}}
                    for i, s in self.states.items()}}


SPEC = AdaptiveAlgorithm("legacy_flanker_log", "Legacy flanker condRule=2 mathematics (development)", LegacyFlankerAdaptive, controls=('n_down', 'trial_point', 'reverse_point', 'log_up', 'log_down', 'initial_log_down', 'reversal_limit', 'condition_trial_limit'))
