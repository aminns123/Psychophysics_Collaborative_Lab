"""Read the experiment's own planning functions; no alternative scientific model."""
import sys
from pathlib import Path
from ..researcher import RunContext


class _ParameterReads(dict):
    def __init__(self, values, reads):
        super().__init__(values)
        self.reads = reads

    def __getitem__(self, key):
        self.reads.add(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.reads.add(key)
        return super().get(key, default)


class _PlanningContext(RunContext):
    """RunContext's actual parameter/adaptive machinery, with saving disabled."""
    def initialise(self, *, expected_trials, resolution, **kwargs):
        self.expected_trials = expected_trials
        self.resolution = resolution
        self.status = "running"

    def stimulus_parameters(self, slot="target", **overrides):
        values = super().stimulus_parameters(slot, **overrides)
        self.overrides.setdefault(slot, {}).update(overrides)
        return _ParameterReads(values, self.parameter_reads.setdefault(slot, set()))

    def _no_execution(self, *args, **kwargs):
        raise ValueError("This experiment needs execution to describe this value; inspect its Python procedure.")

    trial = record = save_resolution = save_primary = save_adaptive = _no_execution
    complete = complete_adaptive = _no_execution


def describe_settings(spec, values, snapshots, *, profile=None):
    """Describe a representative trial from loaded code, never a promised random trial.

    Older/custom procedures without planning functions keep their literal selected
    values in Review. They need no new authoring interface or registry entry.
    """
    result = {"stimuli": {slot: selected["document"]["parameters"] for slot, selected in snapshots.items()},
              "overrides": {}, "parameter_reads": {}, "conditions": [], "phases": [], "note": ""}
    if spec.procedure is None or spec.historical:
        result["note"] = "Historical driver: selected parameters are shown; inspect its Python/shader for trial-dependent values."
        return result
    module = sys.modules[spec.procedure.__module__]
    names = ("make_conditions", "initialise_experiment", "choose_condition", "prepare_stimuli", "make_trial")
    if not all(callable(getattr(module, name, None)) for name in names):
        result["note"] = "Selected parameters shown; this procedure supplies no separate trial-planning functions."
        return result
    run = _PlanningContext(values, profile, spec, Path(), synthetic=True, seed=0, stimulus_snapshots=snapshots)
    run.overrides, run.parameter_reads = {}, {}
    conditions = module.make_conditions(values)
    state = module.initialise_experiment(run, conditions)
    condition = module.choose_condition(run, conditions, state)
    stimuli = module.prepare_stimuli(run, condition, state)
    # Capture dependency reads before converting the returned mappings for display.
    reads = {slot: set(keys) for slot, keys in run.parameter_reads.items()}
    result.update(stimuli={slot: dict(p) for slot,p in stimuli.items()}, overrides=run.overrides,
                  parameter_reads=reads, conditions=conditions,
                  phases=module.make_trial(values, condition).resolve(values).to_dict()["phases"],
                  note="Trial-controlled values show one representative trial. Random choices and adaptive strengths vary during a run.")
    return result


def parameter_sources(description, slot):
    """An overridden parameter can still be an input (e.g. base orientation)."""
    overridden = set(description["overrides"].get(slot, {}))
    read_as_input = description["parameter_reads"].get(slot, set())
    return overridden - read_as_input


def review_rows(spec, values, snapshots, description, *, refresh_hz=None):
    """One visible table of the values that feed the selected procedure."""
    rows = [("Experiment", field.display_label, str(values[field.key]), "Experiment setting") for field in spec.fields]
    if spec.adaptive:
        rows.append(("Adaptive", "Algorithm", spec.adaptive.algorithm_id, "Selected by experiment Python"))
    if spec.response_paradigm:
        rows.append(("Responses", "Alternative order", ", ".join(spec.response_paradigm.alternatives), "Keys follow the same order"))
    for slot, selected in snapshots.items():
        identity = selected["document"]["stimulus_id"]
        rows.append((slot, "Stimulus", identity, selected["file_identity"]))
        from ..stimuli.registry import get_stimulus
        stimulus = get_stimulus(identity)
        effective = description["stimuli"].get(slot, selected["document"]["parameters"])
        for field in stimulus.parameters:
            source = "Selected stimulus parameter"
            if field.key in description["overrides"].get(slot, {}):
                source = "Experiment-controlled; sample" if field.key in parameter_sources(description, slot) else "Base parameter used by experiment; sample"
            rows.append((slot, field.display_label, str(effective[field.key]), source))
    if description["conditions"]:
        rows.append(("Conditions", "Number of condition/staircase entries",str(len(description["conditions"])),"Experiment's make_conditions"))
        keys = dict.fromkeys(key for c in description["conditions"] for key in c if key not in {"id","repeat"})
        for key in keys:
            distinct = list(dict.fromkeys(str(c[key]) for c in description["conditions"] if key in c))
            rows.append(("Conditions",key,", ".join(distinct),"All configured values; repeats shown above"))
    for phase in description["phases"]:
        rows.append(("Trial",phase["name"]+" duration",str(phase["duration_ms"]),
                     "ms; self-paced response" if phase["kind"]=="response" and phase["duration_ms"]==0 else "ms"))
        if phase["kind"] == "show" and refresh_hz is not None:
            from ..core.presentation import presentation_frames
            frames = presentation_frames(phase["duration_ms"],refresh_hz)
            rows.append(("Trial",phase["name"]+" planned display",f"{frames} frames / {frames*1000/refresh_hz:.6g} ms",
                         f"At {refresh_hz:g} Hz; not measured photon timing"))
        if phase.get("slot"):
            rows.append(("Trial",phase["name"]+" stimulus",phase["slot"],"Selected slot"))
        for placement in phase.get("stimuli",[]):
            rows.append(("Trial",phase["name"]+" / "+placement["slot"],
                         f"x={placement['x_deg']}, y={placement['y_deg']}","degrees from fixation"))
        if phase.get("beep"):
            rows.append(("Audio",phase["name"],str(phase["beep"]),phase["beep_trigger"]))
    return rows
