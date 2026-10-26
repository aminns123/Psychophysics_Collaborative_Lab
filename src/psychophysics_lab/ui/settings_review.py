"""Read the experiment's own planning functions; no alternative scientific model."""
import json
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
    """RunContext's real parameter/adaptive machinery, with saving disabled.

    RunContext is a dataclass without its own __post_init__ at decoration time.
    Its generated __init__ therefore does not call a subclass __post_init__.
    Initialise the read-tracking members explicitly, including for direct
    construction by auditors and scientist-facing planning tools.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overrides = {}
        self.parameter_reads = {}
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
              "overrides": {}, "parameter_reads": {}, "conditions": [], "phases": [], "resolution": {}, "note": ""}
    if spec.procedure is None or spec.historical:
        result["note"] = "Historical driver: selected parameters are shown; inspect its Python/shader for trial-dependent values."
        return result
    module = sys.modules[spec.procedure.__module__]
    names = ("make_conditions", "initialise_experiment", "choose_condition", "prepare_stimuli", "make_trial")
    if not all(callable(getattr(module, name, None)) for name in names):
        result["note"] = "Selected parameters shown; this procedure supplies no separate trial-planning functions."
        return result
    run = _PlanningContext(values, profile, spec, Path(), synthetic=True, seed=0, stimulus_snapshots=snapshots)
    if spec.id == "contrast_sensitivity" and values.get("contrast_method") == "constant_stimuli":
        # Review must inspect the selected fixed-level schedule, not invent a
        # staircase just because this CSF experiment supports adaptive trials.
        schedule = module.make_fixed_schedule(values, run.seed)
        frequencies = list(dict.fromkeys(row["frequency_cpd"] for row in schedule))
        conditions = [{"id": i, "frequency_cpd": frequency}
                      for i, frequency in enumerate(frequencies, 1)]
        condition = schedule[0]
        state = {}
        run.initialise(expected_trials=len(schedule),
                       resolution={"trial_selection_method": "constant_stimuli",
                                   "planned_trials": len(schedule),
                                   "fixed_contrast_levels": list(module.fixed_contrast_levels(values)),
                                   "fixed_repetitions_per_level_per_condition": values["fixed_repetitions"]})
        representative_note = ("Constant stimuli: condition is spatial frequency; "
                               f"{len(schedule)} planned presentations at the selected fixed levels. "
                               "This is one seeded sample; no adaptive staircase or threshold estimate.")
    else:
        conditions = module.make_conditions(values)
        state = module.initialise_experiment(run, conditions)
        condition = module.choose_condition(run, conditions, state)
        representative_note = ("Trial-controlled values show one representative trial. "
                               "Random choices and adaptive strengths vary during a run.")
    stimuli = module.prepare_stimuli(run, condition, state)
    # Capture dependency reads before converting the returned mappings for display.
    reads = {slot: set(keys) for slot, keys in run.parameter_reads.items()}
    timeline=module.make_trial(values, condition)
    result.update(stimuli={slot: dict(p) for slot,p in stimuli.items()}, overrides=run.overrides,
                  parameter_reads=reads, conditions=conditions, resolution=getattr(run, "resolution", {}),
                  phases=timeline.resolve(values).to_dict()["phases"],
                  phase_inputs={phase.name:phase.duration_ms for phase in timeline.phases if phase.kind in {"show","response"}},
                  note=representative_note)
    if profile is not None and getattr(profile, "expected_resolution_px", None):
        from ..core.presentation import plan_visible_stimulus
        from ..stimuli.registry import get_stimulus
        result["viewport"] = []
        for phase in timeline.resolve(values).phases:
            for placement in getattr(phase, "placements", ()):
                selected = snapshots[placement.slot]["document"]
                geometry, _, _ = plan_visible_stimulus(profile, profile.expected_resolution_px,
                    get_stimulus(selected["stimulus_id"]), stimuli[placement.slot], placement)
                result["viewport"].append(geometry | {"phase": phase.name})
        clipped = [view for view in result["viewport"] if view["clipped"]]
        if clipped:
            result["note"] += " WARNING: viewport clipping in this sample trial: " + "; ".join(
                view["phase"] + "/" + view["slot"] + " (" + ", ".join(view["clipped_edges"]) + ")"
                for view in clipped) + ". Requested geometry is retained, not fitted to the monitor. Review whether this is appropriate for the protocol."
    return result


def parameter_sources(description, slot):
    """An overridden parameter can still be an input (e.g. base orientation)."""
    overridden = set(description["overrides"].get(slot, {}))
    read_as_input = description["parameter_reads"].get(slot, set())
    return overridden - read_as_input


def review_rows(spec, values, snapshots, description, *, refresh_hz=None):
    """One visible table of the values that feed the selected procedure."""
    saved = spec.settings_snapshot()
    defaults = saved["values"] if saved else {f.key: f.default for f in spec.fields}
    def origin(field):
        base = (saved["file_identity"] if saved and field.key in saved["document"]["values"] else "Python ConfigField default")
        return f"Selected value (TUI/saved setup); {base} = {defaults[field.key]!r}"
    controls = set(spec.adaptive.controls) if spec.adaptive else set()
    rows = [("Experiment", field.display_label, str(values[field.key]), origin(field))
            for field in spec.fields if field.key not in controls]
    # Input settings have one authoritative, editable row. Derived contrast
    # summaries must not duplicate the same selected intensity or staircase rule.
    field_keys = {field.key for field in spec.fields}
    rows.extend(row for row in probe_intensity_rows(
        spec, values, conditions=description.get("conditions")
    ) if not (
        (row[:2] == ("Intensity", "Starting probe intensity")
         and "starting_probe_intensity" in field_keys)
        or (row[:2] == ("Intensity", "Background intensity")
            and "background_intensity" in field_keys)
        or (row[:2] == ("Adaptive scale", "Response rule")
            and {"n_down", "n_up"} <= field_keys)
    ))
    if spec.adaptive:
        rows.append(("Adaptive", "Algorithm", spec.adaptive.algorithm_id, "Selected by experiment Python"))
        rows.extend(("Adaptive", field.display_label, str(values[field.key]), origin(field))
                    for field in spec.fields if field.key in controls)
        if spec.adaptive.step_parameterization:
            rows.append(("Adaptive", "Step units / parameterization", spec.adaptive.step_parameterization,
                         "Declared by experiment Python"))
        if spec.adaptive.step_calculator:
            rows.append(("Adaptive", "Optional step calculator", spec.adaptive.step_calculator,
                         "Available calculator; selected step values above are used"))
    if spec.response_paradigm:
        rows.append(("Responses", "Alternative order", ", ".join(spec.response_paradigm.alternatives), "Keys follow the same order"))
    for slot, selected in snapshots.items():
        identity = selected["document"]["stimulus_id"]
        rows.append((slot, "Stimulus", identity, selected["file_identity"]))
        from ..stimuli.registry import get_stimulus
        stimulus = get_stimulus(identity)
        effective = description["stimuli"].get(slot, selected["document"]["parameters"])
        for field in stimulus.parameters:
            source = f"Selected stimulus: {selected['file_identity']} (Python defaults fill missing keys)"
            if field.key in description["overrides"].get(slot, {}):
                source = "Experiment-controlled; sample" if field.key in parameter_sources(description, slot) else "Base parameter used by experiment; sample"
            rows.append((slot, field.display_label, str(effective[field.key]), source))
    from ..core.viewport import stimulus_geometry
    for slot, selected in snapshots.items():
        stimulus = get_stimulus(selected["document"]["stimulus_id"])
        geometry = stimulus_geometry(stimulus, description["stimuli"].get(slot, selected["document"]["parameters"]))
        labels = {"support_radius_deg": "Outer support radius (degrees)",
                  "support_diameter_deg": "Outer support diameter (degrees)",
                  "taper_start_radius_deg": "Smooth fade starts at radius (degrees)",
                  "raster_extent_deg": "Effective raster extent (degrees)",
                  "background_outside_support": "Digital background outside support"}
        for key, label in labels.items():
            if key in geometry:
                rows.append(("Stimulus geometry", slot + " / " + label, str(geometry[key]),
                             "Derived from stimulus definition; display clipping does not rescale this geometry"))
    for view in description.get("viewport", ()):
        rows.append(("Viewport", view["phase"] + " / " + view["slot"],
                     str(view["origin_px"]) + " + " + str(view["raster_px"]) + " pixels",
                     "Clipped: " + ", ".join(view["clipped_edges"]) if view["clipped"] else "Entire requested raster visible"))
    if description["conditions"]:
        rows.append(("Conditions", "Number of condition/staircase entries",str(len(description["conditions"])),"Experiment's make_conditions"))
        keys = dict.fromkeys(key for c in description["conditions"] for key in c if key not in {"id","repeat"})
        for key in keys:
            distinct = list(dict.fromkeys(str(c[key]) for c in description["conditions"] if key in c))
            rows.append(("Conditions",key,", ".join(distinct),"All configured values; repeats shown above"))
    for phase in description["phases"]:
        if phase["kind"] not in {"show", "response"}:
            labels = {"record_state": "Record state", "update_state": "Update state",
                      "update_adaptive": "Update staircase"}
            detail = ", ".join(phase.get("fields", ())) or phase.get("function", "")
            rows.append(("Trial action", phase["name"], labels.get(phase["kind"], phase["kind"]),
                         "Nonvisual action" + (": " + detail if detail else "")))
            continue
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
    # Display *additional* planning metadata, but do not show a second copy of
    # settings already available as editable ConfigFields above. Compare with the
    # ACTUAL resolved output: if an experiment transforms/overrides a value, show
    # that meaningful difference explicitly rather than silently suppressing it.
    plan_equivalents = {
        "adaptive_rule / n_down": "n_down",
        "adaptive_rule / n_up": "n_up",
        "adaptive_rule / log_up": "logUNIT_UP",
        "adaptive_rule / log_down": "logUNIT_DW",
        "adaptive_rule / reversal_limit": "reversal_termination",
        "adaptive_rule / initial_one_down_limit": "initial_one_down_limit",
        "adaptive_rule / max_trials": "max_trials",
        "threshold_reversals": "threshold_reversals",
        "staircases_per_condition": "staircases_per_condition",
        "background_digital_intensity": "background_intensity",
        "gaussian_sigma_deg": "grating_sigma_deg",
        "grating_cutoff_sigmas": "grating_cutoff_sigmas",
        "target_offset_deg": "grating_offset_deg",
    }
    def plan_rows(mapping, prefix=""):
        for key, value in mapping.items():
            label = f"{prefix} / {key}" if prefix else str(key)
            if isinstance(value, dict):
                yield from plan_rows(value, label)
                continue
            selected_key = plan_equivalents.get(label)
            if selected_key in field_keys and value == values[selected_key]:
                continue
            if label == "adaptive_rule / algorithm" and spec.adaptive and value == spec.adaptive.algorithm_id:
                continue
            rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
            # The authoritative primary_estimator describes analysis of
            # *recorded human or simulated* responses, not a simulation-only
            # setting and not a second threshold algorithm invented by Review.
            # Keep its reported values and provenance distinct from editable
            # adaptive step rules and experiment trial timing.
            if label.startswith("primary_estimator / "):
                key = label.removeprefix("primary_estimator / ")
                readable = {
                    "within_staircase": "Within-staircase method",
                    "across_staircases": "Across-staircase method",
                    "retained_reversals": "Retained reversals",
                    "value_column": "Recorded strength column",
                    "completion": "Completion requirement",
                    "units": "Strength units",
                }.get(key, key.replace("_", " "))
                yield ("Threshold estimation", readable, rendered,
                       "Resolved by the experiment's primary_rule; analysis after acquisition")
            elif selected_key in field_keys:
                yield ("Run plan", "Effective " + label, rendered,
                       "Resolved by experiment; differs from selected " + selected_key)
            else:
                yield ("Run plan", label, rendered, "Resolved by experiment initialise_experiment")
    rows.extend(plan_rows(description.get("resolution", {})))
    return rows


def probe_intensity_rows(spec, values, *, conditions=None):
    """Explain declared bright-probe log steps in digital units, not photometry.

    Read the experiment's own maximum and shared update arithmetic. No separate
    scientific bounds, adaptation rule or participant-response prediction.
    """
    if not ("starting_probe_intensity" in values and "background_intensity" in values
            and spec.migrate_values is not None):
        return []
    import math
    from ..adaptive.steps import bounded_log_step
    background = float(values["background_intensity"])
    intensity = float(values["starting_probe_intensity"])
    down, up = float(values["logUNIT_DW"]), float(values["logUNIT_UP"])
    if (not all(math.isfinite(x) for x in (background, intensity, down, up))
            or not 0 <= background < 1 or not background <= intensity <= 1
            or down <= 0 or up <= 0):
        raise ValueError("Use finite 0..1 intensities (probe at or above background, background below 1) and positive log steps.")
    difference = intensity - background
    module = sys.modules[spec.procedure.__module__]
    try:
        # Some study conditions are still incomplete while typing. The shared
        # minimum condition fields can nevertheless resolve the exact ceiling.
        conditions = conditions or module.make_conditions(values)
        bounds = [module.maximum_contrast(values, condition) for condition in conditions]
    except (ValueError, TypeError, KeyError):
        bounds = []
    digital_note = "Digital commands; not measured luminance or optical contrast"
    rows = [("Intensity", "Starting probe intensity", f"{intensity:.10g}", "0 black; 1 white; before additive overlaps/subpixel coverage"),
            ("Intensity", "Background intensity", f"{background:.10g}", digital_note),
            ("Contrast", "Starting difference from background", f"{difference:.10g}", "probe intensity minus background; adaptive/recorded strength"),
            ("Contrast", "Relative digital contrast", f"{difference/background:.10g}" if background else "undefined at black background", "(probe-background)/background; not luminance Weber contrast")]
    if bounds:
        rows.append(("Intensity", "Maximum nominal probe intensity", ", ".join(f"{background+b:.10g}" for b in sorted(set(bounds))), "Experiment's additive headroom; outward updates hold at the ceiling"))
        if any(b <= 0 or difference > b for b in bounds):
            rows.append(("Intensity", "Starting intensity check", "Outside at least one condition's headroom", "Review settings; no value was clipped"))
            return rows
        maximum = min(bounds)
    else:
        rows.append(("Intensity", "Maximum nominal probe intensity", "Resolve study conditions first", "The experiment defines condition-specific headroom"))
        return rows
    next_down = bounded_log_step(difference, -down, maximum=maximum)
    next_up = bounded_log_step(difference, up, maximum=maximum)
    rows.extend([
        ("Adaptive scale", "After one decrease", f"intensity {background+next_down:.10g}; difference {next_down:.10g}", f"Multiply difference by 10^(-{down:g}); not subtraction from intensity"),
        ("Adaptive scale", "After one increase", f"intensity {background+next_up:.10g}; difference {next_up:.10g}", f"Multiply difference by 10^({up:g}); capped at condition ceiling"),
        ("Adaptive scale", "Exact background", "Already at background" if difference == 0 else "No finite number of log decreases", "Ideal log rule; a positive numeric floor is retained. Rendering precision may merge levels earlier.")])
    if difference > 0:
        for fraction, label in ((.1, "10%"), (.01, "1%"), (.001, "0.1%")):
            count = math.ceil(-math.log10(fraction)/down)
            remaining = bounded_log_step(difference, -count*down, maximum=maximum)
            rows.append(("Adaptive scale", f"Decreases to <= {label} of starting difference", str(count),
                         f"Adaptive decrease updates, not trials; intensity {background+remaining:.10g}, difference {remaining:.10g}"))
    rows.append(("Adaptive scale", "Response rule", f"{values['n_down']}-down / {values['n_up']}-up; initial one-down limit {values['initial_one_down_limit']}",
                 "Decrease counts are updates; actual trial count depends on response history"))
    return rows
