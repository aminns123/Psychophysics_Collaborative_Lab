from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping

from ..config.models import MonitorProfile

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

    @property
    def target_key(self) -> str:
        return self.legacy_key or self.key

    def coerce(self, value: Any) -> Any:
        if value is None or value == "":
            if self.default is None:
                raise ValueError(f"{self.label} must be selected.")
            value = self.default

        if self.kind == "int":
            return int(value)
        if self.kind == "float":
            return float(value)
        if self.kind == "choice":
            if value not in self.choices:
                for choice in self.choices:
                    if str(choice) == str(value):
                        return choice
                raise ValueError(f"{self.label}: {value!r} is not an allowed choice.")
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
    # Optional experiment-specific clarifications for the canonical trial
    # dictionary. Keys are trials.tsv column names; values may override
    # logical_type, units_or_encoding, meaning and/or notes.
    trial_column_overrides: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def field_defaults(self) -> dict[str, Any]:
        return {item.key: item.default for item in self.fields}

    def normalise_values(self, values: Mapping[str, Any]) -> dict[str, Any]:
        normalised: dict[str, Any] = {}
        for item in self.fields:
            normalised[item.key] = item.coerce(values.get(item.key, item.default))

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
