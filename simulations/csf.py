"""CSF-specific virtual observer and real legacy acquisition event adapter.

Condition values are the retained legacy units (63, 252), NOT verified c/deg.
The model threshold is its midpoint between chance and ceiling; it is not the
reversal estimator's guaranteed convergence point.
"""
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
import io
import json
import math
from pathlib import Path
import random
from types import SimpleNamespace


@dataclass(frozen=True)
class CSFObserver:
    threshold: float = 0.10
    preferred_condition: float = 63.0
    tuning_width_octaves: float = 2.0
    slope: float = 3.0
    lapse: float = 0.02

    def __post_init__(self):
        for name in ("threshold", "preferred_condition", "tuning_width_octaves", "slope"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        if isinstance(self.lapse, bool) or not math.isfinite(self.lapse) or not 0 <= self.lapse < .5:
            raise ValueError("lapse must be in [0, 0.5).")

    def probability_correct(self, contrast, condition):
        if not math.isfinite(contrast) or contrast < 0 or not math.isfinite(condition) or condition <= 0:
            raise ValueError("Observer needs finite nonnegative contrast and positive condition.")
        if contrast == 0:
            return .5
        offset = math.log2(condition / self.preferred_condition) / self.tuning_width_octaves
        # Compute in log space to avoid overflowing extreme tuning/contrast.
        log_threshold = math.log(self.threshold) + .5 * offset * offset
        log_odds = self.slope * (math.log(contrast) - log_threshold)
        fraction = 1 / (1 + math.exp(-max(-700., min(700., log_odds))))
        return .5 + (.5 - self.lapse) * fraction


DEFAULT_VALUES = {"Max_monitor_Luminance": 500., "Background_Luminance": 49.,
                  "Background_Screen_intensity": .374, "max_trials": 400,
                  "reversal_termination": 12}


def runtime(observer, seed, algorithm_id):
    """Factory with its own RNG; no monkeypatching, global seeding or graphics."""
    def acquire(conditions, parameters, response, state):
        from Events.adaptive_session import LegacyStaircaseSession
        from Events.adaptiveMethods import Trials_read_write_staircase_conditions
        from Events.display_contrast import normalized_display_contrast
        import Functions.functionsForUse as funcs
        from psychophysics_lab.data.session import atomic_write_json
        rng = random.Random(seed)
        root = Path(response).parent
        data = funcs.read_JSON(conditions)
        data["2AFC_choice"] = [10, 20]  # mock pixel positions, no physical claim
        funcs.create_JSON(conditions, data)
        params = funcs.read_JSON(parameters)
        session = LegacyStaircaseSession(conditions, parameters, response,
            max_trials=params["max_trials"], metadata_path=root / "adaptive_session.json",
            algorithm_id=algorithm_id, synthetic=True)
        atomic_write_json(root / "runtime_display.json", {"data_kind": "synthetic",
            "hardware": "none", "timing_status": "unverified", "photon_timing_verified": False})
        atomic_write_json(root / "resolved_experiment.json", {"experiment_id": "contrast_sensitivity",
            "data_kind": "synthetic", "observer": asdict(observer), "seed": seed,
            "condition_units": "legacy CSF units; not calibrated cycles/degree",
            "adaptive_parameters": {
                "n_down": params["n_dw"], "n_up": params["n_up"],
                "logUNIT_UP": params["logUNIT_UP"], "logUNIT_DW": params["logUNIT_DW"],
                "reversal_termination": params["reversal_termination"],
                "max_accepted_responses": session.run.max_trials,
            },
            "virtual_substitutions": {
                "observer_responses": "seeded psychometric choice probabilities",
                "input_device": "simulated accepted response events, not physical keyboard",
                "stimulus_position": "two mocked choices at 10/20 pixels, not a rendered grating",
                "clock": "deterministic virtual time, not measured photon onset or reaction time",
                "timing_values": "experiment settings recorded but NOT physically played by Pyglet",
            }})
        window = SimpleNamespace(trials=[], exit=lambda: None)
        logger = session.logger(window)
        try:
            with redirect_stdout(io.StringIO()):
                while session.run.status == "running":
                    target = rng.randrange(2)
                    def trial(name):
                        result = session.attach(Trials_read_write_staircase_conditions(name, [], 250,
                            [10 if target == 0 else 20, 0], conditions, parameters, response, keys=["LEFT", "RIGHT"]))
                        result.choose = rng.choice
                        result.feedback_enabled = False
                        return result
                    event_time = session.run.total_trials * 1.0  # deterministic mock clock
                    logger("TRIAL", event_time, trial("new_condition"), [])
                    current = funcs.read_JSON(conditions)
                    identity = current["staircase_Identity_active"][0]
                    contrast = normalized_display_contrast(current["staircase_intensity_active"][identity],
                        background_intensity=params["background_intensity"], maximum_intensity=params["max_intensity"])
                    correct = rng.random() < observer.probability_correct(contrast, current["condition_list"][identity])
                    answer = target if correct else 1 - target
                    key = "LEFT" if answer == 0 else "RIGHT"
                    response_trial = trial("response")
                    logger("TRIAL", event_time, response_trial, [])
                    logger("KEY", event_time, response_trial, [key, key])
        except BaseException as exc:
            session.save(status="error", error=exc)
            raise
        finally:
            session.finish()
            funcs.removeZeroRow(response)
            funcs.correctFileSpacings(response)
    return acquire
