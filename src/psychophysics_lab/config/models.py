from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class LuminanceCalibrationPoint:
    """One measured mapping between a digital display command and luminance."""

    screen_intensity: float
    luminance_cdm2: float

    def validate(self) -> None:
        if not 0.0 <= self.screen_intensity <= 1.0:
            raise ValueError("Calibration screen intensity must be in [0, 1].")
        if self.luminance_cdm2 < 0:
            raise ValueError("Calibration luminance must be non-negative.")


@dataclass(frozen=True)
class MonitorProfile:
    id: str
    display_name: str
    physical_width_m: float
    physical_height_m: float
    refresh_rate_hz: int
    viewing_distance_m: float
    pyglet_wakeup_rate_hz: int = 60
    expected_resolution_px: tuple[int, int] | None = None
    notes: str = ""
    calibration_status: str = "unverified"
    luminance_calibration: tuple[LuminanceCalibrationPoint, ...] = ()
    calibration_notes: str = ""

    def validate(self) -> None:
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
            if width <= 0 or height <= 0:
                raise ValueError("Expected resolution must contain positive pixel dimensions.")
        for point in self.luminance_calibration:
            point.validate()

    @property
    def has_verified_luminance_mapping(self) -> bool:
        return (
            self.calibration_status.strip().lower() == "verified"
            and bool(self.luminance_calibration)
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
