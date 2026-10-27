"""Researcher workflow boundaries; window/input are injected, never hardware claims."""

import asyncio
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual.widgets import Button, Input, Select

from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.presentation_testing import (
    PresentationTestRequest,
    run_presentation_test,
)
from psychophysics_lab.experiments._internal.registry import get_experiment
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "identity",
    [
        "contrast_sensitivity",
        "line_position_baseline",
        "line_position_flanker",
        "ellipse_major_axis",
        "ellipse_centre",
        "orientation_task",
        "csf_escape",
    ],
)
def test_real_presentation_mode_isolated_and_bounded_without_qualifying_acquisition(
    tmp_path, monkeypatch, identity
):
    abort = identity == "csf_escape"
    identity = "contrast_sensitivity" if abort else identity
    from psychophysics_lab.core.presentation import Response
    from psychophysics_lab.core.trial_execution import VirtualPresentation

    # Exercise the physical branch, with an explicit software substitute for the
    # unavailable monitor and keyboard. No synthetic observer is supplied.
    class Display:
        synthetic = False

        def __init__(self, profile, responses, **kwargs):
            self.metadata = {
                "physical_display_used": True,
                "test_fixture": True,
                "photon_timing_verified": False,
            }
            self.prepared = 0
            self.delegate = VirtualPresentation(Response(0, responses.keys[0], 0.2))

        def prepare(self, *args):
            from psychophysics_lab.researcher import SessionTimeline
            self.prepared += int(not isinstance(args[0], SessionTimeline))
            if abort and self.prepared == 2:
                from psychophysics_lab.researcher import ParticipantAbort

                raise ParticipantAbort("injected Escape")
            self.delegate.prepare(*args)

        def play_phase(self, *args, **kwargs):
            return self.delegate.play_phase(*args, **kwargs)

        def close(self):
            pass

    monkeypatch.setattr("psychophysics_lab.core.presentation.Presentation", Display)
    monkeypatch.setattr(
        "psychophysics_lab.core.display.preflight_fullscreen_display", lambda p: None
    )
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(
        config_root(ROOT),
        replace(
            reference,
            id="workflow_display",
            origin="local",
            display_binding={"index": 0, "x": 0, "y": 0, "width": 1920, "height": 1080},
            expected_resolution_px=(1920, 1080),
        ),
    )
    spec = get_experiment(identity)
    values = {}
    if identity.startswith("line_"):
        values = {"probe_vertical_offset_deg": 0.5}
        if identity.endswith("flanker"):
            values["flanker_cpd"] = 2.0
    elif identity.startswith("ellipse_"):
        values = {"ring_increment": 0.1}
    values = spec.normalise_values(spec.field_defaults() | values)
    human = tmp_path / "human"
    human.mkdir()
    sentinel = human / "keep.txt"
    sentinel.write_text("KEEP")
    request = SetupRequest("H001", "new", identity, profile.id, values, str(human))
    result = run_presentation_test(
        PresentationTestRequest(request, trial_limit=2), repo_root=ROOT
    )
    assert result.status == ("aborted_by_user" if abort else "test_finished")
    assert result.accepted_trials == (1 if abort else 2)
    manifest = json.loads(result.manifest_file.read_text())
    assert manifest["data_kind"] == "uncalibrated_presentation_test"
    assert not manifest.get("simulation")
    assert not result.run_directory.is_relative_to(human)
    assert list(human.iterdir()) == [sentinel] and sentinel.read_text() == "KEEP"
    assert not (result.run_directory / "primary_thresholds.json").exists()
    assert not [
        (c.name, c.detail) for c in validate_run(result.run_directory) if not c.passed
    ]
    from psychophysics_lab.core.runner import run_request

    with pytest.raises(ValueError):
        run_request(request, repo_root=ROOT, data_root=human)


def test_bad_test_length_rejected():
    for value in (0, -1, True, 1001):
        with pytest.raises(ValueError):
            PresentationTestRequest(None, value)


def test_preview_renders_selected_values_and_opens_existing_image(
    tmp_path, monkeypatch
):
    from psychophysics_lab.ui import preview
    from psychophysics_lab.stimuli.registry import get_stimulus
    from psychophysics_lab.config.stimulus_parameters import document_for

    spec = get_stimulus("teaching_gabor")
    values = document_for(spec)["parameters"] | {"contrast": 0.2}
    opened = []
    monkeypatch.setattr(
        preview, "open_preview", lambda path: opened.append((path, path.is_file()))
    )
    path = preview.show_stimulus_preview(spec.id, values, tmp_path)
    assert opened == [(path, True)] and path.suffix == ".png"


def test_preview_opener_refuses_non_image_files(tmp_path):
    from psychophysics_lab.ui.preview import open_preview

    file = tmp_path / "command.py"
    file.write_text("pass")
    with pytest.raises(ValueError):
        open_preview(file)


def test_plain_parameter_editor_previews_and_saves_without_changing_defaults(
    tmp_path, monkeypatch
):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ExperimentConfigScreen
    from psychophysics_lab.ui.stimulus_editor import StimulusValueEditor
    from psychophysics_lab.ui.stimulus_parameters import StimulusParametersPanel
    from psychophysics_lab.ui import preview

    shown = []
    monkeypatch.setattr(
        preview,
        "show_stimulus_preview",
        lambda identity, values, directory: shown.append(dict(values)),
    )

    async def check():
        spec = get_experiment("orientation_task")
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(110, 45)) as pilot:
            app.push_screen(
                ExperimentConfigScreen(
                    data_root=tmp_path,
                    participant_id="synthetic_preview",
                    session_mode="new",
                    experiment=spec,
                    monitor_profile_id="legacy_reference_display",
                    defaults=spec.field_defaults(),
                )
            )
            await pilot.pause()
            panel = app.screen.query_one(StimulusParametersPanel)
            original = dict(panel.current()["document"]["parameters"])
            panel.query_one("#stimulus-values-target", Button).press()
            await pilot.pause()
            editor = app.screen
            assert isinstance(editor, StimulusValueEditor)
            index = next(
                i
                for i, f in enumerate(panel.stimulus.parameters)
                if f.key == "orientation_deg"
            )
            editor.query_one(f"#stimulus-value-{index}", Input).value = "35"
            editor.query_one("#stimulus-values-preview", Button).press()
            await pilot.pause()
            assert shown[-1]["orientation_deg"] == 35
            assert panel.current()["document"]["parameters"] == original
            editor.query_one("#stimulus-value-name", Input).value = "angle35"
            editor.query_one("#stimulus-values-save", Button).press()
            await pilot.pause()
            assert panel.current()["document"]["parameters"]["orientation_deg"] == 35

    asyncio.run(check())


def test_viewer_failure_preserves_preview_and_reports_its_location(
    tmp_path, monkeypatch
):
    from psychophysics_lab.ui import preview
    from psychophysics_lab.stimuli.registry import get_stimulus
    from psychophysics_lab.config.stimulus_parameters import document_for

    spec = get_stimulus("teaching_gabor")

    def fail(path):
        raise OSError("no image viewer")

    monkeypatch.setattr(preview, "open_preview", fail)
    with pytest.raises(OSError, match="Preview saved to"):
        preview.show_stimulus_preview(
            spec.id, document_for(spec)["parameters"], tmp_path
        )
    assert len(list(tmp_path.glob("*.png"))) == 1


def test_preview_uses_the_platform_image_viewer_without_a_shell(tmp_path, monkeypatch):
    from psychophysics_lab.ui import preview

    path = tmp_path / "image with spaces.png"
    path.write_bytes(b"test fixture")
    opened = []
    if preview.os.name == "nt":
        monkeypatch.setattr(preview.os, "startfile", lambda path: opened.append(path))
        preview.open_preview(path)
        assert opened == [str(path.resolve())]
    else:
        monkeypatch.setattr(
            preview.subprocess,
            "Popen",
            lambda args, **kwargs: opened.append((args, kwargs)),
        )
        preview.open_preview(path)
        assert opened[0][0][-1] == str(path.resolve()) and not opened[0][1].get("shell")


def test_normal_review_and_test_confirmation_have_one_selected_action(
    tmp_path, monkeypatch
):
    from textual.widgets import Checkbox, Static
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
    from psychophysics_lab.ui.presentation_testing import PresentationTestScreen
    from psychophysics_lab.core import presentation_testing

    monkeypatch.setattr(
        presentation_testing, "validate_presentation", lambda request, *args: request
    )

    async def check():
        spec = get_experiment("contrast_sensitivity")
        request = SetupRequest(
            "synthetic_preview",
            "new",
            spec.id,
            "legacy_reference_display",
            spec.field_defaults(),
            str(tmp_path),
        )
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=tmp_path)
        async with app.run_test(size=(100, 40)) as pilot:
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            review = app.screen
            assert review.query_one("#run-presentation-test", Button).display
            assert not review.query_one("#run-simulation", Button).display
            assert not review.query_one("#run", Button).display
            review.query_one("#review-run-intent", Select).value = "simulation"
            await pilot.pause()
            assert review.query_one("#run-simulation", Button).display
            assert not review.query_one("#run-presentation-test", Button).display
            review.query_one("#review-run-intent", Select).value = "test"
            await pilot.pause()
            review.query_one("#run-presentation-test", Button).press()
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, PresentationTestScreen)
            assert modal.query_one("#presentation-trial-limit", Input).value == "8"
            modal.query_one("#presentation-ack", Checkbox).value = True
            modal.query_one("#presentation-trial-limit", Input).value = "0"
            modal.query_one("#presentation-launch", Button).press()
            await pilot.pause()
            assert app.screen is modal and "1 to 1000" in str(
                modal.query_one("#presentation-feedback", Static).render()
            )
            modal.query_one("#presentation-trial-limit", Input).value = "2"
            modal.query_one("#presentation-launch", Button).press()
            await pilot.pause()
        assert isinstance(app.return_value, PresentationTestRequest)
        assert app.return_value.trial_limit == 2
        assert app.return_value.request.experiment_values == spec.field_defaults()

    asyncio.run(check())
