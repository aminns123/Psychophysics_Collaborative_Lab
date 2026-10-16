"""Small public API for stimulus authors and experiment procedures.

A procedure receives RunContext: validated values, display profile, adaptive
factory, response paradigm and canonical recorder. It owns presentation,
accepted responses and scientific completion. No framework file paths required.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Any
from .adaptive import AdaptiveSelection, StaircaseConfig, Step, get_algorithm
from .experiments.spec import ConfigField, ExperimentSpec
from .experiments.responses import ResponseParadigm, LEFT_RIGHT, TWO_INTERVAL
from .stimuli.registry import StimulusSpec
from .data.trials import TrialLog
from .data.session import atomic_write_json


def experiment(*, id, name, description, procedure, fields=(), adaptive=None,
               responses=None, source_paths=(), validator=None, monitor_validator=None,
               calibration_requirements=(), calibration_not_applicable="", monitor_capabilities=None):
    """Build a registered experiment without the historical four-file adapter."""
    return ExperimentSpec(id=id, display_name=name, description=description,
        legacy_module=procedure.__module__, legacy_experiment_type=id,
        fields=tuple(fields), procedure=procedure, adaptive=adaptive,
        response_paradigm=responses, source_paths=tuple(source_paths),
        configure_module="psychophysics_lab.researcher", configure_function="configure",
        validator=validator, monitor_validator=monitor_validator,
        calibration_requirements=tuple(calibration_requirements),
        calibration_not_applicable=calibration_not_applicable,
        monitor_capabilities=monitor_capabilities)


class ParticipantAbort(Exception):
    """Raised by RunContext.abort; the runner preserves an aborted run."""


@dataclass
class RunContext:
    values: Mapping[str, Any]
    display: Any
    spec: ExperimentSpec
    run_directory: Path
    synthetic: bool = False
    data_kind: str = "human"
    seed: int = 0
    status: str = field(default="created", init=False)
    accepted_trials: int = field(default=0, init=False)
    expected_trials: int = field(default=0, init=False)

    def initialise(self, *, expected_trials: int, resolution: Mapping, runtime_display=None):
        """Declare the planned response count and resolved scientific settings."""
        if self.status != "created" or type(expected_trials) is not int or expected_trials < 1:
            raise ValueError("Initialise once with a positive expected_trials count.")
        if not resolution:
            raise ValueError("Provide resolved stimulus and task information.")
        if not self.synthetic and not runtime_display:
            raise ValueError("Human presentation must record the actual runtime_display.")
        self.expected_trials = expected_trials
        self.save_resolution(**dict(resolution))
        atomic_write_json(self.run_directory / "runtime_display.json", dict(runtime_display or {
            "physical_display_used": False, "mode": "simulation",
            "monitor_profile_id": self.display.id,
        }))
        self.status = "running"
        self._save_lifecycle()

    def _save_lifecycle(self, reason=""):
        atomic_write_json(self.run_directory / "procedure_lifecycle.json", {
            "schema_version": 1, "status": self.status, "expected_trials": self.expected_trials,
            "accepted_trials": self.accepted_trials, "reason": reason,
        })

    def complete(self):
        """Complete only after every planned accepted response was recorded."""
        if self.status != "running" or self.accepted_trials != self.expected_trials:
            raise ValueError("Cannot complete: planned responses are missing or the procedure is not running.")
        self.status = "completed"
        self._save_lifecycle()

    def abort(self, reason="Participant stopped the experiment"):
        if self.status == "completed":
            raise ValueError("Cannot abort a completed procedure.")
        self.status = "aborted_by_user"
        self._save_lifecycle(reason)
        raise ParticipantAbort(reason)

    def fail(self, reason):
        self.status = "error"
        self._save_lifecycle(str(reason))
        raise RuntimeError(reason)

    @property
    def responses(self):
        return self.spec.response_paradigm

    def adaptive(self, *args, **kwargs):
        if self.spec.adaptive is None:
            raise ValueError("This experiment has not declared an adaptive algorithm.")
        return get_algorithm(self.spec.adaptive.algorithm_id).factory(*args, **kwargs)

    def record(self, **trial):
        """Append one accepted response using the documented canonical columns."""
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Record responses only in a running procedure within its planned trial count.")
        required = {"stimulus_condition", "target_alternative", "participant_response", "response_key", "correct"}
        if required - trial.keys():
            raise ValueError(f"Response is missing canonical fields: {sorted(required - trial.keys())}")
        trial["trial_index"] = self.accepted_trials + 1
        trial["run_status"] = "running"
        if self.synthetic:
            trial["response_key"] = "SIMULATED_" + str(trial.get("response_key", ""))
            from .core.synthetic import synthetic_recorded_utc
            trial.setdefault("event_time_s", float(self.accepted_trials + 1))
            trial["recorded_utc"] = synthetic_recorded_utc(trial["event_time_s"])
        TrialLog(self.run_directory / "trials.tsv").append(trial)
        self.accepted_trials += 1
        self._save_lifecycle()

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
