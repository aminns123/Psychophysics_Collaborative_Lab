"""Explicit local copies and append-only revisions of display profiles."""
from dataclasses import replace, asdict
import json
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import Header, Footer, Button, Static, Input, Label, Select
from ..config.local import save_profile
from ..config.monitor import _profile_from_dict
from ..core.display import enumerate_displays, resolve_binding

class ProfileScreen(Screen):
    def __init__(self, *, profile):
        super().__init__()
        self.profile = profile
        self.displays = ()
        self.detected_values = {}

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
            yield Label("Expected pixel width and height (manual override; both blank = check at launch)")
            yield Input(value=str(p.expected_resolution_px[0]) if p.expected_resolution_px else "", id="profile-pixel-width")
            yield Input(value=str(p.expected_resolution_px[1]) if p.expected_resolution_px else "", id="profile-pixel-height")
            yield Static("Measure the active image area and eye-to-screen distance yourself. OS resolution may be DPI-scaled; verify actual fullscreen pixels. Refresh is an OS mode or manual value, not measured photon timing.")
            for name in ("calibration_status", "geometry_status", "timing_status"):
                yield Label(name.replace("_", " ").title())
                yield Select([(v, v) for v in ("unverified", "manual_unverified", "verified")], value=getattr(p, name), allow_blank=False, id="profile-" + name)
            yield Label("Measured luminance table (JSON list of screen_intensity / luminance_cdm2 objects)")
            yield Input(value=json.dumps(p.to_dict()["luminance_calibration"]), id="profile-luminance")
            yield Button("Detect connected displays", id="profile-detect")
            yield Select([], id="profile-binding")
            yield Button("Use detected resolution and refresh", id="profile-use-detected")
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
                selector = self.query_one("#profile-binding", Select)
                previous = next((d for d in self.displays if d.index == selector.value), None)
                binding = asdict(previous) if previous else self.profile.display_binding
                self.displays = enumerate_displays()
                selector.set_options([(f"Display {d.index}: {d.width} × {d.height} at ({d.x}, {d.y}), {d.refresh_hz or 'unknown'} Hz", d.index) for d in self.displays])
                if binding:
                    try:
                        selector.value = resolve_binding(binding, self.displays).index
                    except ValueError:
                        selector.value = Select.BLANK
                elif len(self.displays) == 1:
                    selector.value = self.displays[0].index
                status.update("Select the correct display; detection does not validate physical dimensions.")
            elif event.button.id == "profile-use-detected":
                selection = self.query_one("#profile-binding", Select).value
                selected = next((d for d in self.displays if d.index == selection), None)
                if selected is None:
                    raise ValueError("Detect and select a display first.")
                self.detected_values = {"expected_resolution_px": [selected.width, selected.height]}
                self.query_one("#profile-pixel-width", Input).value = str(selected.width)
                self.query_one("#profile-pixel-height", Input).value = str(selected.height)
                if selected.refresh_hz:
                    self.query_one("#profile-refresh_rate_hz", Input).value = str(selected.refresh_hz)
                    self.detected_values["refresh_rate_hz"] = selected.refresh_hz
                status.update("Copied OS mode values. Physical dimensions and viewing distance still require measurement. Unknown refresh was left unchanged.")
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
                pixels = [self.query_one("#profile-pixel-width", Input).value.strip(), self.query_one("#profile-pixel-height", Input).value.strip()]
                payload["expected_resolution_px"] = None if not any(pixels) else [int(v) for v in pixels]
                sources = dict(self.profile.measurement_sources)
                for key in ("physical_width_m", "physical_height_m", "viewing_distance_m", "refresh_rate_hz", "expected_resolution_px"):
                    old = self.profile.to_dict().get(key)
                    if key in self.detected_values and payload[key] == self.detected_values[key]:
                        sources[key] = "os_mode"
                    elif payload[key] != old:
                        sources[key] = "manual"
                    else:
                        sources.setdefault(key, "reference" if self.profile.origin == "reference" else "unspecified")
                payload["measurement_sources"] = sources
                # Measurements or binding changes invalidate the previous qualification.
                geometry_changed = any(payload[k] != self.profile.to_dict().get(k) for k in ("physical_width_m", "physical_height_m", "viewing_distance_m", "expected_resolution_px"))
                timing_changed = payload["refresh_rate_hz"] != self.profile.refresh_rate_hz
                if geometry_changed:
                    payload["geometry_status"] = "manual_unverified"
                if timing_changed:
                    payload["timing_status"] = "manual_unverified"
                selection = self.query_one("#profile-binding", Select).value
                if selection is Select.BLANK and self.displays:
                    raise ValueError("Select a connected display before saving.")
                if self.displays and selection is not Select.BLANK:
                    selected = next(d for d in self.displays if d.index == selection)
                    payload["display_binding"] = asdict(selected)
                    if self.profile.display_binding != payload["display_binding"]:
                        payload["geometry_status"] = "manual_unverified"
                        payload["timing_status"] = "manual_unverified"
                        payload["calibration_status"] = "manual_unverified"
                        payload["qualified_experiments"] = []
                if not payload.get("display_binding"):
                    raise ValueError("Detect and select a display before saving a local profile.")
                if geometry_changed or timing_changed:
                    payload["qualified_experiments"] = []
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
