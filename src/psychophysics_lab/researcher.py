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


    @property
    def trial_state(self):
        """Detached read-only scientific state returned by the latest trial."""
        from .core.timeline import immutable_state
        return immutable_state(getattr(self, "_trial_state", {}))

    def present(self, *, slot="target", target, condition, parameters=None, instructions=""):
        """Compatibility self-paced trial through the authoritative action path."""
        from .core.timeline import Phase, TrialTimeline
        return self.play_trial(TrialTimeline((Phase("answer", "response", slot),)),
                               target=target, condition=condition,
                               parameters_by_slot={slot: parameters} if parameters is not None else None,
                               instructions=instructions)

    def play_trial(self, timeline, *, target, condition, parameters_by_slot=None,
                   instructions="", measurements=None, state=None):
        """Execute chronological scientific actions and persist at the trial boundary.

        Callbacks get immutable detached state and response, and return finite JSON
        state. They are trusted scientific functions: do not render or perform IO.
        A valid response is saved even if a later action fails. Partial events and
        state are saved on abort/error; no response is invented before collection.
        """
        import random
        from .core.timeline import (TrialTimeline, Phase, RecordState, UpdateState,
                                    UpdateAdaptive, scientific_snapshot, immutable_state)
        from .core.trial_execution import VirtualPresentation, execute_timeline
        from .core.presentation import Response
        from .stimuli.registry import get_stimulus
        if not isinstance(timeline, TrialTimeline):
            raise TypeError("play_trial requires a TrialTimeline.")
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Start a timeline only while a response is expected.")
        timeline = timeline.resolve(self.values).validate_slots(self.stimulus_snapshots)
        self.responses.correct(target, target)
        observations = scientific_snapshot(dict(measurements or {}))
        for key, value in observations.items():
            if not key.isidentifier() or type(value) not in (int, float, str, bool):
                raise ValueError("Custom measurements require identifier keys and finite scalar values.")
        current = scientific_snapshot(dict(state if state is not None else self.trial_state))
        condition = scientific_snapshot(condition)
        resolved = {}
        for phase in timeline.phases:
            if isinstance(phase, Phase):
                if phase.actions and phase.actions != self.responses.alternatives:
                    raise ValueError("CollectResponse actions must match the declared response meanings in order.")
                for item in phase.placements:
                    if item.slot in resolved:
                        continue
                    selected = self.stimulus_snapshots[item.slot]["document"]
                    stimulus = get_stimulus(selected["stimulus_id"])
                    params = (parameters_by_slot or {}).get(item.slot, selected["parameters"])
                    resolved[item.slot] = (stimulus.id, stimulus.validate_parameters(params))
            if isinstance(phase, UpdateAdaptive):
                if not any(phase.algorithm is item for item in getattr(self, "_algorithms", ())):
                    raise ValueError("UpdateAdaptive requires an algorithm created with run.adaptive().")
        if not resolved:
            raise ValueError("An experimental timeline requires a stimulus slot.")
        response_slot = next(item.slot for phase in reversed(timeline.phases)
                             if isinstance(phase, Phase) for item in reversed(phase.placements))
        events = []
        response_data = None
        accepted_response = None
        correct = None
        trial_index = self.accepted_trials + 1
        trace = {"trial_index": trial_index, "condition": condition, "target": target,
                 "plan": timeline.to_dict(), "resolved_stimuli": scientific_snapshot({
                     slot: {"stimulus_id": identity, "parameters": params}
                     for slot, (identity, params) in resolved.items()}),
                 "initial_state": scientific_snapshot(current), "events": events, "status": "started"}

        def apply(action, response, event):
            nonlocal current, response_data, accepted_response, correct
            if isinstance(action, Phase) and action.kind == "response":
                if response is None:
                    raise ValueError("Response stage ended without a valid response.")
                correct = self.responses.correct(target, response.alternative)
                accepted_response = response
                response_data = {"alternative": response.alternative, "key": response.key,
                                 "meaning": self.responses.alternatives[response.alternative],
                                 "correct": correct, "valid": True,
                                 "reaction_time_s": response.reaction_time_s,
                                 "timing_basis": "virtual observer" if self.synthetic else
                                     "software flip to key; photon onset and HID latency unverified"}
                event["response"] = scientific_snapshot(response_data)
            elif isinstance(action, RecordState):
                captured = {key: current[key] for key in action.fields} if action.fields else current
                event["snapshot"] = scientific_snapshot({
                    "state": captured, "response": response_data,
                    "stimuli": trace["resolved_stimuli"], "condition": condition,
                    "trial_index": trial_index, "action_index": event["action_index"]})
            elif isinstance(action, UpdateState):
                updated = action.function(immutable_state(current), immutable_state(response_data))
                if not isinstance(updated, Mapping):
                    raise ValueError("UpdateState must return a mapping of scientific state.")
                current = scientific_snapshot(updated)
                event["state"] = scientific_snapshot(current)
            elif isinstance(action, UpdateAdaptive):
                if response_data is None:
                    raise ValueError("Adaptive update requires an accepted response.")
                before = scientific_snapshot(action.algorithm.snapshot())
                step, value = self.update_adaptive(action.algorithm, action.identity, correct,
                    lambda step: action.update_value(immutable_state(current),
                                                     immutable_state(response_data), step))
                current[action.state_key] = scientific_snapshot(value)
                event.update(adaptive_before=before, adaptive_after=scientific_snapshot(action.algorithm.snapshot()),
                             step=int(step), state=scientific_snapshot(current))

        self._in_trial = True
        try:
            if self.synthetic:
                if not hasattr(self, "_rng"):
                    self._rng = random.Random(self.seed)
                probability = float(self.observer_parameters.get("accuracy", .85))
                alternative = target if self._rng.random() < probability else self._rng.choice(
                    [i for i in range(len(self.responses.keys)) if i != target])
                backend = VirtualPresentation(Response(alternative, self.responses.keys[alternative],
                                                       .25 + .25 * self._rng.random()))
            else:
                backend = self._presentation
            backend.prepare(timeline, resolved)
            execute_timeline(timeline, backend, events, apply, instructions=instructions)
            trace["status"] = "completed"
        except BaseException as exc:
            trace["status"] = "aborted" if isinstance(exc, ParticipantAbort) else "error"
            trace["error"] = str(exc)
            raise
        finally:
            self._in_trial = False
            self._trial_state = scientific_snapshot(current)
            trace["final_state"] = scientific_snapshot(current)
            # No file access above, from first phase through last action. Flush
            # even on abort/error, before the runner finalizes status and hashes.
            if not hasattr(self, "_action_trials"):
                self._action_trials = []
            self._action_trials.append(trace)
            atomic_write_json(self.run_directory / "trial_actions.json",
                              {"schema_version": 1, "trials": self._action_trials})
            if accepted_response is not None:
                self.record(stimulus_condition=condition, target_alternative=target,
                            participant_response=accepted_response.alternative,
                            response_key=accepted_response.key, correct=int(correct))
                if not hasattr(self, "_presentations"):
                    self._presentations = []
                self._presentations.append({"trial_index": trial_index, "slot": response_slot,
                    "stimulus_id": resolved[response_slot][0], "parameters": resolved[response_slot][1],
                    "reaction_time_s": accepted_response.reaction_time_s,
                    "phase_events": [e for e in events if e["kind"] in {"show", "response"}],
                    "measurements": observations,
                    "timing_basis": response_data["timing_basis"]})
                atomic_write_json(self.run_directory / "trial_presentations.json",
                                  {"schema_version": 1, "trials": self._presentations})
            self._flush_adaptive_history()
        return correct

    def _flush_adaptive_history(self):
        if hasattr(self, "_adaptive_history"):
            atomic_write_json(self.run_directory / "adaptive_history.json", {
                "schema_version": 1, "algorithm_id": self.spec.adaptive.algorithm_id,
                "updates": self._adaptive_history})

    def update_adaptive(self, algorithm, identity, correct, update_value):
        """Use a registered staircase's update contract and save each accepted update."""
        result = algorithm.respond(identity, correct, update_value)
        if not hasattr(self, "_adaptive_history"):
            self._adaptive_history = []
        from .core.timeline import scientific_snapshot
        self._adaptive_history.append({"trial_index": self.accepted_trials + int(getattr(self, "_in_trial", False)),
                                       "state": scientific_snapshot(algorithm.snapshot())})
        if not getattr(self, "_in_trial", False):
            self._flush_adaptive_history()
        return result

    def close(self):
        if hasattr(self, "_presentation"):
            self._presentation.close()

    def adaptive(self, *args, **kwargs):
        if self.spec.adaptive is None:
            raise ValueError("This experiment has not declared an adaptive algorithm.")
        algorithm = get_algorithm(self.spec.adaptive.algorithm_id).factory(*args, **kwargs)
        if not hasattr(self, "_algorithms"):
            self._algorithms = []
        self._algorithms.append(algorithm)
        return algorithm

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

# Small public chronological vocabulary; existing Phase/JSON stays compatible.
from .core.timeline import (TrialTimeline, Phase, Show, Stimulus, CollectResponse,
                            RecordState, UpdateState, UpdateAdaptive)
