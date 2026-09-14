from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.expected_resolution_px is not None:
            data["expected_resolution_px"] = list(self.expected_resolution_px)
        return data


@dataclass(frozen=True)
class SetupRequest:
    participant_id: str
    session_mode: str
    experiment_id: str
    monitor_profile_id: str
    experiment_values: dict[str, Any]
