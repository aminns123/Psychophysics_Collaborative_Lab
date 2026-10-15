"""Explicit local copies and append-only revisions of display profiles."""
from dataclasses import replace, asdict
import json
import os
import sys
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import Header, Footer, Button, Static, Input, Label, Select, Checkbox
from ..config.local import save_profile
from ..config.calibration_templates import (
    write_luminance_example, read_luminance_measurements
)
from ..config.monitor import _profile_from_dict
from ..core.display import enumerate_displays, resolve_binding

class ProfileScreen(Screen):
    def __init__(self, *, profile, focus_field: str | None = None):
        super().__init__()
        self.profile = profile
        self.displays = ()
        self.detected_values = {}
        self.focus_field = focus_field

    def on_mount(self) -> None:
        from .domain_feedback import profile_domains
        profile_domains(self)
        # A calibration-guide deep link opens the exact required input
        # instead of leaving the researcher hunting through a long form.
        if self.focus_field:
            target = self.query_one("#" + self.focus_field)
            self.call_after_refresh(target.scroll_visible)
            self.call_after_refresh(target.focus)

    def on_input_changed(self,event):
        if self.is_mounted:
            from .domain_feedback import profile_domains
            profile_domains(self)

    def compose(self) -> ComposeResult:
        from .setup import _nav_bar
        p = self.profile
        with Vertical(id="fixed-shell"):
            yield Header()
            yield _nav_bar()
            with Horizontal(classes="buttons"):
                yield Button("Back", id="profile-back")
                yield Button("Save profile / continue calibration", id="profile-save", variant="success")
            yield Static(
                "Saving creates a local monitor profile. Without a detected/bound display "
                "it is a draft and cannot launch human acquisition.",
                id="profile-save-feedback",
            )
        with VerticalScroll(classes="page-body"):
            yield Static(
                "Edit the physical image width/height and eye distance, then save a new "
                "local copy (or revision). A monitor binding is needed to RUN human "
                "experiments, but NOT to save a geometry draft. The shared reference "
                "profile remains unchanged. The edited profile is reloaded and selected "
                "automatically on the Calibrate page after saving."
            )
            yield Static(
                "[b]STEP 1 — Bind the real display (required to launch fullscreen tests)[/b]\n"
                "Click Detect connected displays, then select the actual display "
                "below. A previously saved unbound draft is NOT automatically "
                "associated with the primary monitor.",
                classes="info-card",
            )
            yield Button("Detect connected displays", id="profile-detect")
            yield Label("Physical monitor for fullscreen calibration")
            yield Select([], id="profile-binding")
            yield Button("Use detected resolution and refresh", id="profile-use-detected")
            yield Static(
                "[b]STEP 2 — Measure and enter geometric dimensions[/b]\n"
                "Screen size is the physical ACTIVE IMAGE AREA, not the "
                "Windows setting for resolution or desktop scaling. "
                "Saving a draft without binding is allowed but fullscreen calibration "
                "will be blocked until a display is bound."
            )
            yield Static("",id="live-input-domains",markup=False,classes="info-card")
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
            labels = {"qualified_experiments": "Explicitly qualified experiments (comma-separated IDs, after laboratory validation)", "physical_width_m": "Active screen image width (metres; e.g. 0.610 = 610 mm)", "physical_height_m": "Active screen image height (metres; e.g. 0.350 = 350 mm)", "viewing_distance_m": "Eye-to-screen viewing distance (metres; e.g. 1.0)", "refresh_rate_hz": "Refresh rate (Hz; e.g. 59.94)", "pyglet_wakeup_rate_hz": "Legacy callback rate (Hz; does not certify presentation timing)"}
            for key, value in values.items():
                yield Label(labels.get(key, key.replace("_", " ").title()))
                yield Input(value=str(value), id="profile-" + key)
            yield Label("Expected pixel width and height (manual override; both blank = check at launch)")
            yield Input(value=str(p.expected_resolution_px[0]) if p.expected_resolution_px else "", id="profile-pixel-width")
            yield Input(value=str(p.expected_resolution_px[1]) if p.expected_resolution_px else "", id="profile-pixel-height")
            yield Static("Measure the active image area and eye-to-screen distance yourself. OS resolution may be DPI-scaled; verify actual fullscreen pixels. Refresh is an OS mode or manual value, not measured photon timing.")
            yield Checkbox(
                "I personally measured the active WIDTH, HEIGHT and EYE DISTANCE "
                "and confirm these three entered values (not just defaults).",
                value=all(p.measurement_sources.get(key) == "manual" for key in
                          ("physical_width_m", "physical_height_m", "viewing_distance_m")),
                id="profile-confirm-manual-geometry",
            )
            yield Static(
                "Check this only after measuring. It records manual provenance even "
                "if a value happens to match the previous/reference value. "
                "It does NOT verify the ruler test or automatically qualify experiments.",
                classes="field-help",
            )
            for name in ("calibration_status", "geometry_status", "timing_status"):
                yield Label(name.replace("_", " ").title())
                statuses = ["unverified", "manual_unverified", "verified"]
                if name == "calibration_status" and p.calibration_status == "accepted":
                    statuses.append("accepted")
                yield Select([(v, v) for v in statuses], value=getattr(p, name), allow_blank=False, id="profile-" + name)
            yield Static(
                "[b]STEP 3 — Luminance: measured command-to-cd/m² pairs[/b]\n"
                "This needs a PHOTOMETER, not a ruler or Windows brightness slider. "
                "Use a digital grayscale command from 0 to 1 (e.g. 0.50), "
                "measure the light emitted in cd/m² and enter the readings in "
                "the JSON example. Create example opens an editable file on "
                "Windows. Fill at least TWO real screen-intensity / cd/m² pairs; "
                "unused blank rows can stay null. Meter method, date and notes "
                "are OPTIONAL, but recommended for reproducibility. Paste the "
                "absolute JSON path and click Load measurements into draft, "
                "then Save profile / continue calibration. The saved readings "
                "mark the measurement stage complete, NOT physically verified.\n"
                "If you have no photometer, leave this unverified; you can still "
                "run headless simulations and inspect geometry diagnostics.",
                classes="info-card",
            )
            if p.luminance_calibration:
                yield Static(
                    f"[green]Already saved in this profile: {len(p.luminance_calibration)} "
                    f"intensity / cd/m² pairs (revision {p.revision}).[/green] "
                    "If these are the readings you want, there is NO need to load "
                    "an older JSON again. Click Back to view calibration progress, "
                    "or Save profile / continue calibration after making edits. "
                    "Saved pairs are not automatically physically verified.",
                    classes="info-card",
                )
            else:
                yield Static(
                    "[yellow]No saved intensity / luminance pairs on this profile yet.[/yellow] "
                    "Import a completed JSON, or enter pairs in the editable draft "
                    "list below, then Save profile / continue calibration.",
                    classes="info-card",
                )
            yield Button("Create / open example luminance JSON", id="profile-luminance-example")
            yield Label("Path to completed luminance measurement JSON file")
            yield Input(value="", placeholder="C:\\...\\luminance_...json", id="profile-luminance-path")
            yield Button("Load measurements into draft (not yet saved)", id="profile-luminance-load")
            yield Static("", id="profile-luminance-feedback")
            yield Label("Measurement values in this profile (editing requires Save; no need to re-import if already populated)")
            yield Input(value=json.dumps(p.to_dict()["luminance_calibration"]), id="profile-luminance")
            yield Static(
                "[b]STEP 4 — Timing, provenance and experiment qualification[/b]\n"
                "Software flicker tests do not measure photon onset. Record "
                "physical timing evidence separately before choosing Verified. "
                "Only declare an experiment qualified after the laboratory has "
                "reviewed all its requirements. Use the experiment ID, e.g. "
                "'contrast_sensitivity', in the qualified-experiments field; "
                "a ruler check alone is insufficient.",
                classes="info-card",
            )
            yield Static(
                "Detected OS resolution/refresh values can be copied into this profile, "
                "but they must agree with the selected physical display when launching "
                "a fullscreen test. Check physical dimensions and eye distance manually."
            )
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
        saved_result = None
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
                notice = "Connected displays detected. Select the correct physical display; OS mode does not measure active width, height or eye distance."
                status.update(notice)
                self.query_one("#profile-save-feedback", Static).update(notice)
                self.app.notify(notice, timeout=7)
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
                notice = "Copied detected pixel resolution/refresh into the draft. Measure physical display size and viewing distance, then Save local revision."
                status.update(notice)
                self.query_one("#profile-save-feedback", Static).update(notice)
                self.app.notify(notice, timeout=7)
            elif event.button.id == "profile-luminance-example":
                example = write_luminance_example(self.app.local_config_root, self.profile)
                self.query_one("#profile-luminance-path", Input).value = str(example)
                message = (
                    f"Editable example: {example}. Enter at least two REAL command / cd/m² "
                    "measurements (other null rows may remain blank). Method, date and "
                    "notes are recommended but optional. Save the file and Load measurements. "
                    "Example placeholders are NOT observations."
                )
                if sys.platform == "win32":
                    try:
                        os.startfile(str(example))
                    except OSError as exc:
                        message += f" Automatic file opening failed ({exc}); open this path manually."
                status.update(message)
                self.query_one("#profile-luminance-feedback", Static).update(message)
                self.app.notify("Luminance example ready; edit the file before loading.", timeout=8)
            elif event.button.id == "profile-luminance-load":
                measurement_path = self.query_one("#profile-luminance-path", Input).value
                from ..config.calibration_dataset import import_observations
                self.imported_raw, _ = import_observations(measurement_path,self.profile,self.app.local_config_root)
                draft = read_luminance_measurements(
                    measurement_path, self.profile,
                    local_config_root=self.app.local_config_root
                )
                for key in ("calibration_method", "calibration_date", "calibration_notes"):
                    if not draft[key]:
                        draft[key] = self.profile.to_dict()[key]
                # Apply only after EVERY field and all measured pairs validated.
                self.query_one("#profile-luminance", Input).value = json.dumps(draft["luminance_calibration"])
                self.query_one("#profile-calibration_method", Input).value = draft["calibration_method"]
                self.query_one("#profile-calibration_date", Input).value = draft["calibration_date"]
                self.query_one("#profile-calibration_notes", Input).value = draft["calibration_notes"]
                same_mapping = all(draft[key] == self.profile.to_dict()[key] for key in
                                   ("luminance_calibration", "calibration_method", "calibration_date"))
                if not same_mapping:
                    self.query_one("#profile-calibration_status", Select).value = "manual_unverified"
                    self.query_one("#profile-qualified_experiments", Input).value = ""
                warnings = draft.get("warnings", [])
                message = (
                    f"Loaded {len(draft['luminance_calibration'])} entered command/luminance "
                    "pairs into this UNSAVED, UNVERIFIED draft. Click Save profile / "
                    "continue calibration. This completes the measurement stage, not "
                    "laboratory certification. "
                    + ("Unchanged mapping retains saved verification/qualification." if same_mapping else
                       "Changed mapping clears experiment qualification pending review.")
                    + ("\nOptional metadata warnings: " + "; ".join(warnings) if warnings else "")
                )
                status.update(message)
                self.query_one("#profile-luminance-feedback", Static).update(message)
                self.app.notify("Luminance draft loaded; review and Save to persist.", timeout=8)
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
                    elif self.profile.origin == "reference":
                        sources.setdefault(key, "reference")
                if self.query_one("#profile-confirm-manual-geometry", Checkbox).value:
                    for key in ("physical_width_m", "physical_height_m", "viewing_distance_m"):
                        sources[key] = "manual"
                payload["measurement_sources"] = sources
                # Changes to a scientific measurement mapping invalidate
                # previous certification and any per-experiment qualification.
                # Import/Save must NEVER auto-verify photometry.
                luminance_changed = (
                    payload["luminance_calibration"]
                    != self.profile.to_dict()["luminance_calibration"]
                )
                if luminance_changed:
                    payload["calibration_status"] = "manual_unverified"
                    payload["qualified_experiments"] = []
                elif payload["calibration_status"] == "verified":
                    # Researcher-initiated declaration is distinct from importing
                    # measured values; optional metadata may be missing. Preserve
                    # that limitation in warnings, not an arbitrary save blocker.
                    if len(payload["luminance_calibration"]) < 2:
                        raise ValueError(
                            "At least two measured intensity/luminance pairs are needed "
                            "before explicitly declaring photometry verified."
                        )
                # Measurements or binding changes invalidate the previous qualification.
                geometry_changed = any(payload[k] != self.profile.to_dict().get(k) for k in ("physical_width_m", "physical_height_m", "viewing_distance_m", "expected_resolution_px"))
                timing_changed = payload["refresh_rate_hz"] != self.profile.refresh_rate_hz
                if geometry_changed:
                    payload["geometry_status"] = "manual_unverified"
                if timing_changed:
                    payload["timing_status"] = "manual_unverified"
                selection = self.query_one("#profile-binding", Select).value
                if self.displays and selection is Select.BLANK:
                    raise ValueError(
                        "You detected physical displays but did not choose one. "
                        "Select your monitor in the Physical monitor dropdown "
                        "or go Back and save only an unbound draft without detection."
                    )
                if self.displays and selection is not Select.BLANK:
                    selected = next(d for d in self.displays if d.index == selection)
                    payload["display_binding"] = asdict(selected)
                    if self.profile.display_binding != payload["display_binding"]:
                        payload["geometry_status"] = "manual_unverified"
                        payload["timing_status"] = "manual_unverified"
                        payload["calibration_status"] = "manual_unverified"
                        payload["qualified_experiments"] = []
                # A physical monitor is not required to SAVE measurements. An
                # unbound local copy is clearly a draft: no physical human run
                # may use it until a suitable monitor is bound and validated.
                if not payload.get("display_binding") and self.profile.origin != "local":
                    payload["geometry_status"] = "manual_unverified"
                    payload["timing_status"] = "manual_unverified"
                    payload["qualified_experiments"] = []
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
                unchanged_revision = self.profile.revision
                result = save_profile(self.app.local_config_root, _profile_from_dict(payload), expected_revision=self.profile.revision if same else 0)
                if hasattr(self,"imported_raw"):
                    from ..config.calibration_dataset import load_active,merge_observations,save_active
                    active=load_active(self.app.local_config_root,result)
                    data=merge_observations(active,self.imported_raw,mode='replace_all',confirmed=True)
                    data.update(method=result.calibration_method,date=result.calibration_date,notes=result.calibration_notes)
                    result,_=save_active(self.app.local_config_root,result,data,expected_version=active['version'])
                no_changes = same and result.revision == unchanged_revision
                saved_result = result
                # Do not report success until the on-disk revision is visible
                # through the same loader used by future experiment sessions.
                self.app.reload_profiles()
                persisted = self.app.monitor_profiles.get(result.id)
                if persisted != result:
                    raise RuntimeError("Saved display profile could not be reloaded; inspect the local configuration folder.")
                self.profile = persisted
                detail = ("bound to a selected physical display" if result.display_binding
                          else "saved as an UNBOUND DRAFT (not ready for human acquisition)")
                notice = (
                    "No changes to save. " if no_changes else
                    f"Saved {result.id}, revision {result.revision}; {detail}. "
                    "The Calibrate page now shows your saved values."
                )
                status.update(notice)
                self.query_one("#profile-save-feedback", Static).update(f"[green]{notice}[/green]")
                self.app.notify(notice, title="Display profile saved", timeout=8)
                # Saving a profile must not silently change the current
                # calibration page. Researchers review the saved result and
                # choose Next stage themselves when ready.
                self.app.pop_screen()
        except Exception as exc:
            action = event.button.id
            operation = {
                "profile-detect": "Display detection failed",
                "profile-use-detected": "Detected values not copied",
                "profile-luminance-example": "Example file not created/opened",
                "profile-luminance-load": "Luminance file NOT loaded",
                "profile-save": ("Display file saved, but refresh FAILED"
                                 if saved_result is not None else "Display NOT saved"),
            }.get(action, "Display action failed")
            message = f"{operation}: {exc}"
            status.update(message)
            self.query_one("#profile-save-feedback", Static).update(f"[red]{message}[/red]")
            self.app.notify(message, title=operation, severity="error", timeout=10)
            if not isinstance(exc, (ValueError, TypeError, KeyError, StopIteration, OSError,
                                    RuntimeError, json.JSONDecodeError)):
                from .setup import _report_ui_exception
                _report_ui_exception(self.app, exc, phase=f"tui_profile_{action}")
