"""Read the experiment's own planning functions; no alternative scientific model."""
import json
import sys
import inspect
from collections.abc import Mapping
from pathlib import Path
from ..researcher import RunContext


def _source_position(function):
    try:
        return {"path": inspect.getsourcefile(function), "line": inspect.getsourcelines(function)[1]}
    except (OSError, TypeError):
        return {}


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
    result["session_phases"] = spec.session_start.resolve(values).to_dict()["phases"]
    result["session_inputs"] = {event.name: {"duration": event.duration_ms, "key": event.key}
                                for event in spec.session_start.phases}
    if spec.procedure is None or spec.historical:
        result["note"] = "Historical driver: selected parameters are shown; inspect its Python/shader for trial-dependent values."
        return result
    module = sys.modules[spec.procedure.__module__]
    event_factory = getattr(module, "trial_events", None)
    event_name = "trial_events" if event_factory is not None else "make_trial"
    if event_factory is None:
        event_factory = getattr(module, "make_trial", None)
    names = ("prepare_stimuli",)
    method = values.get("contrast_method")
    reviewer = (spec.method_reviewer.get(method) if isinstance(spec.method_reviewer, Mapping)
                else spec.method_reviewer if method == "adaptive" else None)
    if not ((method == "constant_stimuli" and callable(spec.method_planner))
            or callable(reviewer)):
        names += ("make_conditions", "initialise_experiment", "choose_condition")
    if not callable(event_factory) or not all(callable(getattr(module, name, None)) for name in names):
        result["note"] = "Selected parameters shown; this procedure supplies no separate trial-planning functions."
        return result
    run = _PlanningContext(values, profile, spec, Path(), synthetic=True, seed=0, stimulus_snapshots=snapshots)
    record_function = None
    if method == "constant_stimuli" and (callable(reviewer) or callable(spec.method_planner)):
        # Review must inspect the selected fixed-level schedule, not invent a
        # staircase just because this CSF experiment supports adaptive trials.
        selected_method = reviewer(run) if callable(reviewer) else None
        if selected_method is not None:
            from ..methods.contrast import ConstantContrastMethod
            if not isinstance(selected_method, ConstantContrastMethod):
                raise TypeError("Fixed method reviewer must return its existing ConstantContrastMethod.")
            result["planning_source"] = _source_position(reviewer)
        schedule = selected_method.schedule if selected_method is not None else spec.method_planner(values, run.seed)
        unique = {}
        for row in schedule:
            unique.setdefault(row["value"], {key: value for key, value in row.items()
                                            if key not in {"id", "repeat", "target", "contrast"}})
        conditions = [dict(item, id=i) for i, item in enumerate(unique.values(), 1)]
        condition = schedule[0]
        state = {}
        if selected_method is None:
            run.initialise(expected_trials=len(schedule),
                           resolution={"trial_selection_method": "constant_stimuli",
                                       "planned_trials": len(schedule),
                                       "fixed_contrast_levels": list(dict.fromkeys(row["contrast"] for row in schedule)),
                                       "fixed_repetitions_per_level_per_condition": values["fixed_repetitions"]})
        else:
            # The existing factory resolves its real preflight and metadata.
            # Do not advance the schedule, collect input or accept a response.
            state = selected_method.state
            record_function = selected_method._record
        representative_note = ("Constant stimuli: scientific conditions remain unchanged; "
                               f"{len(schedule)} planned presentations at the selected fixed levels. "
                               "This is one seeded sample; no adaptive staircase or threshold estimate.")
    elif method == "adaptive" and callable(reviewer):
        # New teaching methods declare their own execution-free preview.
        conditions, condition, state = reviewer(run)
        representative_note = (
            "Adaptive teaching method: illustrative selected trial with "
            "current starting digital strength; no threshold claim."
        )
    else:
        conditions = module.make_conditions(values)
        state = module.initialise_experiment(run, conditions)
        condition = module.choose_condition(run, conditions, state)
        representative_note = ("Trial-controlled values show one representative trial. "
                               "Random choices and adaptive strengths vary during a run.")
    if callable(getattr(module, "prepare_selection", None)):
        module.prepare_selection(run, condition)
    prepare = getattr(module, "prepare_method_stimuli", module.prepare_stimuli)
    stimuli = prepare(run, condition, state)
    units = getattr(module, "MEASUREMENT_UNITS", {})
    if units:
        if method != "constant_stimuli":
            record_function = record_function or getattr(module, "trial_record", None)
        if record_function is not None:
            record = (record_function(run, condition) if method == "constant_stimuli"
                      else record_function(run, condition, state))
            result["measurements"] = {name: {"sample": value, "units": units.get(name, "Units not declared")}
                                      for name, value in record.get("measurements", {}).items()}
            result["measurement_source"] = _source_position(record_function)
    result["inactive_fields"] = tuple(getattr(module, "REVIEW_INACTIVE_FIELDS", {}).get(method, ()))
    # Capture dependency reads before converting the returned mappings for display.
    reads = {slot: set(keys) for slot, keys in run.parameter_reads.items()}
    from ..core.timeline import as_trial_timeline
    timeline=as_trial_timeline(event_factory(values, condition))
    result.update(stimuli={slot: dict(p) for slot,p in stimuli.items()}, overrides=run.overrides,
                  parameter_reads=reads, conditions=conditions, resolution=getattr(run, "resolution", {}),
                  phases=timeline.resolve(values).to_dict()["phases"], trial_event_function=event_name,
                  phase_inputs={phase.name:phase.duration_ms for phase in timeline.phases if phase.kind in {"show","response"}},
                  note=representative_note)
    if profile is not None and getattr(profile, "expected_resolution_px", None):
        from ..core.presentation import plan_visible_stimulus
        from ..stimuli.registry import get_stimulus
        result["viewport"] = []
        for phase in timeline.resolve(values).phases:
            for placement in getattr(phase, "placements", ()):
                selected = snapshots[placement.slot]["document"]
                try:
                    geometry, _, _ = plan_visible_stimulus(profile, profile.expected_resolution_px,
                        get_stimulus(selected["stimulus_id"]), stimuli[placement.slot], placement)
                except ValueError as exc:
                    # Physical sampling/visibility can be invalid on this monitor
                    # while editing and synthetic simulation remain available.
                    # Human acquisition still uses its own strict preflight.
                    result["note"] += (
                        f" Physical presentation preflight for {phase.name}/{placement.slot}: "
                        f"{exc} Correct the setting or select a suitable monitor before human acquisition."
                    )
                    continue
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


def parameter_controller(spec, slot, key):
    """An explicit setting link, separate from binding/acquisition semantics."""
    return (spec.stimulus_parameter_controls.get(slot, {}).get(key)
            or spec.stimulus_field_bindings.get(slot, {}).get(key))


def review_rows(spec, values, snapshots, description, *, refresh_hz=None):
    """One visible table of the values that feed the selected procedure."""
    saved = spec.settings_snapshot()
    defaults = saved["values"] if saved else {f.key: f.default for f in spec.fields}
    def origin(field):
        base = (saved["file_identity"] if saved and field.key in saved["document"]["values"] else "Python ConfigField default")
        meaning = field.help_text.strip() or (
            f"Researcher-selected {field.section.lower()} parameter in "
            f"{spec.display_name}; see its experiment Python declaration."
        )
        return (f"Meaning: {meaning} | Setting: {field.key} "
                f"| Selected in TUI/saved setup; original {base} = {defaults[field.key]!r}")
    controls = set(spec.adaptive.controls) if spec.adaptive else set()
    method = values.get("contrast_method", "adaptive")
    adaptive = method == "adaptive"
    inactive = set(description.get("inactive_fields", ()))
    def field_origin(field):
        return origin(field) + (" | Not used by the selected method; existing settings validation still applies."
                                if field.key in inactive else "")
    rows = [("Experiment", field.display_label, str(values[field.key]), field_origin(field))
            for field in spec.fields if field.key not in controls or not adaptive]
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
    if spec.adaptive and adaptive:
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
            explanation = field.help_text.strip() or (
                f"Parameter {field.key} controls the {stimulus.display_name} "
                f"stimulus in slot {slot}; units are shown in the parameter column."
            )
            source = (f"{explanation} | Stimulus slot: {slot}, "
                      f"renderer: {identity}, source: {selected['file_identity']}")
            controller = parameter_controller(spec, slot, field.key)
            if controller:
                control = next(f for f in spec.fields if f.key == controller)
                source = (f"Derived / experiment-controlled by {controller} ({control.display_label}). "
                          f"Change Review → Edit experiment inputs / stimuli → {control.section} → {control.label}; "
                          "the stimulus Python default or preset is overridden. " + source)
            elif field.key in description["overrides"].get(slot, {}):
                usage = ("Trial-controlled; value shown for one representative trial"
                         if field.key in parameter_sources(description, slot)
                         else "Selected base parameter read by the experiment")
                source = f"{usage}. {source}"
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
        label = ("Number of distinct scientific conditions"
                 if values.get("contrast_method") == "constant_stimuli"
                 else "Number of condition/staircase entries")
        rows.append(("Conditions", label, str(len(description["conditions"])),
                     "Experiment's selected condition values"))
        if adaptive:
            distinct = {str(c.get("value", c.get("frequency_cpd", c.get("id"))))
                        for c in description["conditions"]}
            rows.append(("Conditions", "Number of distinct scientific conditions", str(len(distinct)),
                         "Independent staircase repeats do not add scientific conditions"))
        keys = dict.fromkeys(key for c in description["conditions"] for key in c if key not in {"id","repeat"})
        for key in keys:
            distinct = list(dict.fromkeys(str(c[key]) for c in description["conditions"] if key in c))
            rows.append(("Conditions",key,", ".join(distinct),"All configured values; repeats shown above"))
    for phase in description.get("session_phases", ()):
        group = "Session start (once)"
        if phase["kind"] == "key_wait":
            rows.append((group, phase["name"] + " key", phase["key"],
                         "Readiness only; fresh key after onset; Escape aborts; not a scientific answer"))
        else:
            rows.append((group, phase["name"] + " duration", str(phase["duration_ms"]), "ms; planned settling/display duration"))
        for placement in (phase.get("stimuli") or ([{"slot": phase["slot"]}] if phase.get("slot") else [])):
            rows.append((group, phase["name"] + " stimulus", placement["slot"], "Selected slot base parameters; prepared before session timing"))
        if phase.get("instructions"):
            rows.append((group, phase["name"] + " instructions", phase["instructions"], "Independent of response-key guidance"))
        if phase.get("beep"):
            rows.append((group, phase["name"] + " audio", str(phase["beep"]), phase["beep_trigger"]))
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
            # Structured conditions and schedule counts already have dedicated
            # rows. The saved general protocol can describe inactive methods;
            # retain it in the description, not as a selected fixed-run rule.
            if not prefix and (key in {"schedule", "condition_definitions"}
                               or (method == "constant_stimuli" and key == "protocol" and isinstance(value, dict))):
                continue
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
    for name, measurement in description.get("measurements", {}).items():
        rows.append(("Recorded measurements", f"{name} ({measurement['units']})", str(measurement["sample"]),
                     "Per-trial journal measurement; representative trial value, not an additional canonical column"))
    from ..data.trials import TRIAL_COLUMNS, TRIAL_DATA_DICTIONARY_FILENAME
    rows.extend([
        ("Saved data", "Canonical trial table", "trials.tsv", f"{len(TRIAL_COLUMNS)} columns; meanings and units in {TRIAL_DATA_DICTIONARY_FILENAME}"),
        ("Saved data", "Per-trial journal", "trial_events.jsonl", "Chronological events, prepared stimuli and custom measurements; retained on interruption"),
        ("Saved data", "Run settings and provenance", "manifest.json; experiment_config.json; resolved_experiment.json", "Source identities, selected settings and resolved scientific definitions"),
    ])
    if "primary_estimator" in description.get("resolution", {}):
        rows.append(("Saved data", "Adaptive results", "adaptive_session.json; primary_thresholds.json",
                     "Track history and declared primary estimator; incomplete conditions are excluded"))
    elif method == "constant_stimuli":
        rows.append(("Saved data", "Fixed-level results", "resolved_experiment.json / observed_level_accuracy",
                     "Accepted-response counts and accuracy per condition/strength; no staircase threshold"))
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
    adaptive = values.get("contrast_method", "adaptive") == "adaptive"
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
    if not adaptive:
        rows = [("Intensity", "Background intensity", f"{background:.10g}", digital_note)]
    if bounds:
        rows.append(("Intensity", "Maximum nominal probe intensity", ", ".join(f"{background+b:.10g}" for b in sorted(set(bounds))), "Experiment's resolved local additive headroom; digital command, not measured luminance"))
        if adaptive and any(b <= 0 or difference > b for b in bounds):
            rows.append(("Intensity", "Starting intensity check", "Outside at least one condition's headroom", "Review settings; no value was clipped"))
            return rows
        maximum = min(bounds)
    else:
        rows.append(("Intensity", "Maximum nominal probe intensity", "Resolve study conditions first", "The experiment defines condition-specific headroom"))
        return rows
    if not adaptive:
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
