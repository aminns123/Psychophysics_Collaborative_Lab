"""Small public API for stimulus authors and experiment procedures.

A procedure receives RunContext: validated values, display profile, adaptive
factory, response paradigm and canonical recorder. It owns presentation,
accepted responses and scientific completion. No framework file paths required.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Any
from .adaptive import AdaptiveSelection, StaircaseConfig, Step, get_algorithm
from .experiments.spec import ConfigField, ExperimentSpec
from .experiments.responses import ResponseParadigm, LEFT_RIGHT, TWO_INTERVAL
from .stimuli.registry import StimulusSpec
from .data.trials import TrialLog
from .data.session import atomic_write_json


def experiment(*, id, name, description, procedure, fields=(), adaptive=None,
               responses=None, source_paths=(), validator=None, monitor_validator=None):
    """Build a registered experiment without the historical four-file adapter."""
    return ExperimentSpec(id=id, display_name=name, description=description,
        legacy_module=procedure.__module__, legacy_experiment_type=id,
        fields=tuple(fields), procedure=procedure, adaptive=adaptive,
        response_paradigm=responses, source_paths=tuple(source_paths),
        configure_module="psychophysics_lab.researcher", configure_function="configure",
        validator=validator, monitor_validator=monitor_validator)


@dataclass
class RunContext:
    values: Mapping[str, Any]
    display: Any
    spec: ExperimentSpec
    run_directory: Path
    synthetic: bool = False
    data_kind: str = "human"

    @property
    def responses(self):
        return self.spec.response_paradigm

    def adaptive(self, *args, **kwargs):
        if self.spec.adaptive is None:
            raise ValueError("This experiment has not declared an adaptive algorithm.")
        return get_algorithm(self.spec.adaptive.algorithm_id).factory(*args, **kwargs)

    def record(self, **trial):
        """Append one accepted response using the documented canonical columns."""
        if self.synthetic:
            trial["response_key"] = "SIMULATED_" + str(trial.get("response_key", ""))
        TrialLog(self.run_directory / "trials.tsv").append(trial)

    def save_adaptive(self, algorithm):
        atomic_write_json(self.run_directory / "adaptive_session.json", algorithm.snapshot())

    def save_resolution(self, **details):
        """Record experiment-owned stimulus/timing definitions for later review."""
        atomic_write_json(self.run_directory / "resolved_experiment.json",
                          {"experiment_id": self.spec.id, **details})


def configure(participant_id, data_root, setup, *, run_directory):
    """Internal bridge: contributors use procedure(context), not this function."""
    state = Path(run_directory) / "state"
    conditions, parameters = state / "conditions.runtime.json", state / "parameters.runtime.json"
    for path in (conditions, parameters, state / "user_experiment_config.json"):
        atomic_write_json(path, setup)
    response = Path(run_directory) / "legacy_response.txt"
    response.write_text("", encoding="utf-8")
    return str(conditions), str(parameters), str(response)
