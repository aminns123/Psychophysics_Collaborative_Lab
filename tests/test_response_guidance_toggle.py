"""Presentation-only response guidance; science and response mapping stay fixed."""
import asyncio
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Checkbox, Select

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.timeline import CollectResponse, Show
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen

from test_action_presentation import fake_presentation

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("visible", [True, False])
def test_response_prompt_toggle_affects_only_text_not_response_capture(monkeypatch, visible):
    display, _, handlers = fake_presentation(monkeypatch, key_time=.005, key="LEFT")
    display.show_response_instructions = visible

    # The real renderer sees both the explicit run instruction and the
    # response phase's study-specific help. Neither can leak when hidden.
    labels = []
    pyglet = sys.modules["pyglet"]
    pyglet.text.Label = lambda value, **kwargs: (
        labels.append(value) or SimpleNamespace(draw=lambda: None)
    )
    answer = CollectResponse(
        actions=("left", "right"), name="answer",
        instructions="Press LEFT or RIGHT",
    )
    recorded = {}
    response = display.play_phase(answer, recorded, instructions="F or J — press a response")
    assert response.key == "LEFT"
    assert response.alternative == 0
    assert recorded["software_onset_s"] == 0.
    assert labels == (["F or J — press a response"] if visible else [])
    assert not handlers


def test_hidden_response_guidance_keeps_other_explicit_show_phase_text(monkeypatch):
    display, _, _ = fake_presentation(monkeypatch, key_time=.005, key=None)
    display.show_response_instructions = False
    display.refresh_rate_hz = 60.
    display._rendered["cue"] = []
    labels = []
    sys.modules["pyglet"].text.Label = lambda value, **kwargs: (
        labels.append(value) or SimpleNamespace(draw=lambda: None)
    )
    phase = Show("cue", duration=20, instructions="Maintain fixation")
    assert display.play_phase(phase, {}) is None
    assert labels == ["Maintain fixation"]


def test_review_checkbox_is_presentation_only_and_survives_run_mode_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR", str(tmp_path / "config"))
    spec = get_experiment("contrast_sensitivity")
    values = spec.field_defaults()
    request = SetupRequest(
        "synthetic_preview", "new", spec.id, "legacy_reference_display",
        values, str(tmp_path / "data"),
    )
    assert request.show_response_instructions is True  # backward-compatible
    original_settings = dict(request.experiment_values)

    async def exercise():
        app = PsyCoLabSetupApp(
            repo_root=ROOT, data_root=tmp_path / "data", include_historical=True
        )
        async with app.run_test(size=(120, 50)) as pilot:
            await app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            screen = app.screen
            widget = screen.query_one("#review-show-response-instructions", Checkbox)
            assert widget.value is True
            widget.value = False
            await pilot.pause()
            assert screen.request.show_response_instructions is False
            assert screen.request.experiment_values == original_settings
            assert asdict(screen.request)["show_response_instructions"] is False

            screen.query_one("#review-run-intent", Select).value = "human"
            await pilot.pause()
            assert screen.request.show_response_instructions is False
            screen.query_one("#review-run-intent", Select).value = "test"
            await pilot.pause()
            assert screen.request.show_response_instructions is False

            widget.value = True
            await pilot.pause()
            assert screen.request.show_response_instructions is True

    asyncio.run(exercise())
