"""Small public API for stimulus authors and experiment procedures.

A procedure receives RunContext: validated values, display profile, adaptive
factory, response paradigm and canonical recorder. It owns presentation,
accepted responses and scientific completion. No framework file paths required.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Any
from .adaptive import AdaptiveSelection, AdaptiveAlgorithm, StaircaseConfig, Step, get_algorithm
from .experiments.spec import ConfigField, ExperimentSpec
from .experiments.responses import ResponseParadigm, LEFT_RIGHT, TWO_INTERVAL
from .stimuli.registry import StimulusSpec
from .data.trials import TrialLog
from .data.session import atomic_write_json


def experiment(*, id, name, description, procedure, fields=(), adaptive=None,
               responses=None, source_paths=(), validator=None, monitor_validator=None,
               calibration_requirements=(), calibration_not_applicable="", monitor_capabilities=None,
               stimulus_slots=None, stimulus_defaults=None, supports_simulation=False):
    """Build a registered experiment without the historical four-file adapter."""
    if responses is not None and "response_keys" not in {item.key for item in fields}:
        fields = tuple(fields) + (ConfigField("response_keys", "Response keys (in alternative order: " + ", ".join(responses.alternatives) + ")", "text", default=",".join(responses.keys), section="Response mapping"),)
    return ExperimentSpec(id=id, display_name=name, description=description,
        legacy_module=procedure.__module__, legacy_experiment_type=id,
        fields=tuple(fields), procedure=procedure, adaptive=adaptive,
        response_paradigm=responses, source_paths=tuple(source_paths),
        configure_module="psychophysics_lab.researcher", configure_function="configure",
        validator=validator, monitor_validator=monitor_validator,
        calibration_requirements=tuple(calibration_requirements),
        calibration_not_applicable=calibration_not_applicable,
        monitor_capabilities=monitor_capabilities,
        stimulus_slots=stimulus_slots or {}, stimulus_defaults=stimulus_defaults or {}, supports_simulation=supports_simulation)


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
    stimulus_snapshots: dict = field(default_factory=dict)
    observer_parameters: dict = field(default_factory=dict)
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
            if not self.spec.stimulus_slots:
                raise ValueError("Human presentation must record the actual runtime_display.")
            from .core.presentation import Presentation
            self._presentation = Presentation(self.display, self.responses)
            runtime_display = self._presentation.metadata
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
        if self.spec.response_paradigm is not None and self.values.get("response_keys"):
            from dataclasses import replace
            keys = tuple(self.values["response_keys"].split(","))
            if keys != self.spec.response_paradigm.keys:
                return replace(self.spec.response_paradigm, keys=keys)
        return self.spec.response_paradigm

    def stimulus_parameters(self, slot="target", **overrides):
        from .stimuli.registry import get_stimulus
        selected = self.stimulus_snapshots[slot]["document"]
        return get_stimulus(selected["stimulus_id"]).validate_parameters(selected["parameters"] | overrides)

    def present(self, *, slot="target", target, condition, parameters=None, instructions=""):
        """Present a registered stimulus, collect a mapped response, and durably record it."""
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Present only during the running procedure's planned trials.")
        import random
        from .stimuli.registry import get_stimulus
        from .core.presentation import Response, render_pixels
        selected = self.stimulus_snapshots[slot]["document"]
        stimulus = get_stimulus(selected["stimulus_id"])
        parameters = stimulus.validate_parameters(parameters or selected["parameters"])
        self.responses.correct(target, target)  # Validate the task's declared target.
        if self.synthetic:
            render_pixels(stimulus, parameters)  # Exercise the actual scientific renderer headlessly.
            if not hasattr(self, "_rng"):
                self._rng = random.Random(self.seed)
            probability = float(self.observer_parameters.get("accuracy", .85))
            answer = target if self._rng.random() < probability else self._rng.choice([i for i in range(len(self.responses.keys)) if i != target])
            response = Response(answer, self.responses.keys[answer], .25 + .25*self._rng.random())
        else:
            response = self._presentation.present(stimulus, parameters, instructions)
        correct = self.responses.correct(target, response.alternative)
        self.record(stimulus_condition=condition, target_alternative=target,
                    participant_response=response.alternative, response_key=response.key, correct=int(correct))
        if not hasattr(self, "_presentations"):
            self._presentations = []
        self._presentations.append({"trial_index": self.accepted_trials, "slot": slot,
            "stimulus_id": stimulus.id, "parameters": parameters,
            "reaction_time_s": response.reaction_time_s,
            "time_basis": "virtual observer" if self.synthetic else "software flip to key event; latency unverified"})
        atomic_write_json(self.run_directory / "trial_presentations.json", {"schema_version": 1, "trials": self._presentations})
        return correct

    def play_trial(self, timeline, *, target, condition, parameters_by_slot=None, instructions="", measurements=None):
        """Run ordered stages; save one response and phase observations per trial.

        Experiments own the timeline, condition and adaptive update. PsyCoLab
        owns rendering, response collection, accepted-trial state and files.
        """
        import random
        from .core.timeline import TrialTimeline, simulated_phases
        from .core.presentation import Response, render_pixels
        from .stimuli.registry import get_stimulus
        if not isinstance(timeline, TrialTimeline):
            raise TypeError("play_trial requires a TrialTimeline; use load_timeline or Phase.")
        # Extra scientific observations use the versioned presentation JSON,
        # never undocumented columns in the fixed legacy trials.tsv schema.
        import json
        import math
        observations = dict(measurements or {})
        for key, value in observations.items():
            if not isinstance(key, str) or not key.isidentifier():
                raise ValueError("Custom measurement keys must be Python identifiers.")
            if type(value) not in (int, float, str, bool) or (type(value) is float and not math.isfinite(value)):
                raise ValueError(f"Measurement {key} must be a finite number, string or boolean.")
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Start a timeline only while a response is expected.")
        timeline.validate_slots(self.stimulus_snapshots)
        self.responses.correct(target, target)
        resolved = {}
        for stage in timeline.phases:
            if stage.slot is None or stage.slot in resolved:
                continue
            selected = self.stimulus_snapshots[stage.slot]["document"]
            stimulus = get_stimulus(selected["stimulus_id"])
            overrides = (parameters_by_slot or {}).get(stage.slot, selected["parameters"])
            params = stimulus.validate_parameters(overrides)
            resolved[stage.slot] = (stimulus.id, params)
        if self.synthetic:
            # Validate ALL shown stimuli, not just the one paired with the response.
            for name, params in resolved.values():
                render_pixels(get_stimulus(name), params)
            if not hasattr(self, "_rng"):
                self._rng = random.Random(self.seed)
            probability = float(self.observer_parameters.get("accuracy", .85))
            alternative = target if self._rng.random() < probability else self._rng.choice(
                [i for i in range(len(self.responses.keys)) if i != target])
            response = Response(alternative, self.responses.keys[alternative], .25 + .25 * self._rng.random())
            phase_events = simulated_phases(timeline)
        else:
            response, phase_events = self._presentation.play_timeline(
                timeline, resolved, instructions=instructions)
        correct = self.responses.correct(target, response.alternative)
        self.record(stimulus_condition=condition, target_alternative=target,
                    participant_response=response.alternative, response_key=response.key, correct=int(correct))
        if not hasattr(self, "_presentations"):
            self._presentations = []
        # A response may use a blank screen: associate saved response with the
        # last scientific stimulus slot presented in the timeline.
        response_slot = next((p.slot for p in reversed(timeline.phases) if p.slot is not None), None)
        if response_slot is None:
            raise ValueError("An experimental timeline requires a stimulus slot.")
        self._presentations.append({"trial_index": self.accepted_trials, "slot": response_slot,
            "stimulus_id": resolved[response_slot][0], "parameters": resolved[response_slot][1],
            "reaction_time_s": response.reaction_time_s,
            "phase_events": phase_events, "measurements": observations,
            "timing_basis": "virtual observer" if self.synthetic else "software flip to key event; latency unverified"})
        atomic_write_json(self.run_directory / "trial_presentations.json",
                          {"schema_version": 1, "trials": self._presentations})
        return correct

    def update_adaptive(self, algorithm, identity, correct, update_value):
        """Use a registered staircase's update contract and save each accepted update."""
        result = algorithm.respond(identity, correct, update_value)
        if not hasattr(self, "_adaptive_history"):
            self._adaptive_history = []
        self._adaptive_history.append({"trial_index": self.accepted_trials, "state": algorithm.snapshot()})
        atomic_write_json(self.run_directory / "adaptive_history.json", {"schema_version": 1,
            "algorithm_id": self.spec.adaptive.algorithm_id, "updates": self._adaptive_history})
        return result

    def close(self):
        if hasattr(self, "_presentation"):
            self._presentation.close()

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
