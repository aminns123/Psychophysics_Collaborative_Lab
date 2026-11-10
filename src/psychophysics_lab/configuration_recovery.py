"""Researcher-reviewed recovery of settings, separate from executable configuration."""

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from fractions import Fraction
import hashlib
import math
import sys

from .config.preflight import validate_setup
from .config.sharing import FORMAT, SCHEMA_VERSION, make_document, save_local, software_identity
from .config.stimulus_parameters import snapshot
from .experiments._internal.spec import ConfigField


@dataclass(frozen=True)
class RecoveryRule:
    """One versioned mapping declared by the installed component's author."""

    schema_version: int
    source_sha256: str
    engine_sha256: str
    old_key: str
    new_key: str
    old_kind: str
    old_units: str
    new_units: str
    meaning: str
    reason: str
    scale: float | None = None


@dataclass
class RecoveryRow:
    path: tuple[str, ...]
    field: ConfigField
    status: str
    explanation: str
    historical: dict = field(default_factory=dict)
    suggestion: object = None
    default: object = None
    rule: RecoveryRule | None = None
    value: object = None
    decisions: list = field(default_factory=list)
    locked: bool = False

    @property
    def resolved(self):
        return self.value is not None

    @property
    def label(self):
        group = self.path[1] if self.path[0] == "stimuli" else self.path[0].title()
        return f"{group}: {self.field.display_label}"

    def decide(self, action, value=None):
        if self.locked:
            raise ValueError(self.explanation)
        if action == "reject":
            value = None
        elif action == "accept" and self.suggestion is not None:
            value = self.suggestion
        elif action == "default" and self.default is not None:
            value = self.default
        elif action == "replace":
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError("Enter an explicit value before replacing this setting.")
            value = self.field.coerce(value)
        else:
            raise ValueError("This row has no value available for that action.")
        if action != "reject":
            _check_value(self.field, value)
        self.value = value
        self.decisions.append({"action": action, "value": value})


def _check_value(field, value):
    if field.kind == "choice":
        valid = any(type(value) is type(option) and value == option for option in field.choices)
    elif field.kind == "float":
        valid = type(value) in (int, float)
    elif field.kind == "int":
        valid = type(value) is int
    else:
        valid = field.kind == "text" and isinstance(value, str) and bool(value.strip())
    if not valid:
        raise ValueError(f"{field.display_label}: supply an explicit {field.kind} value.")
    field.coerce(value)


def _object(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object for recovery.")
    return value


def _schema(value, supported, label):
    if type(value) is not int or value not in supported:
        raise ValueError(f"{label} schema is unsupported for recovery.")


def _entries(document, section, slots):
    """Flatten only the recognized sections. Unrecognized data stays opaque."""
    result = {}
    for name, value in section.items():
        if name not in {"schema_version", "experiment_id", "values"}:
            result[("experiment", name)] = value
    for name, value in _object(section.get("values", {}), "Experiment values").items():
        result[("experiment", "values", name)] = value
    for slot, selected in _object(document.get("stimuli", {}), "Stimuli").items():
        if slot not in slots:
            result[("stimuli", slot)] = selected
            continue
        selected = _object(selected, "Stimulus")
        _schema(selected.get("schema_version"), {1}, "Stimulus")
        for name, value in selected.items():
            if name not in {"schema_version", "parameters"}:
                result[("stimuli", slot, name)] = value
        for name, value in _object(selected.get("parameters", {}), "Stimulus parameters").items():
            result[("stimuli", slot, "parameters", name)] = value
    for name, value in _object(document.get("presentation", {}), "Presentation").items():
        result[("presentation", name)] = value
    for name, value in document.items():
        if name not in {"format", "schema_version", "experiment", "stimuli", "presentation", "software"}:
            result[(name,)] = value
    return result


def _rules(component, kind, schema, software):
    # Only the defining module of an already loaded, locally verified component
    # may declare rules. Downloaded keys cannot name an import or a callable.
    definition = component.procedure if kind == "experiment" else component.render
    module = sys.modules.get(getattr(definition, "__module__", ""))
    declarations = vars(module).get("CONFIGURATION_RECOVERY_RULES", {}) if module is not None else {}
    rules = declarations.get((kind, component.id), ())
    selected = tuple(rule for rule in rules if isinstance(rule, RecoveryRule)
                     and (rule.schema_version, rule.source_sha256, rule.engine_sha256)
                     == (schema, software.get("source_sha256"), software.get("engine_sha256")))
    fields = component.fields if kind == "experiment" else component.parameters
    keys = {field.key for field in fields}
    if any(type(rule.schema_version) is not int or rule.new_key not in keys
           or not rule.meaning.strip() or not rule.reason.strip()
           or any(len(fingerprint) != 64 or set(fingerprint) - set("0123456789abcdef")
                  for fingerprint in (rule.source_sha256, rule.engine_sha256))
           for rule in selected):
        raise ValueError(f"{component.id}: invalid local recovery declaration. Review the installed author rules.")
    return selected


def _convert(rule, field, raw):
    if rule.new_units != field.units:
        raise ValueError("The local migration's target units no longer match the declaration.")
    _check_value(ConfigField(rule.old_key, rule.old_key, rule.old_kind, units=rule.old_units,
                             choices=field.choices), raw)
    if rule.scale is None:
        if rule.old_units != field.units or rule.old_kind != field.kind:
            raise ValueError("A rename requires matching declared types and units.")
        return raw
    if (rule.old_kind not in {"int", "float"} or field.kind not in {"int", "float"}
            or type(rule.scale) not in (int, float) or not math.isfinite(rule.scale) or rule.scale <= 0):
        raise ValueError("A unit conversion requires an explicit positive numeric scale.")
    # Keep integers exact while applying the declared factor. The existing
    # field validator rejects fractional results for integer destinations.
    converted = Fraction(str(raw)) * Fraction(str(rule.scale))
    if field.kind == "int":
        if converted.denominator != 1:
            raise ValueError("The declared conversion does not give an exact whole number.")
        return converted.numerator
    return float(converted)


def _row(path, field, entries, rules, exact):
    direct = path in entries and not any(rule.old_key == field.key for rule in rules)
    options = [(path, None)] if direct else []
    options += [(path[:-1] + (rule.old_key,), rule) for rule in rules if rule.new_key == field.key
                and path[:-1] + (rule.old_key,) in entries]
    historical = {key: entries[key] for key, _ in options}
    default = field.default
    try:
        _check_value(field, default)
    except (ValueError, TypeError, OverflowError):
        default = None
    row = RecoveryRow(path, field, "Missing", "No historical value was found for this field.",
                      historical, default=default)
    if not options:
        return row
    old_path, rule = options[0]
    if len(options) > 1 or (rule and sum(item.old_key == rule.old_key for item in rules) > 1):
        row.status = "Ambiguous"
        row.explanation = "More than one mapping is possible. Inspect the originals and enter the intended value."
        return row
    raw = entries[old_path]
    try:
        suggested = _convert(rule, field, raw) if rule else raw
        _check_value(field, suggested)
    except (ValueError, TypeError, OverflowError) as exc:
        row.status = "Out of range" if "outside its permitted range" in str(exc) else "Invalid"
        row.explanation = str(exc)
        return row
    row.suggestion = suggested
    row.rule = rule
    if rule:
        row.status = "Declared migration"
        row.explanation = f"Historical meaning: {rule.meaning} ({rule.old_kind}, {rule.old_units or 'no units'}). {rule.reason}"
    elif exact:
        row.status = "Compatible"
        row.explanation = "Declared field and complete scientific fingerprints match. The value is unchanged."
    else:
        row.status = "Check meaning"
        row.explanation = "Identity and value fit locally. Verify the original meaning and units before accepting."
    return row


@dataclass
class RecoveryDraft:
    spec: object
    stimuli: dict
    schema: int | None
    software: dict
    local_software: dict
    original_bytes: bytes
    rows: list
    unmapped: dict
    source_kind: str = "portable configuration"
    scope_note: str = ""

    @property
    def review_rows(self):
        return [row for row in self.rows if row.status != "Retained from Review"]

    @property
    def unresolved(self):
        return sum(not row.resolved for row in self.rows)

    def accept_compatible(self):
        for row in self.rows:
            if row.status == "Compatible" and not row.decisions:
                row.decide("accept")

    def unmapped_entries(self):
        statuses = {path: row.status for row in self.rows for path in row.historical}
        return [{"path": path, "value": value, "status": statuses.get(path, "Obsolete or unrecognised")}
                for path, value in self.unmapped.items()]

    def save(self, root, repo, current, profile, *, reviewed, verify_sources):
        if self.unresolved:
            raise ValueError(f"Resolve all {self.unresolved} incomplete settings before saving.")
        if not reviewed:
            raise ValueError("Confirm you reviewed the scientific meanings and installed protocol.")
        chosen = {row.path: row.value for row in self.rows}
        if self.source_kind == "experiment settings":
            for slot, bindings in self.spec.stimulus_field_bindings.items():
                for parameter, key in bindings.items():
                    chosen[("stimuli", slot, "parameters", parameter)] = chosen[("experiment", "values", key)]
        values = {field.key: chosen[("experiment", "values", field.key)] for field in self.spec.fields}
        documents = {
            slot: {"schema_version": 1, "stimulus_id": chosen[("stimuli", slot, "stimulus_id")],
                   "parameters": {field.key: chosen[("stimuli", slot, "parameters", field.key)]
                                  for field in stimulus.parameters}}
            for slot, stimulus in self.stimuli.items()
        }
        snapshots = {slot: snapshot(data, file_identity="configuration.json") for slot, data in documents.items()}
        verify_sources(self.spec, snapshots)
        candidate = replace(current, experiment_id=self.spec.id, experiment_values=values,
                            stimulus_snapshots=snapshots, monitor_profile_hash=None, researcher_override=None,
                            show_response_instructions=chosen[("presentation", "show_response_instructions")])
        document = make_document(repo, candidate, profile)
        if document["software"] != self.local_software:
            raise ValueError("Installed scientific source changed after preview. Start a new recovery preview.")
        checked = _entries(document, document["experiment"], self.stimuli)
        for path, value in chosen.items():
            if checked[path] != value:
                raise ValueError(f"Validation normalized {' / '.join(path)} to {checked[path]!r}. "
                                 "Enter that value explicitly or choose a different valid setting.")
        if self.spec.monitor_validator is not None and not self.spec.historical:
            self.spec.monitor_validator(values, profile)
        report = {
            "schema_version": 1, "experiment_id": self.spec.id, "original_schema": self.schema,
            "original_kind": self.source_kind,
            "original_sha256": hashlib.sha256(self.original_bytes).hexdigest(),
            "original_software": self.software, "local_software": self.local_software,
            "researcher_reviewed": True,
            "unmapped": self.unmapped_entries(),
            "parameters": [{"path": row.path, "status": row.status, "explanation": row.explanation,
                            "historical": [{"path": path, "value": value} for path, value in row.historical.items()],
                            "suggestion": row.suggestion, "declared_default": row.default,
                            "rule": asdict(row.rule) if row.rule else None,
                            "decisions": row.decisions + (
                                [{"action": "resolve experiment binding", "value": chosen[row.path]}]
                                if chosen[row.path] != row.value else []),
                            "value": chosen[row.path]} for row in self.rows],
        }
        return save_local(root, repo, document, current, profile, recovery=(self.original_bytes, report))


def prepare_recovery(document, raw, repo, *, verify_sources):
    """Read a supported shape and propose settings without creating a SetupRequest."""
    from .experiments._internal.registry import list_experiments
    from .stimuli.registry import list_stimuli

    _object(document, "Configuration")
    if document.get("format") != FORMAT:
        raise ValueError("Recovery supports PsyCoLab portable configuration files only.")
    schema = document.get("schema_version")
    _schema(schema, {1, SCHEMA_VERSION}, "Portable configuration")
    section = _object(document.get("experiment"), "Experiment")
    _schema(section.get("schema_version"), {1}, "Experiment")
    identity = section.get("experiment_id")
    spec = next((item for item in list_experiments(include_historical=True) if item.id == identity), None)
    if spec is None:
        raise ValueError(f"Required experiment {identity!r} is not installed and enabled. Verify it locally first.")
    entries = _entries(document, section, spec.stimulus_slots)
    software = _object(document.get("software", {}), "Software identity")
    installed = {item.id: item for item in list_stimuli()}
    stimuli = {}
    snapshots = {}
    for slot, family in spec.stimulus_slots.items():
        key = ("stimuli", slot, "stimulus_id")
        sid = entries.get(key, spec.stimulus_defaults[slot])
        stimulus = installed.get(sid) if isinstance(sid, str) else None
        if stimulus is None:
            raise ValueError(f"{slot}: required stimulus {sid!r} is not installed and enabled. Verify it locally first.")
        if stimulus.family != family:
            raise ValueError(f"{slot}: stimulus {sid!r} no longer belongs to the declared {family} family.")
        stimuli[slot] = stimulus
        snapshots[slot] = {"document": {"stimulus_id": sid}}
    verify_sources(spec, snapshots)
    local = software_identity(repo, spec, snapshots)
    exact = (schema == SCHEMA_VERSION and all(("stimuli", slot, "stimulus_id") in entries for slot in stimuli)
             and all(software.get(key) == local[key] for key in ("source_sha256", "engine_sha256", "dependencies")))
    experiment_rules = _rules(spec, "experiment", schema, software)
    rows = [_row(("experiment", "values", field.key), field, entries, experiment_rules, exact)
            for field in spec.fields]
    for slot, stimulus in stimuli.items():
        selection = ConfigField("stimulus_id", "Stimulus implementation", "choice", default=stimulus.id,
                                choices=(stimulus.id,))
        key = ("stimuli", slot, "stimulus_id")
        rows.append(_row(key, selection, entries, (), exact))
        if key in entries:
            rules = _rules(stimulus, "stimulus", schema, software)
            rows.extend(_row(("stimuli", slot, "parameters", field.key), field, entries, rules, exact)
                        for field in stimulus.parameters)
        else:
            for field in stimulus.parameters:
                path = ("stimuli", slot, "parameters", field.key)
                item = _row(path, field, {}, (), exact)
                if path in entries:
                    item.status = "Ambiguous"
                    item.explanation = "The original stimulus identity is missing. Its values cannot be mapped."
                    item.historical[path] = entries[path]
                rows.append(item)
    key = "show_response_instructions"
    presentation = ConfigField(key, "Show response-key guidance", "choice", default=True, choices=(True, False))
    rows.append(_row(("presentation", key), presentation, entries, (), exact))
    mapped = {key for row in rows if row.suggestion is not None for key in row.historical}
    unmapped = {key: value for key, value in entries.items() if key not in mapped}
    return RecoveryDraft(spec, stimuli, schema, deepcopy(software), local, raw, rows, unmapped)


def prepare_component_recovery(document, raw, repo, current, profile, *, slot, verify_sources):
    """Recover one local settings file against the already validated Review."""
    is_stimulus = {"stimulus_id", "parameters"} <= document.keys()
    schema = document.get("schema_version")
    if is_stimulus or "schema_version" in document:
        _schema(schema, {1}, "Local stimulus" if is_stimulus else "Local experiment settings")
    identity_key, values_key = ("stimulus_id", "parameters") if is_stimulus else ("experiment_id", "values")
    identity = document.get(identity_key)
    if not isinstance(identity, str):
        raise ValueError(f"The local file must identify its {identity_key}.")
    values = _object(document[values_key], "Local settings values")
    if is_stimulus:
        slots = [key for key, selected in current.stimulus_snapshots.items()
                 if selected["document"]["stimulus_id"] == identity]
        if not slots:
            raise ValueError(f"Required stimulus {identity!r} is not selected in this Review. "
                             "Install and verify it if needed, then select it in the appropriate stimulus slot.")
        if len(slots) > 1 and slot not in slots:
            raise ValueError(f"{identity!r} is selected in more than one slot: {', '.join(slots)}. "
                             "Return to Review, select a row in the intended slot, then preview this file again.")
        slot = slots[0] if len(slots) == 1 else slot
        prefix = ("stimuli", slot, "parameters")
        scope = f"Recovering only the {slot} stimulus. Experiment inputs and other stimuli retain their current Review values."
    else:
        if identity != current.experiment_id:
            raise ValueError(f"This file belongs to {identity!r}. Open Review for that experiment and preview it there. "
                             "Install and verify its implementation separately if it is missing.")
        prefix = ("experiment", "values")
        scope = ("Recovering experiment inputs only. Other settings retain their current Review values. "
                 "Stimulus fields bound to recovered experiment inputs follow those inputs.")

    baseline = make_document(repo, current, profile)
    draft = prepare_recovery(baseline, raw, repo, verify_sources=verify_sources)
    current_values = _entries(baseline, baseline["experiment"], draft.stimuli)
    historical = {(*prefix, key): value for key, value in values.items()}
    bindings = draft.spec.stimulus_field_bindings.get(slot, {}) if is_stimulus else {}
    metadata = document.get("parameter_info")
    metadata = metadata if isinstance(metadata, dict) else {}
    for index, row in enumerate(draft.rows):
        current_value = current_values[row.path]
        if row.path[:-1] != prefix or row.field.key in bindings:
            controlled = row.path[:-1] == prefix
            history = {row.path: historical[row.path]} if controlled and row.path in historical else {}
            draft.rows[index] = RecoveryRow(
                row.path, row.field, "Experiment-controlled" if controlled else "Retained from Review",
                f"Controlled by experiment input {bindings[row.field.key]}. Edit that input in Review."
                if controlled else "Retained from the already validated Review.",
                historical=history, value=current_value, locked=True,
                decisions=[{"action": "retain current Review", "value": current_value}],
            )
            continue
        recovered = _row(row.path, row.field, historical, (), False)
        info = metadata.get(row.field.key)
        if recovered.suggestion is not None and isinstance(info, dict) and "units" in info:
            if info["units"] != row.field.units:
                recovered.status = "Different units"
                recovered.suggestion = None
                recovered.explanation = (f"File declares {info['units']!r}, current field uses {row.field.units!r}. "
                                         "Verify the intended value in the current units before replacing it.")
        draft.rows[index] = recovered
    transferred = {row.path for row in draft.rows if row.suggestion is not None
                   or (row.locked and row.historical.get(row.path) == row.value)}
    draft.unmapped = {path: value for path, value in historical.items() if path not in transferred}
    draft.unmapped.update({(key,): value for key, value in document.items()
                           if key not in {identity_key, values_key, "schema_version", "saved_utc", "parameter_info"}})
    draft.schema = schema
    draft.software = {}
    draft.source_kind = "stimulus parameters" if is_stimulus else "experiment settings"
    draft.scope_note = scope
    return draft
