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
from ..experiments.registry import get_experiment


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
        "Select the actual physical monitor, confirm its Windows framebuffer "
        "resolution and refresh rate, and save the local profile. A saved "
        "unbound draft is not enough for human acquisition."
    ),
    "geometry": (
        "In Calibrate, display a known bar at your actual viewing distance. "
        "Measure its physical length with a ruler, then Record Measurement. "
        "A saved result for the CURRENT profile revision is evidence of a "
        "geometric check; review its error before accepting it. A new revision "
        "invalidates the earlier test's direct applicability."
    ),
    "spatial": (
        "Run the Spatial sine grating diagnostic at one or more known "
        "cycles/degree, in horizontal and vertical orientations. Look for "
        "clipping/aliasing and verify realised patch size. A successful "
        "software display test alone does not measure the actual emitted "
        "spatial frequency or physical optical transfer function."
    ),
    "luminance": (
        "The digital display commands are NOT luminance in cd/m². Measure "
        "command-to-luminance pairs with a photometer, including the "
        "background and usable grating extrema. In Bind/edit monitor profile, "
        "enter the measured calibration table and provenance. Only mark "
        "photometry verified after those measurements; do not guess gamma, "
        "luminance or uncertainty from the operating system."
    ),
    "timing": (
        "Calibrate offers binary flicker and frame-sampled modulation tests. "
        "These exercise the software and nominal refresh timing. For claims "
        "about photon onset, dropped frames or accurate exposure durations, "
        "record suitable photodiode/physical timing measurements. The OS "
        "refresh rate alone is insufficient."
    ),
    "contrast": (
        "Review 'Background digital screen intensity', 'Starting probe "
        "digital intensity' and the adaptive up/down factors in Configure "
        "Experiment. The current box=False shader uses "
        "RGB = background + envelope*C_disp*sin(phase)/2. "
        "Production acquisition rejects out-of-range RGB commands rather "
        "than silently clamping them. A safe starting value does not "
        "guarantee all later upward staircase steps stay within range. "
        "Any changed contrast protocol needs scientific review."
    ),
    "qualification": (
        "After assessing geometry, spatial pattern, photometry, timing, "
        "response mapping and protocol-specific contrast rules, explicitly "
        "record the selected experiment ID in the local monitor profile's "
        "'Explicitly qualified experiments' field. This is a researcher/lab "
        "declaration, NOT an automatic consequence of pressing Save. "
        "Do not mark a study qualified simply to silence a warning."
    ),
}


def guide_statuses(readiness: dict, profile, values: dict) -> tuple[tuple[str, str], ...]:
    """Return semantic statuses, never equating completed software checks with certification."""
    bound = bool(readiness.get("bound"))
    resolution = profile.expected_resolution_px is not None
    geometry = readiness.get("geometry_check")
    spatial = readiness.get("spatial_check")
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
        ("recorded" if spatial else "missing",
         "Spatial diagnostic displayed; physical frequency still needs review" if spatial
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
            f"[b]Progress[/b] {flow}\n\n"
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
        if key == "contrast":
            # Review is normally above ExperimentConfigScreen. Return to
            # editable contrast/adaptive controls with draft values intact.
            from .setup import ReviewScreen, ExperimentConfigScreen
            if isinstance(self.app.screen, ReviewScreen):
                self.app.pop_screen()
            if not isinstance(self.app.screen, ExperimentConfigScreen):
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
            self.app.push_screen(ProfileScreen(profile=profile))
