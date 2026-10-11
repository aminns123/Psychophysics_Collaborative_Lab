"""Response alternatives and encodings, independent of adaptive update rules."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResponseParadigm:
    id: str
    alternatives: tuple[str, ...]
    keys: tuple[str, ...]

    def __post_init__(self):
        if len(self.alternatives) < 2 or len(self.keys) != len(self.alternatives):
            raise ValueError("Provide one key for each of at least two alternatives.")
        if len(set(self.keys)) != len(self.keys) or len(set(self.alternatives)) != len(self.alternatives):
            raise ValueError("Response keys and alternatives must be unique.")

    def decode(self, key: str) -> int:
        try:
            return self.keys.index(key)
        except ValueError as exc:
            raise ValueError(f"Unaccepted response key: {key}") from exc

    def correct(self, target: int, response: int) -> bool:
        if any(type(v) is not int or not 0 <= v < len(self.alternatives) for v in (target, response)):
            raise ValueError("Target and response must identify declared alternatives.")
        return target == response


LEFT_RIGHT = ResponseParadigm("spatial_2afc", ("left", "right"), ("LEFT", "RIGHT"))
TWO_INTERVAL = ResponseParadigm("interval_2afc", ("first", "second"), ("1", "2"))
