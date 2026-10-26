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
    initial_one_down_limit: int = 0

    def __post_init__(self):
        for name in ("n_down", "n_up", "reversal_limit"):
            positive_integer(name, getattr(self, name))
        if (type(self.initial_one_down_limit) is not int
                or not 0 <= self.initial_one_down_limit <= 1000):
            raise ValueError("initial_one_down_limit must be an integer from 0 to 1000.")


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
    initial_one_down_responses: int = 0
    initial_one_down_end_reason: str | None = None

    def observe_recorded_value(self, value):
        """Count sign changes in recorded values, ignoring flat steps.

        Without an explicit starting value, the first recorded update seeds
        the legacy history detector. Modern callers provide the actual starting
        presentation; its first movement then supplies the initial direction.
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

    def __init__(self, configurations, max_trials, *, starting_values=None, response_goal=None):
        if not configurations:
            raise ValueError("At least one staircase is required")
        positive_integer("max_trials", max_trials)
        if response_goal is not None:
            positive_integer("response_goal", response_goal)
            if response_goal > max_trials:
                raise ValueError("response_goal must not exceed max_trials.")
        self.response_goal = response_goal
        self.configurations = dict(configurations)
        if not all(isinstance(c, StaircaseConfig) for c in configurations.values()):
            raise TypeError("Each staircase requires a StaircaseConfig")
        self.states = {identity: StaircaseState(ResponseStreak())
                       for identity in configurations}
        # Modern protocols seed the actual starting presentation so the
        # first change supplies a direction. Omission retains historical
        # recorded-update seeding for saved-protocol replay.
        self.reversal_convention = "recorded_updates"
        if starting_values is not None:
            if set(starting_values) != set(self.states):
                raise ValueError("Starting values must identify every configured staircase.")
            for identity, value in starting_values.items():
                if isinstance(value, bool) or not math.isfinite(value):
                    raise ValueError("Starting staircase values must be finite numbers.")
                self.states[identity].last_value = float(value)
            self.reversal_convention = "starting_presentation"
        self.max_trials = max_trials
        self.total_trials = 0

    @property
    def active_ids(self):
        return tuple(identity for identity, state in self.states.items()
                     if not state.complete)

    @property
    def status(self):
        # Finite teaching protocols terminate by accepted responses, without
        # pretending their unconverged staircases reached reversal limits.
        if self.response_goal is not None and self.total_trials >= self.response_goal:
            return "completed"
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

    def initial_one_down_active(self, identity):
        """True until first incorrect response or N accepted responses (per ID)."""
        config = self.configurations[identity]
        state = self.states[identity]
        return (config.initial_one_down_limit > 0
                and state.initial_one_down_end_reason is None
                and state.initial_one_down_responses < config.initial_one_down_limit)

    def expected_step(self, identity, correct):
        """Preview the next decision without mutating response history."""
        self.require_active(identity)
        config = self.configurations[identity]
        state = self.states[identity]
        effective_down = 1 if self.initial_one_down_active(identity) and correct else config.n_down
        if correct:
            return Step.DOWN if state.streak.correct + 1 >= effective_down else Step.HOLD
        return Step.UP if state.streak.incorrect + 1 >= config.n_up else Step.HOLD

    def respond(self, identity, correct, update_value):
        self.require_active(identity)
        if type(correct) is not bool:
            raise TypeError("Response correctness must be a boolean.")
        config = self.configurations[identity]
        # Failed numeric updates must not partially consume a response or
        # switch out of the introductory 1-down phase.
        old = self.states[identity]
        state = replace(old, streak=replace(old.streak))
        introductory = self.initial_one_down_active(identity)
        effective_down = 1 if introductory and correct else config.n_down
        step = state.streak.respond(correct, effective_down, config.n_up)
        value = update_value(step)
        state.observe_recorded_value(value)
        state.trial_count += 1
        if introductory:
            state.initial_one_down_responses += 1
            if not correct:
                # The first wrong response is evaluated by the user's n-up rule,
                # and exits 1-down for the NEXT accepted presentation.
                state.initial_one_down_end_reason = "first_incorrect"
            elif state.initial_one_down_responses >= config.initial_one_down_limit:
                state.initial_one_down_end_reason = "response_limit"
        state.complete = state.reversal_count >= config.reversal_limit
        self.states[identity] = state
        self.total_trials += 1
        return step, value

    def snapshot(self):
        return {
            **({"response_goal": self.response_goal} if self.response_goal is not None else {}),
            **({"reversal_convention": self.reversal_convention}
               if self.reversal_convention == "starting_presentation" else {}),
            "status": self.status,
            "max_trials": self.max_trials,
            "total_trials": self.total_trials,
            "active_staircase_ids": list(self.active_ids),
            "unfinished_staircase_ids": list(self.active_ids),
            "completed_staircase_ids": [i for i, s in self.states.items() if s.complete],
            "staircases": {str(i): {"config": asdict(self.configurations[i]),
                                    **asdict(s)} for i, s in self.states.items()},
        }
