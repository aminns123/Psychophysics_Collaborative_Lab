from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping
import math
from types import MappingProxyType

from psychophysics_lab.config.models import MonitorProfile

DataPathBuilder = Callable[[Mapping[str, Any], MonitorProfile], Iterable[str]]


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    kind: str
    default: Any = None
    choices: tuple[Any, ...] = ()
    help_text: str = ""
    legacy_key: str | None = None

    units: str = ""
    minimum: float | None = None
    maximum: float | None = None
    editable: bool = True
    section: str = "Experiment"

    @property
    def display_label(self) -> str:
        return f"{self.label} ({self.units})" if self.units else self.label

    @property
    def target_key(self) -> str:
        return self.legacy_key or self.key

    def coerce(self, value: Any) -> Any:
        if not self.editable and value not in (None, "", self.default):
            raise ValueError(f"{self.display_label} is a fixed specification field.")
        if value is None or value == "":
            if self.default is None:
                raise ValueError(f"{self.display_label} must be selected.")
            value = self.default

        if self.kind in {"int", "float"}:
            if isinstance(value, bool):
                raise ValueError(f"{self.display_label} must be a number, not a boolean.")
            if self.kind == "int":
                # JSON integers and TUI decimal strings must not pass through a
                # binary float: valid 64-bit seeds can otherwise silently round.
                from decimal import Decimal, InvalidOperation
                try:
                    exact = Decimal(str(value))
                except InvalidOperation as exc:
                    raise ValueError(f"{self.display_label} must be a number.") from exc
                if not exact.is_finite():
                    raise ValueError(f"{self.display_label} must be finite.")
                if exact != exact.to_integral_value():
                    raise ValueError(f"{self.display_label} must be a whole number.")
                number = int(exact)
            else:
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError(f"{self.display_label} must be finite.")
            if self.minimum is not None and number < self.minimum or self.maximum is not None and number > self.maximum:
                raise ValueError(f"{self.display_label} ({self.key.replace(chr(95), chr(45))}) = {number:g} is outside its permitted range [{self.minimum if self.minimum is not None else '-infinity'}, {self.maximum if self.maximum is not None else '+infinity'}].")
            return int(number) if self.kind == "int" else number
        if self.kind == "choice":
            if value not in self.choices:
                for choice in self.choices:
                    if str(choice) == str(value):
                        return choice
                raise ValueError(f"{self.display_label}: {value!r} is not an allowed choice.")
            return value
        if self.kind == "text":
            return str(value)
        raise ValueError(f"Unsupported configuration field kind: {self.kind}")


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    display_name: str
    description: str
    legacy_module: str
    legacy_experiment_type: str
    fields: tuple[ConfigField, ...]
    fixed_setup: Mapping[str, Any] = field(default_factory=dict)
    compatible_monitor_profiles: tuple[str, ...] = ()
    validator: Callable[[Mapping[str, Any]], Iterable[str]] | None = None
    # Optional human-facing grouping levels placed between display profile and
    # date. This keeps the universal storage engine experiment-agnostic.
    data_path_builder: DataPathBuilder | None = None
    data_directory_name: str = ""
    # Optional experiment-specific clarifications for the canonical trial
    # dictionary. Keys are trials.tsv column names; values may override
    # logical_type, units_or_encoding, meaning and/or notes.
    trial_column_overrides: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    monitor_validator: Callable | None = None
    configure_module: str = "psychophysics_lab.researcher"
    configure_function: str = "configure"
    source_paths: tuple[str, ...] = ()
    adaptive: Any = None
    response_paradigm: Any = None
    procedure: Callable | None = None
    calibration_requirements: tuple[str, ...] = ()
    calibration_not_applicable: str = ""
    monitor_capabilities: tuple[str, ...] | None = None
    stimulus_slots: Mapping[str, str] = field(default_factory=dict)
    stimulus_defaults: Mapping[str, str] = field(default_factory=dict)
    stimulus_field_bindings: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    supports_simulation: bool = False
    default_config: str = ""
    acquisition_block_reason: str = ""
    historical: bool = False
    migrate_values: Callable | None = None
    scientific_spec: Mapping[str, Any] = field(default_factory=dict)
    # Appended to preserve existing positional constructor arguments.
    origin_namespace: str = ""
    method_planner: Callable | None = None

    def __post_init__(self):
        if self.procedure is not None:
            if not self.calibration_requirements and not self.calibration_not_applicable.strip():
                raise ValueError("Declare calibration_requirements (geometry, luminance, timing), or explain calibration_not_applicable for this task.")
            if self.monitor_capabilities is None:
                raise ValueError("Declare monitor_capabilities explicitly: display_binding and/or resolution, or () when not applicable.")
        if any(key not in {"display_binding", "resolution"} for key in (self.monitor_capabilities or ())):
            raise ValueError("Unknown monitor capability; use display_binding or resolution.")
        if self.calibration_requirements and self.calibration_not_applicable:
            raise ValueError("Choose required calibration or a justified not-applicable declaration, not both.")
        if any(key not in {"geometry", "luminance", "timing"} for key in self.calibration_requirements):
            raise ValueError("Unknown experiment calibration requirement.")
        from pathlib import PurePosixPath
        from psychophysics_lab.data.identifiers import validate_path_component
        validate_path_component(self.id, label="experiment")
        if self.data_directory_name:
            validate_path_component(self.data_directory_name, label="experiment directory")
        if len({item.key for item in self.fields}) != len(self.fields):
            raise ValueError("Experiment fields must have unique keys.")
        if self.adaptive is not None:
            self.adaptive.validate({item.key for item in self.fields})
        if self.method_planner is not None and not callable(self.method_planner):
            raise TypeError("Experiment method planner must be callable.")
        if self.procedure is not None and not callable(self.procedure):
            raise TypeError("Experiment procedure must be callable.")
        for value in self.source_paths:
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or "\\" in value or not value.endswith(".py"):
                raise ValueError("Inspectable experiment sources must be relative Python files.")
        object.__setattr__(self, "fixed_setup", MappingProxyType(dict(self.fixed_setup)))
        object.__setattr__(self, "trial_column_overrides", MappingProxyType({key: MappingProxyType(dict(value)) for key, value in self.trial_column_overrides.items()}))

    def settings_snapshot(self):
        if not self.default_config:
            return None
        from psychophysics_lab.config.experiment_parameters import settings_snapshot
        return settings_snapshot(self)

    def field_defaults(self) -> dict[str, Any]:
        saved = self.settings_snapshot()
        return {item.key: saved["values"].get(item.key, item.default) for item in self.fields} if saved else {item.key: item.default for item in self.fields}

    def normalise_input_keys(self, values: Mapping[str, Any]) -> dict[str, Any]:
        """Apply only the experiment's declared compatibility migration."""
        return self.migrate_values(values) if self.migrate_values else dict(values)

    def normalise_values(self, values: Mapping[str, Any], *, use_config=True) -> dict[str, Any]:
        values = self.normalise_input_keys(values)
        pass  # Retired protocol branch removed.
        unknown = set(values) - {item.key for item in self.fields}
        if unknown:
            raise ValueError(f"Unknown experiment values: {sorted(unknown)}")
        defaults = self.field_defaults() if use_config and self.default_config else {item.key: item.default for item in self.fields}
        normalised: dict[str, Any] = {}
        for item in self.fields:
            normalised[item.key] = item.coerce(values.get(item.key, defaults[item.key]))
        if self.response_paradigm is not None and "response_keys" in normalised:
            from psychophysics_lab.experiments._internal.responses import ResponseParadigm
            keys = tuple(part.strip().upper() for part in normalised["response_keys"].split(","))
            ResponseParadigm(self.response_paradigm.id, self.response_paradigm.alternatives, keys)
            normalised["response_keys"] = ",".join(keys)

        errors = list(self.validator(normalised)) if self.validator else []
        if errors:
            raise ValueError("\n".join(errors))
        return normalised

    def data_path_parts(
        self,
        values: Mapping[str, Any],
        monitor_profile: MonitorProfile,
    ) -> tuple[str, ...]:
        """Return experiment-defined run-level grouping folders.

        Only fixed, scientifically useful run-level conditions belong here.
        Trial-varying values and implementation details belong in trials/config.
        """
        if self.data_path_builder is None:
            return ()
        normalised = self.normalise_values(values)
        return tuple(str(part) for part in self.data_path_builder(normalised, monitor_profile))

    def values_from_legacy_setup(self, setup: Mapping[str, Any]) -> dict[str, Any]:
        values = self.field_defaults()
        for item in self.fields:
            if item.target_key in setup:
                values[item.key] = setup[item.target_key]
        return values

    def build_legacy_setup(
        self,
        *,
        participant_id: str,
        values: Mapping[str, Any],
        monitor_profile: MonitorProfile,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        values = self.normalise_values(values)
        timestamp = now or datetime.now()

        setup: dict[str, Any] = dict(self.fixed_setup)
        for item in self.fields:
            setup[item.target_key] = values[item.key]

        setup.update(
            {
                "Name": participant_id,
                "Experiment_Type": self.legacy_experiment_type,
                "date_created": f"{timestamp.year}_{timestamp.month}_{timestamp.day}",
                "monitor_profile": monitor_profile.to_dict(),
            }
        )
        return setup
