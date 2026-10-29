"""Small public API for stimulus authors and experiment procedures.

A procedure receives RunContext: validated values, display profile, adaptive
factory, response paradigm and canonical recorder. It owns presentation,
accepted responses and scientific completion. No framework file paths required.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Any
from .adaptive import AdaptiveSelection, AdaptiveAlgorithm, StaircaseConfig, Step, get_algorithm
from psychophysics_lab.experiments._internal.spec import ConfigField, ExperimentSpec
from psychophysics_lab.experiments._internal.responses import ResponseParadigm, LEFT_RIGHT, TWO_INTERVAL
from .stimuli.registry import StimulusSpec
from .data.trials import TrialLog
from .data.session import atomic_write_json, append_json_record
from .config.models import ResearcherOverride


def experiment(*, id, name, description, procedure, fields=(), adaptive=None,
               responses=None, source_paths=(), validator=None, monitor_validator=None,
               calibration_requirements=(), calibration_not_applicable="", monitor_capabilities=None,
               stimulus_slots=None, stimulus_defaults=None, supports_simulation=False, default_config="",
               acquisition_block_reason="", historical=False, scientific_spec=None,
               trial_column_overrides=None, migrate_values=None, data_directory_name="",
               method_planner=None, method_reviewer=None, stimulus_parameter_controls=None,
               session_start=(), stimulus_field_bindings=None):
    """Build a registered experiment without the historical four-file adapter."""
    if responses is not None and "response_keys" not in {item.key for item in fields}:
        fields = tuple(fields) + (ConfigField("response_keys", "Response keys (in alternative order: " + ", ".join(responses.alternatives) + ")", "text", default=",".join(responses.keys), section="Response mapping", help_text='Keys assigned in the displayed response-alternative order. Changing a key changes input mapping, not which alternative is scientifically correct.'),)
    dictionary = {}
    if responses is not None:
        encoding = "; ".join(f"{i} = {meaning}" for i, meaning in enumerate(responses.alternatives))
        dictionary = {column: {"units_or_encoding": encoding}
                      for column in ("target_alternative", "participant_response")}
    for column, overrides in (trial_column_overrides or {}).items():
        dictionary.setdefault(column, {}).update(overrides)
    return ExperimentSpec(id=id, display_name=name, description=description,
        legacy_module=procedure.__module__, legacy_experiment_type=id,
        fields=tuple(fields), procedure=procedure, adaptive=adaptive, data_directory_name=data_directory_name,
        response_paradigm=responses, source_paths=tuple(source_paths),
        configure_module="psychophysics_lab.researcher", configure_function="configure",
        validator=validator, monitor_validator=monitor_validator, migrate_values=migrate_values,
        calibration_requirements=tuple(calibration_requirements),
        calibration_not_applicable=calibration_not_applicable,
        monitor_capabilities=monitor_capabilities,
        stimulus_slots=stimulus_slots or {}, stimulus_defaults=stimulus_defaults or {}, supports_simulation=supports_simulation, default_config=default_config,
        acquisition_block_reason=acquisition_block_reason, historical=historical, scientific_spec=scientific_spec or {},
        trial_column_overrides=dictionary, method_planner=method_planner,
        method_reviewer=method_reviewer, stimulus_parameter_controls=stimulus_parameter_controls or {},
        session_start=session_start, stimulus_field_bindings=stimulus_field_bindings or {})


class ParticipantAbort(Exception):
    """Raised by RunContext.abort; the runner preserves an aborted run."""


def check_acquisition_qualification(run, spec):
    """Apply the same protocol decision at procedure and presenter entry."""
    if getattr(run, "synthetic", False) or not spec.acquisition_block_reason:
        return
    record = getattr(run, "researcher_override", None)
    data_kind = getattr(run, "data_kind", "human")
    protocol_override = (
        data_kind == "human"
        and isinstance(record, ResearcherOverride)
        and record.experiment_id == spec.id
        and "protocol" in record.waived_requirements
    )
    if not protocol_override and (data_kind != "uncalibrated_presentation_test" or spec.historical):
        raise ValueError(spec.acquisition_block_reason)


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
    observer_probability: Any = None
    test_trial_limit: int | None = None
    virtual_presentation: Any = None  # explicit development replay backend; never used for humans
    researcher_override: ResearcherOverride | None = None
    show_response_instructions: bool = True
    status: str = field(default="created", init=False)
    accepted_trials: int = field(default=0, init=False)
    expected_trials: int = field(default=0, init=False)

    def initialise(self, *, expected_trials: int, resolution: Mapping, runtime_display=None, background_intensity=.5):
        """Initialise normally, then run an optional once-only opening before trials.

        Readiness has its own provenance; it cannot create a scientific answer,
        choose a condition, draw observer randomness or update a staircase.
        """
        if not self.spec.session_start.phases:
            return self._initialise(expected_trials=expected_trials, resolution=resolution,
                                    runtime_display=runtime_display, background_intensity=background_intensity)
        # The established acquisition/argument guards precede even session
        # parameter resolution, including direct Python procedure calls.
        self._validate_initialisation(expected_trials, resolution, background_intensity)
        if self.status != "created" or getattr(self, "_session_started", False):
            raise ValueError("Initialise and execute session start exactly once.")
        from datetime import datetime, timezone
        import time
        from .core.timeline import scientific_snapshot
        from .core.trial_execution import VirtualPresentation, execute_timeline
        # Resolve everything before opening a physical output device.
        sequence = self.spec.session_start.resolve(self.values).validate_slots(self.stimulus_snapshots)
        resolved = {}
        for phase in sequence.phases:
            for placement in phase.placements:
                if placement.slot not in resolved:
                    selected = self.stimulus_snapshots[placement.slot]["document"]
                    resolved[placement.slot] = (selected["stimulus_id"], self.stimulus_parameters(placement.slot))
        trace = {"schema_version": 1, "sequence": "session_start", "status": "started",
                 "declared_plan": self.spec.session_start.to_dict(), "plan": sequence.to_dict(),
                 "resolved_stimuli": scientific_snapshot({slot: {"stimulus_id": identity, "parameters": params}
                                                         for slot, (identity, params) in resolved.items()}),
                 "data_kind": self.data_kind, "synthetic": self.synthetic,
                 "photon_timing_verified": False, "events": [],
                 "started_utc": datetime.now(timezone.utc).isoformat(),
                 "software_started_s": time.perf_counter()}
        self._session_started = True
        self._session_trace = trace
        path = self.run_directory / "session_events.json"
        atomic_write_json(path, trace)
        error = None
        self._session_pending = True
        try:
            self._initialise(expected_trials=expected_trials, resolution=resolution,
                             runtime_display=runtime_display, background_intensity=background_intensity)
            backend = (self.virtual_presentation or VirtualPresentation()) if self.synthetic else self._presentation
            backend.prepare(sequence, resolved)
            def verify(event, response, observed):
                if response is not None:
                    raise ValueError("Session events cannot yield scientific responses.")
                if event.kind == "key_wait":
                    import math
                    ready = observed.get("readiness", {})
                    elapsed = ready.get("elapsed_s")
                    if (ready.get("key") != event.key or type(elapsed) not in (int, float)
                            or not math.isfinite(elapsed) or elapsed < 0):
                        raise ValueError("Readiness requires the declared key and a finite nonnegative elapsed time.")
            execute_timeline(sequence, backend, trace["events"], verify, software_timestamps=True)
            trace["status"] = "completed"
        except BaseException as exc:
            error = exc
            trace["status"] = "aborted" if isinstance(exc, ParticipantAbort) else "error"
            trace["error"] = str(exc)
            self.status = "aborted_by_user" if isinstance(exc, ParticipantAbort) else "error"
            raise
        finally:
            self._session_pending = False
            trace["software_finished_s"] = time.perf_counter()
            self._persist_independently([("session event journal", lambda: atomic_write_json(path, trace))],
                                        original_error=error)

    def _validate_initialisation(self, expected_trials, resolution, background_intensity):
        """Retain the same guards before opening a display or resolving an opening."""
        check_acquisition_qualification(self, self.spec)
        if self.status != "created" or type(expected_trials) is not int or expected_trials < 1:
            raise ValueError("Initialise once with a positive expected_trials count.")
        if not resolution:
            raise ValueError("Provide resolved stimulus and task information.")
        import math
        if type(background_intensity) not in (int, float) or not math.isfinite(background_intensity) or not 0 <= background_intensity <= 1:
            raise ValueError("Background must be a finite digital command in [0, 1].")

    def _initialise(self, *, expected_trials: int, resolution: Mapping, runtime_display=None, background_intensity=.5):
        """Declare the planned response count and resolved scientific settings."""
        self._validate_initialisation(expected_trials, resolution, background_intensity)
        if not self.synthetic and not runtime_display:
            if not self.spec.stimulus_slots:
                raise ValueError("Human presentation must record the actual runtime_display.")
            from .core.presentation import Presentation
            # Existing display construction is unchanged unless instructions
            # are explicitly hidden by the researcher at final Review.
            options = {} if background_intensity == .5 else {"background_intensity": background_intensity}
            if not self.show_response_instructions:
                options["show_response_instructions"] = False
            self._presentation = Presentation(self.display, self.responses, **options)
            runtime_display = self._presentation.metadata
        self.expected_trials = expected_trials
        settings = self.spec.settings_snapshot()
        self._experiment_settings = settings
        self.save_resolution(**({"scientific_specification":dict(self.spec.scientific_spec), "random_seed":self.seed} | dict(resolution) | ({"experiment_settings": settings} if settings else {})))
        atomic_write_json(self.run_directory / "runtime_display.json", dict(runtime_display or {
            "physical_display_used": False, "mode": "simulation",
            "monitor_profile_id": self.display.id, "background_digital_intensity": background_intensity,
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

    def complete_adaptive(self, algorithm):
        """Finish a declared response ceiling only when the owned algorithm stops.

        Keep the original ceiling in lifecycle metadata; never pad missing
        responses when every staircase has completed early.
        """
        if (self.status != "running" or
                not any(algorithm is item for item in getattr(self, "_algorithms", ())) or
                algorithm.status not in {"completed", "max_trials_reached"} or
                algorithm.max_trials != self.expected_trials or
                algorithm.total_trials != self.accepted_trials or self.accepted_trials < 1):
            raise ValueError("Adaptive completion requires an owned, stopped algorithm and all accepted responses")
        ceiling = self.expected_trials
        self.expected_trials = self.accepted_trials
        self.complete()
        self.status = algorithm.status
        atomic_write_json(self.run_directory / "procedure_lifecycle.json", {
            "schema_version": 1, "status": self.status, "expected_trials": self.expected_trials,
            "accepted_trials": self.accepted_trials, "response_ceiling": ceiling,
            "adaptive_stop_status": algorithm.status, "reason": "Adaptive stopping rule",
        })

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

    def trial(self, timeline, **kwargs):
        """Present once, yield accepted input for explicit interpretation/update, then save.

        Use as a context manager. Scientific updates belong inside the context;
        accepted input and partial state survive exceptions. No writes occur
        between the first displayed phase and the final scientific update.
        """
        return self._trial_session(timeline, _staged=True, **kwargs)

    def play_trial(self, timeline, **kwargs):
        """Compatibility: execute a complete action plan at one trial boundary."""
        with self._trial_session(timeline, **kwargs) as trial:
            correct = trial.response["correct"]
        return correct

    @contextmanager
    def _trial_session(self, timeline, *, target, condition, parameters_by_slot=None,
                   instructions="", measurements=None, state=None, record_from_state=None, adaptive_record=None, adaptive_value_column="next_screen_intensity", _staged=False):
        """Execute chronological scientific actions and persist at the trial boundary.

        Callbacks get immutable detached state and response, and return finite JSON
        state. They are trusted scientific functions: do not render or perform IO.
        A valid response is saved even if a later action fails. Partial events and
        state are saved on abort/error; no response is invented before collection.
        """
        import random
        from .core.timeline import (TrialTimeline, Phase, RecordState, UpdateState,
                                    UpdateAdaptive, scientific_snapshot, immutable_state)
        from .core.trial_execution import VirtualPresentation, ScientificTrial, execute_timeline, execute_actions
        from .core.presentation import Response
        from .stimuli.registry import get_stimulus
        if (self.data_kind == "uncalibrated_presentation_test" and self.test_trial_limit is not None
                and self.accepted_trials >= self.test_trial_limit):
            from .core.presentation_testing import PresentationTestComplete
            raise PresentationTestComplete("Test response limit reached; study stopping rules were not changed.")
        if getattr(self, "_in_trial", False):
            raise ValueError("Finish the active trial before starting another.")
        if getattr(self, "_session_pending", False):
            raise ValueError("Finish session start before starting a scientific trial.")
        if adaptive_value_column not in {"next_screen_intensity", "next_display_contrast"}:
            raise ValueError("Declare the canonical column holding the adaptive numeric value.")
        if adaptive_record is not None and not any(adaptive_record is a for a in getattr(self, "_algorithms", ())):
            raise ValueError("Adaptive recording requires an owned algorithm")
        from .core.timeline import as_trial_timeline
        timeline = as_trial_timeline(timeline)
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Start a timeline only while a response is expected.")
        if _staged and any(isinstance(p, (UpdateState, UpdateAdaptive)) for p in timeline.phases):
            raise ValueError("Staged trial presentation cannot contain scientific updates; call update_experiment explicitly.")
        if adaptive_record is not None and not _staged and not any(
                isinstance(p, UpdateAdaptive) and p.algorithm is adaptive_record for p in timeline.phases):
            raise ValueError("Adaptive recording requires this trial's UpdateAdaptive action")
        timeline = timeline.resolve(self.values).validate_slots(self.stimulus_snapshots)
        self.responses.correct(target, target)
        observations = scientific_snapshot(dict(measurements or {}))
        for key, value in observations.items():
            if not key.isidentifier() or type(value) not in (int, float, str, bool):
                raise ValueError("Custom measurements require identifier keys and finite scalar values.")
        current = scientific_snapshot(dict(state if state is not None else self.trial_state))
        from .data.trials import TRIAL_COLUMNS
        projection = dict(record_from_state or {})
        owned = {"trial_index", "recorded_utc", "event_time_s", "stimulus_condition",
                 "target_alternative", "participant_response", "response_key", "correct", "run_status"}
        if set(projection) - (set(TRIAL_COLUMNS) - owned) or any(
                not isinstance(key, str) or key not in current for key in projection.values()):
            raise ValueError("Canonical projection requires declared scalar state fields and non-engine-owned columns")
        if any(current[key] is not None and type(current[key]) not in (str, int, float, bool)
               for key in projection.values()):
            raise ValueError("Canonical projection values must be scalar")
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
                import math
                if (response.key != self.responses.keys[response.alternative] or
                        type(response.reaction_time_s) not in (int, float) or
                        not math.isfinite(response.reaction_time_s) or response.reaction_time_s < 0):
                    raise ValueError("Response key, alternative and finite nonnegative reaction time must agree.")
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

        session = None
        trial_error = None
        first_update = len(getattr(self, "_adaptive_history", ()))
        def append_actions(actions):
            if response_data is None:
                raise ValueError("Scientific updates require an accepted response.")
            if any(not isinstance(p, (RecordState, UpdateState, UpdateAdaptive)) for p in actions):
                raise ValueError("Only nonvisual actions may follow response collection.")
            planned = trace["plan"]["phases"]
            names = [p["name"] for p in planned] + [p.name for p in actions]
            if len(names) != len(set(names)):
                raise ValueError("Each phase name within one trial must be unique.")
            for p in actions:
                if isinstance(p, UpdateAdaptive) and not any(p.algorithm is a for a in getattr(self, "_algorithms", ())):
                    raise ValueError("UpdateAdaptive requires an algorithm created with run.adaptive().")
            planned.extend(p.to_dict() for p in actions)
            execute_actions(actions, backend, events, apply, start_index=len(events))

        self._in_trial = True
        try:
            if self.synthetic:
                if not hasattr(self, "_rng"):
                    self._rng = random.Random(f"{self.seed}:observer") if self.observer_probability is not None else random.Random(self.seed)
                probability = (float(self.observer_probability(condition,immutable_state(current),trace["resolved_stimuli"]))
                    if self.observer_probability is not None else float(self.observer_parameters.get("accuracy", .85)))
                if not 0<=probability<=1:
                    raise ValueError("Observer probability must lie in [0,1].")
                alternative = target if self._rng.random() < probability else self._rng.choice(
                    [i for i in range(len(self.responses.keys)) if i != target])
                backend = self.virtual_presentation or VirtualPresentation(Response(alternative, self.responses.keys[alternative],
                                                       .25 + .25 * self._rng.random()))
            else:
                backend = self._presentation
            trace["presentation_basis"] = getattr(backend, "basis", "software presentation; physical timing unverified")
            backend.prepare(timeline, resolved)
            execute_timeline(timeline, backend, events, apply, instructions=instructions)
            session = ScientificTrial(lambda: immutable_state(response_data),
                                      lambda: immutable_state(current), append_actions)
            yield session
            if adaptive_record is not None and not any(
                    e["kind"] == "update_adaptive" and e.get("status") == "completed" for e in events):
                raise ValueError("Adaptive recording requires this trial's completed adaptive update.")
            trace["status"] = "completed"
        except BaseException as exc:
            trial_error = exc
            trace["status"] = "aborted" if isinstance(exc, ParticipantAbort) else "error"
            trace["error"] = str(exc)
            raise
        finally:
            if session is not None:
                session.close()
            self._in_trial = False
            self._trial_state = scientific_snapshot(current)
            trace["final_state"] = scientific_snapshot(current)
            # No IO during presentation/update. The canonical answer and journal
            # are independent writes: failure of either must not suppress the other.
            if not hasattr(self, "_action_trials"):
                self._action_trials = []
            self._action_trials.append(deepcopy(trace))
            operations = []
            presentation = None
            if accepted_response is not None:
                # Preserve an accepted response even if later scientific state
                # is incomplete: missing/non-scalar values remain unknown.
                projected = {column: current.get(key) if current.get(key) is None or
                             type(current.get(key)) in (str, int, float, bool) else None
                             for column, key in projection.items()}
                operations.append(("canonical response", lambda: self.record(stimulus_condition=condition, target_alternative=target,
                            participant_response=accepted_response.alternative,
                            response_key=accepted_response.key, correct=int(correct), adaptive=adaptive_record, **projected)))
                if not hasattr(self, "_presentations"):
                    self._presentations = []
                presentation = {"trial_index": trial_index, "slot": response_slot,
                    "stimulus_id": resolved[response_slot][0], "parameters": resolved[response_slot][1],
                    "reaction_time_s": accepted_response.reaction_time_s,
                    "phase_events": [e for e in events if e["kind"] in {"show", "response"}],
                    "measurements": observations,
                    "timing_basis": response_data["timing_basis"]}
                self._presentations.append(deepcopy(presentation))
            operations.append(("trial journal", lambda: append_json_record(
                self.run_directory / "trial_events.jsonl",
                {"schema_version": 1, "trial": trace, "presentation": presentation,
                 "adaptive_updates": getattr(self, "_adaptive_history", [])[first_update:]})))
            if _staged and adaptive_record is not None:
                operations.append(("adaptive snapshot", lambda: self.save_adaptive(
                    adaptive_record, value_column=adaptive_value_column)))
            self._persist_independently(operations, original_error=trial_error)

    def _persist_independently(self, operations, *, original_error=None):
        """Attempt every essential write and retain the first scientific error."""
        errors = []
        for name, operation in operations:
            try:
                operation()
            except BaseException as exc:
                errors.append((name, exc))
        if not errors:
            return
        if not hasattr(self, "_persistence_errors"):
            self._persistence_errors = []
        self._persistence_errors.extend({"operation": name, "error": repr(exc)} for name, exc in errors)
        primary = original_error if original_error is not None else errors[0][1]
        for name, exc in errors:
            primary.add_note(f"Persistence failed ({name}): {exc!r}")
        if original_error is None:
            raise primary

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
        # Per-trial journals are already durable. Write each compatible aggregate
        # once at finalisation, including on abort/error; never rewrite N trials
        # after every response. Always attempt display cleanup after save errors.
        operations = []
        if hasattr(self, "_session_trace"):
            # The first trial's flip can finish the last session display's
            # measured dwell. Preserve that existing presenter's observation.
            operations.append(("session event summary", lambda: atomic_write_json(
                self.run_directory / "session_events.json", self._session_trace)))
        if hasattr(self, "_action_trials"):
            operations.append(("action summary", lambda: atomic_write_json(
                self.run_directory / "trial_actions.json", {"schema_version": 1, "trials": self._action_trials})))
        if hasattr(self, "_presentations"):
            operations.append(("presentation summary", lambda: atomic_write_json(
                self.run_directory / "trial_presentations.json", {"schema_version": 1, "trials": self._presentations})))
        if hasattr(self, "_adaptive_history"):
            operations.append(("adaptive history", self._flush_adaptive_history))
        if hasattr(self, "_presentation"):
            operations.append(("display cleanup", self._presentation.close))
        self._persist_independently(operations)

    def adaptive(self, *args, **kwargs):
        if self.spec.adaptive is None:
            raise ValueError("This experiment has not declared an adaptive algorithm.")
        algorithm = get_algorithm(self.spec.adaptive.algorithm_id).factory(*args, **kwargs)
        if not hasattr(self, "_algorithms"):
            self._algorithms = []
        self._algorithms.append(algorithm)
        return algorithm

    def record(self, *, adaptive=None, **trial):
        """Append one accepted response using the documented canonical columns."""
        if self.status != "running" or self.accepted_trials >= self.expected_trials:
            raise ValueError("Record responses only in a running procedure within its planned trial count.")
        required = {"stimulus_condition", "target_alternative", "participant_response", "response_key", "correct"}
        if required - trial.keys():
            raise ValueError(f"Response is missing canonical fields: {sorted(required - trial.keys())}")
        trial["trial_index"] = self.accepted_trials + 1
        trial["run_status"] = "running"
        if adaptive is not None:
            if not any(adaptive is item for item in getattr(self, "_algorithms", ())):
                raise ValueError("Adaptive recording requires an owned algorithm")
            # An action may have failed before committing its adaptive update.
            # Keep that accepted response; the run's error metadata explains it.
            if adaptive.total_trials == self.accepted_trials + 1:
                trial["run_status"] = adaptive.status
        if self.synthetic:
            trial["response_key"] = "SIMULATED_" + str(trial.get("response_key", ""))
            from .core.synthetic import synthetic_recorded_utc
            trial.setdefault("event_time_s", float(self.accepted_trials + 1))
            trial["recorded_utc"] = synthetic_recorded_utc(trial["event_time_s"])
        TrialLog(self.run_directory / "trials.tsv").append(trial)
        self.accepted_trials += 1
        self._save_lifecycle()

    def save_adaptive(self, algorithm, *, value_column="next_screen_intensity"):
        if value_column not in {"next_screen_intensity", "next_display_contrast"}:
            raise ValueError("Declare the canonical column holding the adaptive numeric value.")
        snapshot = algorithm.snapshot()
        snapshot.setdefault("canonical_trial_log", "trials.tsv")
        if value_column != "next_screen_intensity":
            snapshot["canonical_value_column"] = value_column
        atomic_write_json(self.run_directory / "adaptive_session.json", snapshot)

    def adaptive_trial_record(self, algorithm, identity, *, contrast, maximum, log_up, log_down, measurements=None, instructions=""):
        """Record presented/next strength, repeat ID, reversal count and completion.

        Scientific strength, gamut, steps and extra measurements are supplied by
        the experiment. This projection does not choose an update or estimator.
        """
        return {
            "state":{"contrast":contrast,"maximum_contrast":maximum,"log_up":log_up,"log_down":log_down,
                "next_contrast":None,"staircase_id":identity,
                "staircase_trial_index":algorithm.states[identity].trial_count+1,
                "reversal":None,"reversal_count":None,"staircase_complete":None},
            "record_from_state":{"staircase_id":"staircase_id","staircase_trial_index":"staircase_trial_index",
                "presented_display_contrast":"contrast","next_display_contrast":"next_contrast",
                "reversal":"reversal","reversal_count":"reversal_count","staircase_complete":"staircase_complete"},
            "measurements":dict(measurements or {}),"instructions":instructions,
            "adaptive_record":algorithm,"adaptive_value_column":"next_display_contrast"}

    def staircase_record_action(self, algorithm, identity):
        """Record counters after the experiment's explicit adaptive update."""
        from .core.timeline import UpdateState
        previous = algorithm.states[identity].reversal_count
        def record_adjustment(values, answer):
            current = algorithm.states[identity]
            return dict(values) | {"reversal":int(current.reversal_count > previous),
                "reversal_count":current.reversal_count,"staircase_complete":int(current.complete)}
        return UpdateState(record_adjustment,name="record_staircase_change")

    def save_primary(self, rule, conditions):
        """Recompute the declared primary result from the canonical trial log."""
        import json
        from .analysis.primary import from_run
        expected = {}
        for condition in conditions:
            key = str(condition.get("value",condition.get("frequency_cpd")))
            expected.setdefault(key,[]).append(condition["id"])
        result = from_run(self.run_directory,rule,expected,self.status)
        atomic_write_json(self.run_directory/"primary_thresholds.json",result)
        existing_path = self.run_directory / "resolved_experiment.json"
        existing = json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.exists() else {}
        self.save_resolution(**(existing | {"scientific_specification":dict(self.spec.scientific_spec), "random_seed":self.seed} | result))
        return result

    def save_resolution(self, **details):
        """Record experiment-owned stimulus/timing definitions for later review."""
        # A final method summary must retain the source preset captured at
        # initialisation, even if the researcher selected different run values.
        if getattr(self, "_experiment_settings", None):
            details["experiment_settings"] = self._experiment_settings
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
from .core.timeline import (TrialTimeline, SessionTimeline, Phase, Show, Stimulus, CollectResponse, WaitForKey, legacy_trial_factory,
                            RecordState, UpdateState, UpdateAdaptive, Beep)
