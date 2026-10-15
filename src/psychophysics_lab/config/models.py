from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import math
from ..data.identifiers import validate_path_component


def photometry_is_test_data(profile) -> bool:
    return getattr(profile,'luminance_data_kind','unspecified') == 'synthetic' or any(marker in profile.calibration_method.lower()
               for marker in ("fake", "demo", "simulated", "synthetic"))


@dataclass(frozen=True)
class LuminanceCalibrationPoint:
    """One measured mapping between a digital display command and luminance."""

    screen_intensity: float
    luminance_cdm2: float

    def validate(self) -> None:
        if isinstance(self.screen_intensity, bool) or not math.isfinite(self.screen_intensity) or not 0.0 <= self.screen_intensity <= 1.0:
            raise ValueError("Calibration screen intensity must be in [0, 1].")
        if not math.isfinite(self.luminance_cdm2) or self.luminance_cdm2 < 0:
            raise ValueError("Calibration luminance must be non-negative.")


@dataclass(frozen=True)
class MonitorProfile:
    id: str
    display_name: str
    physical_width_m: float
    physical_height_m: float
    refresh_rate_hz: float
    viewing_distance_m: float
    pyglet_wakeup_rate_hz: float = 60
    expected_resolution_px: tuple[int, int] | None = None
    notes: str = ""
    calibration_status: str = "unverified"
    luminance_calibration: tuple[LuminanceCalibrationPoint, ...] = ()
    calibration_notes: str = ""

    profile_uuid: str = ""
    revision: int = 0
    origin: str = "reference"
    display_binding: dict[str, Any] | None = None
    qualified_experiments: tuple[str, ...] = ()
    calibration_method: str = ""
    calibration_date: str = ""
    luminance_data_kind: str = "unspecified"
    luminance_source_hash: str = ""
    geometry_status: str = "unverified"
    timing_status: str = "unverified"
    measurement_sources: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.luminance_data_kind not in {"genuine", "synthetic", "unspecified"}:
            raise ValueError("Unknown luminance provenance classification.")
        validate_path_component(self.id, label="monitor profile")
        allowed_sources = {"manual", "os_mode", "reference", "unspecified"}
        allowed_fields = {"physical_width_m", "physical_height_m", "viewing_distance_m", "refresh_rate_hz", "expected_resolution_px"}
        if not isinstance(self.measurement_sources, dict) or any(k not in allowed_fields or v not in allowed_sources for k, v in self.measurement_sources.items()):
            raise ValueError("Unknown display measurement source.")
        if any(self.measurement_sources.get(k) == "os_mode" for k in ("physical_width_m", "physical_height_m", "viewing_distance_m")):
            raise ValueError("Physical dimensions and viewing distance cannot be verified from OS mode.")
        for name in ("physical_width_m", "physical_height_m", "viewing_distance_m", "refresh_rate_hz", "pyglet_wakeup_rate_hz"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite.")
        for name in ("calibration_status", "geometry_status", "timing_status"):
            if getattr(self, name) not in ({"unverified", "manual_unverified", "verified", "accepted"} if name == "calibration_status" else {"unverified", "manual_unverified", "verified"}):
                raise ValueError(f"Unknown {name}.")
        if self.origin not in {"reference", "local"}:
            raise ValueError("Profile origin must be reference or local.")
        if not self.display_name.strip():
            raise ValueError("Display name must not be empty.")
        for experiment in self.qualified_experiments:
            validate_path_component(experiment, label="qualified experiment")
        if self.display_binding is not None:
            binding = self.display_binding
            if not isinstance(binding, dict) or any(type(binding.get(key)) is not int for key in ("index", "x", "y", "width", "height")):
                raise ValueError("Display binding needs integer index, position and resolution.")
            if binding.get("device_id") is not None and not isinstance(binding["device_id"], str):
                raise ValueError("Display binding device ID must be text.")
            if binding["index"] < 0 or binding["width"] <= 0 or binding["height"] <= 0:
                raise ValueError("Display binding has invalid index or resolution.")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ValueError("Profile revision must be a nonnegative integer.")
        if not self.id.strip():
            raise ValueError("Monitor profile id must not be empty.")
        if self.physical_width_m <= 0 or self.physical_height_m <= 0:
            raise ValueError("Physical monitor dimensions must be positive.")
        if self.refresh_rate_hz <= 0:
            raise ValueError("Refresh rate must be positive.")
        if self.viewing_distance_m <= 0:
            raise ValueError("Viewing distance must be positive.")
        if self.pyglet_wakeup_rate_hz <= 0:
            raise ValueError("Pyglet wake-up rate must be positive.")
        if self.expected_resolution_px is not None:
            width, height = self.expected_resolution_px
            if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in (width, height)):
                raise ValueError("Expected resolution must contain positive pixel dimensions.")
        for point in self.luminance_calibration:
            point.validate()
        commands = [point.screen_intensity for point in self.luminance_calibration]
        luminances = [point.luminance_cdm2 for point in self.luminance_calibration]
        if len(set(commands)) != len(commands) or len(set(luminances)) != len(luminances):
            raise ValueError("Calibration points must have unique commands and luminances.")
        ordered = sorted(self.luminance_calibration, key=lambda point: point.screen_intensity)
        if any(a.luminance_cdm2 >= b.luminance_cdm2 for a, b in zip(ordered, ordered[1:])):
            raise ValueError("Measured luminance must increase with the digital command.")

    @property
    def has_accepted_luminance_mapping(self) -> bool:
        """Mapping reviewed for use; never itself proves physical luminance."""
        return len(self.luminance_calibration) >= 2 and (
            self.calibration_status == "accepted" or self.has_verified_luminance_mapping
        )

    @property
    def has_verified_luminance_mapping(self) -> bool:
        return (
            self.calibration_status.strip().lower() == "verified"
            and bool(self.luminance_calibration)
            and not photometry_is_test_data(self)
        )

    def screen_intensity_for_luminance(
        self,
        luminance_cdm2: float,
        *,
        luminance_tolerance: float = 1e-6,
    ) -> float | None:
        """Return a calibrated command for a measured luminance, if encoded."""
        matches = [
            point.screen_intensity
            for point in self.luminance_calibration
            if abs(point.luminance_cdm2 - float(luminance_cdm2)) <= luminance_tolerance
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"Monitor profile {self.id!r} contains duplicate luminance calibration points "
                f"for {luminance_cdm2} cd/m²."
            )
        return matches[0]

    def validate_luminance_pair(
        self,
        *,
        luminance_cdm2: float,
        screen_intensity: float,
        intensity_tolerance: float = 1e-6,
    ) -> None:
        """Validate a physical/digital pair when a trusted mapping is present.

        Profiles without an encoded calibration table remain usable, but the run
        is explicitly marked as manual/unverified in the manifest and TUI.
        """
        if not math.isfinite(luminance_cdm2) or not math.isfinite(screen_intensity):
            raise ValueError("Luminance and digital command must be finite.")
        if not self.has_verified_luminance_mapping:
            return
        expected = self.screen_intensity_for_luminance(luminance_cdm2)
        if expected is None:
            raise ValueError(
                f"{luminance_cdm2} cd/m² is not present in the selected monitor's "
                "encoded luminance calibration table."
            )
        if abs(expected - float(screen_intensity)) > intensity_tolerance:
            raise ValueError(
                "Background luminance and digital screen intensity do not form a calibrated "
                f"pair for this monitor. {luminance_cdm2} cd/m² maps to {expected}, "
                f"not {screen_intensity}."
            )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.expected_resolution_px is not None:
            data["expected_resolution_px"] = list(self.expected_resolution_px)
        data["luminance_calibration"] = [
            asdict(point) for point in self.luminance_calibration
        ]
        return data


@dataclass(frozen=True)
class SetupRequest:
    participant_id: str
    session_mode: str
    experiment_id: str
    monitor_profile_id: str
    experiment_values: dict[str, Any]
    data_root: str | None = None
    monitor_profile_hash: str | None = None
