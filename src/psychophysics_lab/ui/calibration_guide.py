"""Persistent, interactive help for human-acquisition readiness.

This panel explains real blockers without changing scientific settings,
silently certifying laboratory calibration or allowing acquisition to bypass
the production preflight. It closes only when the researcher asks.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..config.readiness import profile_readiness
from psychophysics_lab.experiments._internal.registry import get_experiment


GUIDE_STEPS = (
    ("display", "Bind the monitor"),
    ("geometry", "Size and ruler"),
    ("spatial", "Spatial frequency"),
    ("luminance", "Luminance"),
    ("timing", "Timing"),
    ("contrast", "Contrast and adaptive rules"),
    ("qualification", "Experiment qualification"),
)

STAGE_HELP = {
    "display": (
        "[b]You need:[/b] the actual monitor, its active image width and height "
        "in METRES (for example 0.340, 0.210), eye-to-screen viewing distance "
        "in METRES (for example 0.500), Windows fullscreen pixel width/height "
        "and refresh in Hz.\n"
        "[b]How:[/b] Bind/edit monitor profile -> Detect connected displays "
        "-> select the actual screen -> Use detected resolution/refresh -> "
        "measure width/height with a ruler -> Save local revision. "
        "Detected pixels never supply physical size or eye distance."
    ),
    "geometry": (
        "[b]You need:[/b] a known physical length and your ruler measurement "
        "in MILLIMETRES.\n"
        "[b]Example:[/b] a centred 5 degree bar at viewing distance 0.5 m "
        "should be about 43.7 mm (not a measurement of your hardware).\n"
        "[b]How:[/b] Calibrate -> Size/ruler bar -> Visual angle (degrees) "
        "-> 5 -> Launch -> measure the bar -> type the actual mm in "
        "'Measured bar length' -> Record Measurement. Check recorded percent "
        "error. Change of monitor profile revision makes older checks stale."
    ),
    "spatial": (
        "[b]You need:[/b] requested grating frequency in cycles/degree "
        "(cpd), orientation, angular patch width and physical viewing distance.\n"
        "[b]Example:[/b] 4 cpd across 5 degrees is nominally 20 cycles "
        "across that extent.\n"
        "[b]How:[/b] Calibrate -> Spatial sine grating -> cpd 2, 4, 8 "
        "in turn; inspect horizontal and vertical orientations and the "
        "patch extent. Check against pixel sampling/Nyquist. Presenting the "
        "diagnostic does NOT independently certify optical frequency. On return, "
        "record whether the pattern was visually consistent and any abnormalities. "
        "One complete light–dark period is a cycle; bright maxima depend on phase and edges."
    ),
    "luminance": (
        "[b]You need:[/b] a real photometer, known digital grayscale "
        "commands (0 to 1), measured luminance readings in cd/m², meter "
        "model/method, date and measurement notes.\n"
        "[b]Example ONLY:[/b] a command of 0.50 and photometer reading "
        "100 cd/m² would be one JSON pair. Do not use the example reading "
        "as your monitor's measurement.\n"
        "[b]Three supported routes:[/b] (1) Import a measured JSON file "
        "in Bind/edit monitor profile; (2) Calibrate -> Start interactive "
        "luminance measurement: 6° centred square on black, starts at command "
        "1.0, Left/Right decreases/increases toward the experiment background, "
        "type meter cd/m² and press Enter for EACH reading (repeat at the same "
        "command to average), Esc to finish; (3) Open pilot/test JSON to edit "
        "the session means or an empty example when no meter is available. "
        "Complete real method/date/notes, import JSON into the profile draft, "
        "inspect and Save local revision. Measurements and means remain "
        "UNVERIFIED until independently reviewed."
    ),
    "timing": (
        "[b]You need:[/b] intended flicker frequency in Hz, nominal "
        "refresh in Hz and, for physical timing claims, photodiode timing "
        "data (including instrument, method and uncertainty).\n"
        "[b]Example:[/b] 7.5 Hz binary flicker at 60 Hz nominal refresh "
        "can use 4 on frames + 4 off frames.\n"
        "[b]How:[/b] Calibrate -> Binary flicker or frame-sampled sine -> "
        "Temporal frequency (Hz) -> Launch. Review software frame logs. "
        "A photodiode is required for emitted light timing; only after "
        "physical review should you manually mark timing verified "
        "and record its provenance/notes in the monitor profile."
    ),
    "contrast": (
        "[b]You need:[/b] the selected experiment's digital background and "
        "initial stimulus modulation, plus its adaptive step rule. Digital "
        "commands are NOT measured luminance or calibrated optical contrast.\n"
        "[b]Example:[/b] the current CSF grating uses peak-to-peak digital "
        "contrast C: background b=0.25 permits C <= 0.50 before clipping. "
        "A line probe instead uses an increment above its background; a "
        "flanker or ring elsewhere need not reduce its local headroom. "
        "These are different mathematical definitions, not equivalent units.\n"
        "[b]How:[/b] Open Experiment -> configure the chosen experiment "
        "-> adjust Background intensity, Starting contrast (or probe "
        "intensity for line tasks), and adaptive step parameters. "
        "Review any displayed numerical constraint and measured optical "
        "calibration separately. A valid starting value does not guarantee "
        "future adaptive steps stay within range."
    ),
    "qualification": (
        "[b]You need:[/b] a completed laboratory acceptance record "
        "for the exact monitor/profile revision AND experiment, covering "
        "required geometry, photometry, timing, response mapping and "
        "protocol-specific stimulus/contrast checks.\n"
        "[b]How:[/b] Bind/edit monitor profile -> Explicitly qualified "
        "experiments. Enter experiment IDs separated by commas "
        "(e.g. contrast_sensitivity), only when the laboratory has "
        "reviewed the evidence. Save a local revision; Review again. "
        "This is a manual declaration, not automatic certification."
    ),
}

def guide_statuses(readiness: dict, profile, values: dict) -> tuple[tuple[str, str], ...]:
    """Return semantic statuses, never equating completed software checks with certification."""
    bound = bool(readiness.get("bound"))
    resolution = profile.expected_resolution_px is not None
    geometry = readiness.get("geometry_check")
    spatial = readiness.get("spatial_check")
    spatial_reviewed = (readiness.get("calibration_stages") or {}).get("spatial", {}).get("completed", False)
    timing = readiness.get("temporal_check")
    photo = readiness.get("photometrically_calibrated")
    qualified = readiness.get("experiment_qualified")
    contrast_risk = any("Grating command may clip" in str(reason)
                        for reason in readiness.get("human_blockers", ()))
    return (
        ("bound" if bound and resolution else "missing",
         "Bound monitor and expected resolution" if bound and resolution
         else "Bind physical monitor and confirm expected resolution"),
        ("recorded" if geometry else "missing",
         "Ruler measurement recorded for this revision; review its error" if geometry
         else "No measured ruler result for this profile revision"),
        ("recorded" if spatial_reviewed else "partial" if spatial else "missing",
         "Researcher-reviewed visual consistency; NOT physical certification" if spatial_reviewed
         else "Spatial diagnostic displayed; awaiting a consistent researcher observation" if spatial
         else "No spatial diagnostic found for this profile revision"),
        ("verified" if photo else "missing",
         "Verified luminance mapping declared in profile" if photo
         else "No verified measured luminance-command table"),
        ("verified" if profile.timing_status == "verified" else
         "partial" if timing else "missing",
         "Physical timing verification declared" if profile.timing_status == "verified"
         else "Software timing test recorded; photon timing not verified" if timing
         else "No recorded timing diagnostic or physical verification"),
        ("missing" if contrast_risk else "partial",
         "Initial grating command may clip: edit protocol settings" if contrast_risk
         else "Initial digital range passes guard; later staircase steps need review"),
        ("verified" if qualified else "missing",
         "Experiment/profile explicitly qualified" if qualified
         else "Experiment/profile combination NOT qualified by the laboratory"),
    )


class CalibrationGuideScreen(ModalScreen[None]):
    """Bottom-right, dismissible guidance panel with Next/Previous navigation."""

    BINDINGS = [
        ("left", "previous_stage", "Previous"),
        ("right", "next_stage", "Next"),
        ("escape", "close_guide", "Close"),
    ]

    CSS = """
    CalibrationGuideScreen {
        align: right bottom;
        background: transparent;
    }
    #calibration-guide-panel {
        width: 82;
        max-width: 96%;
        height: 25;
        max-height: 88%;
        border: round $primary;
        background: $panel;
        padding: 1;
        margin: 0 1 1 0;
    }
    #calibration-guide-panel.guide-done { border: round green; }
    #calibration-guide-panel.guide-warning { border: round yellow; }
    #calibration-guide-panel.guide-blocked { border: round red; }
    #guide-top, #guide-buttons { height: 3; }
    #guide-heading { width: 1fr; text-style: bold; }
    #guide-close { width: 12; }
    #guide-progress { height: 2; color: $text-muted; }
    #guide-body-scroll { height: 1fr; }
    #guide-buttons Button { width: 1fr; min-width: 0; }
    """

    def __init__(self, request, *, initial_stage: str | None = None):
        super().__init__()
        self.request = request
        self.stage_index = next(
            (i for i, (key, _) in enumerate(GUIDE_STEPS) if key == initial_stage), 0
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="calibration-guide-panel"):
            with Horizontal(id="guide-top"):
                yield Static("Calibration help", id="guide-heading")
                yield Button("× Close", id="guide-close")
            yield Static("", id="guide-progress")
            with VerticalScroll(id="guide-body-scroll"):
                yield Static("", id="guide-content")
            with Horizontal(id="guide-buttons"):
                yield Button("← Previous", id="guide-prev")
                yield Button("Open section ↗", id="guide-open", variant="primary")
                yield Button("Next →", id="guide-next")

    def on_mount(self) -> None:
        self._render_stage()

    def _render_stage(self) -> None:
        spec = get_experiment(self.request.experiment_id)
        profile = self.app.monitor_profiles[self.request.monitor_profile_id]
        ready = profile_readiness(spec, profile,
                                  repo_root=self.app.repo_root,
                                  values=self.request.experiment_values)
        statuses = guide_statuses(ready, profile, self.request.experiment_values)
        key, name = GUIDE_STEPS[self.stage_index]
        state, reason = statuses[self.stage_index]
        color = {"verified": "green", "recorded": "green", "partial": "yellow",
                 "bound": "green", "missing": "red"}[state]
        status_label = {"verified": "DECLARED/READY", "recorded": "TEST RECORDED",
                        "partial": "REVIEW NEEDED", "bound": "BOUND",
                        "missing": "INCOMPLETE"}[state]
        panel = self.query_one("#calibration-guide-panel")
        panel.remove_class("guide-done", "guide-warning", "guide-blocked")
        panel.add_class("guide-done" if state in {"verified", "recorded", "bound"}
                        else "guide-warning" if state == "partial"
                        else "guide-blocked")
        self.query_one("#guide-heading", Static).update(
            f"Calibration guide — {name}")
        self.query_one("#guide-progress", Static).update(
            f"Step {self.stage_index + 1}/{len(GUIDE_STEPS)} · "
            f"[{color}]{status_label}[/{color}]  ·  ←/→ to browse · Esc to close"
        )
        flow = " → ".join(
            f"[{('green' if x[0] in {'verified', 'recorded', 'bound'} else 'yellow' if x[0] == 'partial' else 'red')}]"
            f"{i + 1}[/{('green' if x[0] in {'verified', 'recorded', 'bound'} else 'yellow' if x[0] == 'partial' else 'red')}]"
            for i, x in enumerate(statuses)
        )
        text = (
            f"[b]Profile[/b] {profile.id}, revision {profile.revision}\n"
            f"[b]Progress[/b] {flow}\n"
            f"[b]Experiment ID[/b] {spec.id}\n\n"
            f"[{color}][b]{reason}[/b][/{color}]\n\n"
            f"{STAGE_HELP[key]}\n\n"
            "[dim]A green recorded-test indicator is NOT proof of physical "
            "luminance, spatial accuracy or photon timing. Human acquisition "
            "remains subject to independent review/qualification checks.[/dim]"
        )
        self.query_one("#guide-content", Static).update(text)
        self.query_one("#guide-prev", Button).disabled = self.stage_index == 0
        self.query_one("#guide-next", Button).disabled = self.stage_index == len(GUIDE_STEPS) - 1
        self.query_one("#guide-open", Button).label = (
            "Edit experiment ↗" if key == "contrast"
            else "Edit monitor ↗" if key in {"luminance", "qualification", "display"}
            else "Go to Calibrate ↗"
        )

    def action_previous_stage(self) -> None:
        if self.stage_index > 0:
            self.stage_index -= 1
            self._render_stage()

    def action_next_stage(self) -> None:
        if self.stage_index + 1 < len(GUIDE_STEPS):
            self.stage_index += 1
            self._render_stage()

    def action_close_guide(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        key = event.button.id
        if key == "guide-close":
            self.action_close_guide()
        elif key == "guide-prev":
            self.action_previous_stage()
        elif key == "guide-next":
            self.action_next_stage()
        elif key == "guide-open":
            self._go_to_section()

    def _go_to_section(self) -> None:
        key, _ = GUIDE_STEPS[self.stage_index]
        profile_id = self.request.monitor_profile_id
        self.app.pop_screen()
        from .setup import ReviewScreen, DisplayCheckScreen, ExperimentParametersScreen
        if isinstance(self.app.screen, ReviewScreen):
            review=self.app.screen
            if key == "contrast":
                # This step edits the experiment, not the display. The generic
                # "setup" readiness fallback below would otherwise open the
                # Calibrate display screen and conceal the existing draft.
                self.app.config_drafts[(
                    self.request.participant_id, self.request.experiment_id,
                    self.request.monitor_profile_id
                )] = dict(self.request.experiment_values)
                review._edit_experiment_inputs()
                return
            mapped={"display":"binding","qualification":"qualification"}.get(key,key)
            if any(row['key']==mapped and row.get('action') for row in review.readiness_report['requirements']):
                review.resolve_requirement(mapped)
                return
            # Reuse the direct calibration route, including its fullscreen
            # diagnostic restart state, for guide-only stages such as Spatial.
            review.resolve_requirement("setup")
            from ..config.local import save_preferences
            save_preferences(self.app.local_config_root,calibration_active_stage={'display':'bind'}.get(key,key))
            return
        if key == "contrast":
            # A guide opened independently of Review should still land on
            # setup, but never turn an experiment-edit request into Calibrate.
            if not isinstance(self.app.screen, ExperimentParametersScreen):
                self.app.open_hub_page("setup")
            return
        self.app.display_guide_target_profile_id = profile_id
        # The cached Calibrate form must not override this explicit guide
        # selection when DisplayCheckScreen.on_mount restores its input draft.
        self.app.display_draft["geometry-monitor"] = profile_id
        self.app.open_hub_page("display")
        if key in {"display", "luminance", "qualification"}:
            from .profiles import ProfileScreen
            profile = self.app.monitor_profiles[profile_id]
            target_field = {"display": "profile-binding",
                            "luminance": "profile-luminance-example",
                            "qualification": "profile-qualified_experiments"}[key]
            self.app.push_screen(ProfileScreen(
                profile=profile, focus_field=target_field))
