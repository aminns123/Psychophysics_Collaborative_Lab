"""Display-independent consecutive-response rules and adaptive run lifecycle.

The experiment supplies correctness, numeric updates, limits and selection.
There are no stimulus types, response keys, contrast definitions or CSF defaults.
"""

from dataclasses import asdict, dataclass, replace
from enum import IntEnum
import math


class Step(IntEnum):
    DOWN = 0
    UP = 1
    HOLD = 2


def positive_integer(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class StaircaseConfig:
    n_down: int
    n_up: int
    reversal_limit: int

    def __post_init__(self):
        for name in ("n_down", "n_up", "reversal_limit"):
            positive_integer(name, getattr(self, name))


@dataclass
class ResponseStreak:
    correct: int = 0
    incorrect: int = 0

    def respond(self, correct, n_down, n_up):
        positive_integer("n_down", n_down)
        positive_integer("n_up", n_up)
        if not isinstance(correct, bool):
            raise TypeError("correct must be a boolean supplied by the experiment")
        if correct:
            self.incorrect = 0
            self.correct += 1
            if self.correct == n_down:
                self.correct = 0
                return Step.DOWN
        else:
            self.correct = 0
            self.incorrect += 1
            if self.incorrect == n_up:
                self.incorrect = 0
                return Step.UP
        return Step.HOLD


@dataclass
class StaircaseState:
    streak: ResponseStreak
    trial_count: int = 0
    reversal_count: int = 0
    last_value: float = None
    last_direction: int = 0
    complete: bool = False

    def observe_recorded_value(self, value):
        """Count sign changes in recorded values, ignoring flat steps.

        The first recorded response value seeds the sequence, as in the legacy
        history detector. The starting presentation is not an extra observation.
        """
        if not math.isfinite(value):
            raise ValueError("Updated staircase value must be finite")
        if self.last_value is not None:
            direction = (value > self.last_value) - (value < self.last_value)
            if direction:
                if self.last_direction and direction != self.last_direction:
                    self.reversal_count += 1
                self.last_direction = direction
        self.last_value = value


class AdaptiveRun:
    """Stable staircase identities and an experiment-wide response ceiling.

    A numeric update callback receives DOWN/UP/HOLD; the experiment owns the
    step mathematics and returns the next recorded numeric value. Other adaptive
    procedures need not use this class or a boolean-correctness interface.
    """

    def __init__(self, configurations, max_trials):
        if not configurations:
            raise ValueError("At least one staircase is required")
        positive_integer("max_trials", max_trials)
        self.configurations = dict(configurations)
        if not all(isinstance(c, StaircaseConfig) for c in configurations.values()):
            raise TypeError("Each staircase requires a StaircaseConfig")
        self.states = {identity: StaircaseState(ResponseStreak())
                       for identity in configurations}
        self.max_trials = max_trials
        self.total_trials = 0

    @property
    def active_ids(self):
        return tuple(identity for identity, state in self.states.items()
                     if not state.complete)

    @property
    def status(self):
        if not self.active_ids:
            return "completed"
        if self.total_trials >= self.max_trials:
            return "max_trials_reached"
        return "running"

    def require_active(self, identity):
        if self.status != "running":
            raise RuntimeError(f"Run has ended: {self.status}")
        if identity not in self.states:
            raise KeyError(identity)
        if self.states[identity].complete:
            raise ValueError(f"Staircase {identity!r} is complete")

    def select(self, choose):
        if self.status != "running":
            raise RuntimeError(f"Run has ended: {self.status}")
        identity = choose(self.active_ids)
        self.require_active(identity)
        return identity

    def respond(self, identity, correct, update_value):
        self.require_active(identity)
        config = self.configurations[identity]
        # Failed numeric updates must not partially consume a response.
        old = self.states[identity]
        state = replace(old, streak=replace(old.streak))
        step = state.streak.respond(correct, config.n_down, config.n_up)
        value = update_value(step)
        state.observe_recorded_value(value)
        state.trial_count += 1
        state.complete = state.reversal_count >= config.reversal_limit
        self.states[identity] = state
        self.total_trials += 1
        return step, value

    def snapshot(self):
        return {
            "status": self.status,
            "max_trials": self.max_trials,
            "total_trials": self.total_trials,
            "active_staircase_ids": list(self.active_ids),
            "unfinished_staircase_ids": list(self.active_ids),
            "completed_staircase_ids": [i for i, s in self.states.items() if s.complete],
            "staircases": {str(i): {"config": asdict(self.configurations[i]),
                                    **asdict(s)} for i, s in self.states.items()},
        }
