"""Explicit local copies and append-only revisions of display profiles."""
from dataclasses import replace, asdict
import json
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import Header, Footer, Button, Static, Input, Label, Select
from ..config.local import save_profile
from ..config.monitor import _profile_from_dict
from ..core.display import enumerate_displays

class ProfileScreen(Screen):
    def __init__(self, *, profile):
        super().__init__()
        self.profile = profile
        self.displays = ()

    def compose(self) -> ComposeResult:
        from .setup import _nav_bar
        p = self.profile
        with Vertical(id="fixed-shell"):
            yield Header()
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="profile-back")
                yield Button("Save local revision", id="profile-save", variant="success")
        with VerticalScroll(classes="page-body"):
            yield Static("Reference profiles are shared specifications. Save a local copy with a new ID. Display binding, geometry and timing are separate from luminance calibration. Saving a profile does not certify laboratory measurements.")
            values = {
                "id": p.id if p.origin == "local" else p.id + "_local",
                "display_name": p.display_name,
                "physical_width_m": p.physical_width_m,
                "physical_height_m": p.physical_height_m,
                "viewing_distance_m": p.viewing_distance_m,
                "refresh_rate_hz": p.refresh_rate_hz,
                "pyglet_wakeup_rate_hz": p.pyglet_wakeup_rate_hz,
                "notes": p.notes,
                "calibration_method": p.calibration_method,
                "calibration_date": p.calibration_date,
                "calibration_notes": p.calibration_notes,
                "qualified_experiments": ",".join(p.qualified_experiments),
            }
            labels = {"qualified_experiments": "Explicitly qualified experiments (comma-separated IDs, after laboratory validation)", "physical_width_m": "Screen width (metres)", "physical_height_m": "Screen height (metres)", "viewing_distance_m": "Viewing distance (metres)", "refresh_rate_hz": "Refresh rate (Hz; e.g. 59.94)", "pyglet_wakeup_rate_hz": "Legacy callback rate (Hz; does not certify presentation timing)"}
            for key, value in values.items():
                yield Label(labels.get(key, key.replace("_", " ").title()))
                yield Input(value=str(value), id="profile-" + key)
            for name in ("calibration_status", "geometry_status", "timing_status"):
                yield Label(name.replace("_", " ").title())
                yield Select([(v, v) for v in ("unverified", "manual_unverified", "verified")], value=getattr(p, name), allow_blank=False, id="profile-" + name)
            yield Label("Measured luminance table (JSON list of screen_intensity / luminance_cdm2 objects)")
            yield Input(value=json.dumps(p.to_dict()["luminance_calibration"]), id="profile-luminance")
            yield Button("Detect connected displays", id="profile-detect")
            yield Select([], id="profile-binding")
            yield Static("Detection is explicit and may initialise the display driver. Select the display that will present the stimuli; a missing binding prevents a local profile from launching.")
            yield Static("", id="profile-status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from .setup import _handle_nav
        if _handle_nav(self, event):
            return
        event.stop()
        if event.button.id == "profile-back":
            self.app.pop_screen()
            return
        status = self.query_one("#profile-status", Static)
        try:
            if event.button.id == "profile-detect":
                self.displays = enumerate_displays()
                selector = self.query_one("#profile-binding", Select)
                selector.set_options([(f"Display {d.index}: {d.width} × {d.height} at ({d.x}, {d.y}), {d.refresh_hz or 'unknown'} Hz", d.index) for d in self.displays])
                if self.displays:
                    selector.value = self.displays[0].index
                status.update("Select the correct display; detection does not validate physical dimensions.")
            elif event.button.id == "profile-save":
                payload = self.profile.to_dict()
                for key in ("id", "display_name", "notes", "calibration_method", "calibration_date", "calibration_notes"):
                    payload[key] = self.query_one("#profile-" + key, Input).value
                for key in ("physical_width_m", "physical_height_m", "viewing_distance_m", "refresh_rate_hz", "pyglet_wakeup_rate_hz"):
                    payload[key] = float(self.query_one("#profile-" + key, Input).value)
                for key in ("calibration_status", "geometry_status", "timing_status"):
                    payload[key] = self.query_one("#profile-" + key, Select).value
                payload["luminance_calibration"] = json.loads(self.query_one("#profile-luminance", Input).value)
                payload["qualified_experiments"] = [x.strip() for x in self.query_one("#profile-qualified_experiments", Input).value.split(",") if x.strip()]
                payload["origin"] = "local"
                selection = self.query_one("#profile-binding", Select).value
                if self.displays and selection is not Select.BLANK:
                    selected = next(d for d in self.displays if d.index == selection)
                    payload["display_binding"] = asdict(selected)
                    payload["expected_resolution_px"] = [selected.width, selected.height]
                if not payload.get("display_binding"):
                    raise ValueError("Detect and select a display before saving a local profile.")
                existing = self.app.monitor_profiles.get(payload["id"])
                if existing and existing.origin != "local":
                    raise ValueError("A local profile cannot replace a shared reference ID. Use a new ID.")
                same = payload["id"] == self.profile.id and self.profile.origin == "local"
                if existing and not same:
                    raise ValueError("That ID already exists. Open that local profile to edit it or choose a new ID.")
                if not same:
                    payload["profile_uuid"] = ""
                    payload["revision"] = 0
                result = save_profile(self.app.local_config_root, _profile_from_dict(payload), expected_revision=self.profile.revision if same else 0)
                self.profile = result
                self.app.reload_profiles()
                status.update(f"Saved {result.id} revision {result.revision} in {self.app.local_config_root}. Shared reference files are unchanged.")
        except (ValueError, TypeError, KeyError, StopIteration, OSError) as exc:
            status.update(str(exc))
