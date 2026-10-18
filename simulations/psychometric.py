"""A stimulus-dependent 2AFC observer with explicit threshold probability.

P(correct) = chance + (1-chance-lapse)*logistic(slope*log10(C/threshold)+offset).
The offset makes the supplied threshold correspond to threshold_probability.
This is a validation model, not a claim that human data follow this function.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PsychometricObserver:
    threshold: float = 0.02
    slope: float = 4.0
    lapse: float = 0.02
    chance: float = 0.5
    threshold_probability: float = 0.8584

    def __post_init__(self):
        if not all(
            type(v) in (float, int) and math.isfinite(v)
            for v in (
                self.threshold,
                self.slope,
                self.lapse,
                self.chance,
                self.threshold_probability,
            )
        ):
            raise ValueError("Psychometric parameters must be finite numeric values.")
        if (
            self.threshold <= 0
            or self.slope <= 0
            or not 0 <= self.lapse < 1
            or not 0 <= self.chance < 1 - self.lapse
        ):
            raise ValueError("Invalid psychometric scale/chance/lapse.")
        if not self.chance < self.threshold_probability < 1 - self.lapse:
            raise ValueError(
                "Threshold probability must lie between chance and upper asymptote."
            )

    def probability(self, contrast):
        if (
            type(contrast) not in (int, float)
            or not math.isfinite(contrast)
            or contrast < 0
        ):
            raise ValueError("Stimulus strength must be finite and nonnegative.")
        if contrast == 0:
            return self.chance
        fraction = (self.threshold_probability - self.chance) / (
            1 - self.chance - self.lapse
        )
        z = self.slope * (math.log10(contrast) - math.log10(self.threshold)) + math.log(
            fraction / (1 - fraction)
        )
        logistic = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
        return self.chance + (1 - self.chance - self.lapse) * logistic

    def probability_correct(self, condition, state, stimuli):
        return self.probability(state["contrast"])
