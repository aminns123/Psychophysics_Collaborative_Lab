"""Human branches with injected display/input; no claim of physical validation."""

import asyncio
import csv
from dataclasses import asdict, replace
import json
from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox, Select, Static

from psychophysics_lab.config.local import config_root, save_profile
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.researcher_override import authorize_researcher_override
from psychophysics_lab.core.runner import run_request
from psychophysics_lab.data.workspace import load_workspace_state, request_from_workspace_state
from psychophysics_lab.experiments._internal.registry import get_experiment
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup(tmp_path):
    reference = load_monitor_profiles(ROOT)["legacy_reference_display"]
    profile = save_profile(config_root(ROOT), replace(
        reference, id="override_display", origin="local",
        display_binding={"index": 0, "x": 0, "y": 0, "width": 1920, "height": 1080},
        expected_resolution_px=(1920, 1080), qualified_experiments=(),
        geometry_status="unverified", calibration_status="unverified",
        timing_status="unverified", luminance_calibration=(), calibration_method="",
    ))
    spec = get_experiment("contrast_sensitivity")
    request = SetupRequest("H001", "new", spec.id, profile.id,
                           spec.field_defaults() | {"max_trials": 4}, str(tmp_path / "human"))
    return request, spec, profile


def authorize(setup):
    return authorize_researcher_override(*setup, acknowledged=True)


def test_default_strict_and_explicit_override_does_not_verify_profile(setup):
    request, spec, profile = setup
    before = profile.to_dict()
    with pytest.raises(ValueError, match="Human acquisition blocked"):
        validate_setup(request, spec, profile)
    with pytest.raises(ValueError, match="Confirm"):
        authorize_researcher_override(request, spec, profile)
    approved = authorize(setup)
    assert set(approved.researcher_override.waived_requirements) == {
        "protocol", "geometry", "luminance", "timing"}
    assert validate_setup(approved, spec, profile) == approved
    assert profile.to_dict() == before == load_monitor_profiles(ROOT)[profile.id].to_dict()
    assert not profile.has_verified_luminance_mapping


@pytest.mark.parametrize("change", ["participant", "values", "profile", "protocol", "stimulus"])
def test_decision_is_bound_to_reviewed_setup(setup, change):
    request, spec, profile = setup
    approved = authorize(setup)
    if change == "participant":
        approved = replace(approved, participant_id="H002")
    elif change == "values":
        approved = replace(approved, experiment_values=approved.experiment_values | {"max_trials": 5})
    elif change == "profile":
        profile = replace(profile, calibration_notes="new revision")
    elif change == "protocol":
        spec = replace(spec, acquisition_block_reason="New protocol qualification requirement")
    else:
        import copy
        snapshots = copy.deepcopy(approved.stimulus_snapshots)
        snapshots["fixation"]["document"]["parameters"]["background"] = .4
        approved = replace(approved, stimulus_snapshots=snapshots)
    with pytest.raises(ValueError, match="changed|snapshot|parameters"):
        validate_setup(approved, spec, profile)


@pytest.mark.parametrize("identity", ["synthetic_preview", "synthetic_7", "presentation_test_7"])
def test_reserved_identity_cannot_become_human_data(setup, identity):
    request, spec, profile = setup
    with pytest.raises(ValueError, match="human participant"):
        authorize_researcher_override(replace(request, participant_id=identity), spec, profile, acknowledged=True)


@pytest.mark.parametrize("fault", ["binding", "resolution", "geometry", "range", "sampling", "response_keys"])
def test_override_keeps_operational_validity_checks(setup, fault):
    request, spec, profile = setup
    if fault == "binding":
        profile = replace(profile, display_binding=None)
    elif fault == "resolution":
        profile = replace(profile, expected_resolution_px=None)
    elif fault == "geometry":
        profile = replace(profile, viewing_distance_m=0)
    elif fault == "range":
        request = replace(request, experiment_values=request.experiment_values | {"background_intensity": 2})
    elif fault == "sampling":
        request = replace(request, experiment_values=request.experiment_values | {"frequencies_cpd": "999"})
    else:
        request = replace(request, experiment_values=request.experiment_values | {"response_keys": "F,F"})
    with pytest.raises(ValueError):
        authorize_researcher_override(request, spec, profile, acknowledged=True)


def test_override_cannot_be_a_boolean_or_used_for_other_modes(setup):
    request, spec, profile = setup
    with pytest.raises(ValueError, match="reviewed decision"):
        validate_setup(replace(request, researcher_override=True), spec, profile)
    approved = authorize(setup)
    with pytest.raises(ValueError, match="only to human"):
        validate_setup(approved, spec, profile, mode="simulation")
    from psychophysics_lab.core.presentation_testing import validate_presentation
    with pytest.raises(ValueError, match="only to human"):
        validate_presentation(approved, spec, profile)


def inject_display(monkeypatch, outcome="complete"):
    from psychophysics_lab.core.presentation import Response
    from psychophysics_lab.core.trial_execution import VirtualPresentation
    displays = []

    class Display:
        synthetic = False

        def __init__(self, profile, responses, **kwargs):
            self.metadata = {"physical_display_used": True, "test_fixture": True,
                             "photon_timing_verified": False}
            self.delegate = VirtualPresentation(Response(0, responses.keys[0], .2))
            self.prepared = 0
            self.closed = False
            displays.append(self)

        def prepare(self, *args):
            from psychophysics_lab.researcher import SessionTimeline
            self.prepared += int(not isinstance(args[0], SessionTimeline))
            if self.prepared == 2 and outcome != "complete":
                if outcome == "abort":
                    from psychophysics_lab.researcher import ParticipantAbort
                    raise ParticipantAbort("injected Escape")
                raise RuntimeError("injected display failure")
            self.delegate.prepare(*args)

        def play_phase(self, *args, **kwargs):
            return self.delegate.play_phase(*args, **kwargs)

        def close(self):
            self.closed = True

    monkeypatch.setattr("psychophysics_lab.core.presentation.Presentation", Display)
    monkeypatch.setattr("psychophysics_lab.core.display.preflight_fullscreen_display", lambda p: None)
    return displays


@pytest.mark.parametrize("outcome", ["complete", "abort", "error"])
def test_override_runs_real_human_branch_and_ordinary_storage(setup, monkeypatch, outcome):
    request, spec, profile = setup
    approved = authorize(setup)
    displays = inject_display(monkeypatch, outcome)
    if outcome == "error":
        with pytest.raises(RuntimeError, match="injected display failure"):
            run_request(approved, repo_root=ROOT)
        directory = next(Path(request.data_root).rglob("manifest.json")).parent
    else:
        result = run_request(approved, repo_root=ROOT)
        directory = result.run_directory
        assert result.status == ("max_trials_reached" if outcome == "complete" else "aborted_by_user")
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["data_kind"] == "human" and "simulation" not in manifest
    assert manifest["status"] == {"complete": "max_trials_reached", "abort": "aborted_by_user", "error": "error"}[outcome]
    assert directory.is_relative_to(Path(request.data_root) / "H001" / spec.id / profile.id)
    assert manifest["monitor_profile"] == json.loads(json.dumps(profile.to_dict()))
    assert not manifest["calibration"]["has_verified_luminance_mapping"]
    assert manifest["researcher_override"]["confirmed_utc"] == approved.researcher_override.confirmed_utc
    assert {r["key"] for r in manifest["researcher_override"]["requirements"]} == set(approved.researcher_override.waived_requirements)
    assert all(not r["passed"] for r in manifest["researcher_override"]["requirements"])
    with (directory / "trials.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == (4 if outcome == "complete" else 1)
    assert all(not row["response_key"].startswith("SIMULATED_") for row in rows)
    assert json.loads((directory / "trial_context.json").read_text())["data_kind"] == "human"
    assert not (directory / "SYNTHETIC_DATA.json").exists()
    assert not (directory / "UNCALIBRATED_TEST_DATA.json").exists()
    assert displays and all(display.closed for display in displays)
    checks = validate_run(directory)
    assert all(check.passed for check in checks), [check for check in checks if not check.passed]
    state = load_workspace_state(Path(request.data_root))
    restored = request_from_workspace_state(state)
    assert restored.researcher_override is None
    assert restored.participant_id == "H001"
    with pytest.raises(ValueError, match="Human acquisition blocked"):
        validate_setup(restored, spec, profile)
    assert load_monitor_profiles(ROOT)[profile.id].to_dict() == profile.to_dict()


def test_runner_hardware_failure_allocates_no_run(setup, monkeypatch):
    request, _, _ = setup
    approved = authorize(setup)
    def fail(profile):
        raise ValueError("Bound monitor is missing")
    monkeypatch.setattr("psychophysics_lab.core.display.preflight_fullscreen_display", fail)
    with pytest.raises(ValueError, match="Bound monitor"):
        run_request(approved, repo_root=ROOT)
    assert not list(Path(request.data_root).rglob("manifest.json"))


@pytest.mark.parametrize("fault", [None, "hardware", "hardware_runtime", "profile"])
def test_tui_confirmation_cancel_and_launch(setup, tmp_path, monkeypatch, fault):
    from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen
    from psychophysics_lab.ui.researcher_override import ResearcherOverrideScreen
    request, spec, profile = setup
    calls = []
    def hardware(p):
        calls.append(p.id)
        if fault == "hardware":
            raise ValueError("Connected display mode changed")
        if fault == "hardware_runtime":
            raise RuntimeError("Display driver changed")
    monkeypatch.setattr("psychophysics_lab.core.display.preflight_fullscreen_display", hardware)

    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT, data_root=Path(request.data_root))
        async with app.run_test(size=(80, 24)) as pilot:
            review = ReviewScreen(request=request)
            await app.push_screen(review)
            await pilot.pause()
            assert not review.query_one("#run-researcher-override", Button).display
            review.query_one("#review-run-intent", Select).value = "human"
            await pilot.pause()
            assert review.query_one("#run-researcher-override", Button).display
            review.query_one("#run", Button).press()
            await pilot.pause()
            assert app.screen is review and not calls
            app.screen.query_one("#run-researcher-override", Button).focus()
            await pilot.pause(0.6)
            assert await pilot.click("#run-researcher-override")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, ResearcherOverrideScreen)
            modal.query_one("#override-launch", Button).press()
            await pilot.pause()
            assert "Confirm" in str(modal.query_one("#override-feedback", Static).render())
            modal.query_one("#override-cancel", Button).press()
            await pilot.pause()
            assert app.screen is review and review.request.researcher_override is None
            review.query_one("#run-researcher-override", Button).press()
            await pilot.pause()
            modal = app.screen
            assert not modal.query_one("#override-ack", Checkbox).value
            modal.query_one("#override-ack", Checkbox).value = True
            if fault == "profile":
                save_profile(config_root(ROOT), replace(profile, calibration_notes="changed"),
                             expected_revision=profile.revision)
            modal.query_one("#override-launch", Button).press()
            await pilot.pause()
            if fault:
                assert app.screen is modal
                assert "changed" in str(modal.query_one("#override-feedback", Static).render())
        if fault:
            assert app.return_value is None
        else:
            assert isinstance(app.return_value, SetupRequest)
            assert app.return_value.researcher_override is not None
            assert app.return_value.participant_id == "H001"
            assert app.return_value.data_root == request.data_root
            assert validate_setup(app.return_value, spec, profile) == app.return_value
    asyncio.run(scenario())
    assert calls == ([] if fault == "profile" else [profile.id])


def test_saved_settings_never_restore_override(setup):
    approved = authorize(setup)
    restored = request_from_workspace_state({"last_request": asdict(approved)})
    assert restored.researcher_override is None


def test_experiment_profile_qualification_can_be_waived_without_declaring_it(setup):
    request, spec, profile = setup
    spec = replace(spec, compatible_monitor_profiles=("another_display",))
    approved = authorize((request, spec, profile))
    assert "qualification" in approved.researcher_override.waived_requirements
    assert not profile.qualified_experiments
    assert validate_setup(approved, spec, profile) == approved


def test_synthetic_photometry_stays_synthetic_and_unverified(setup):
    from psychophysics_lab.config.models import LuminanceCalibrationPoint, photometry_is_test_data
    request, spec, profile = setup
    profile = replace(profile, calibration_method="fake test meter", luminance_data_kind="synthetic",
                      luminance_calibration=(LuminanceCalibrationPoint(0, 0), LuminanceCalibrationPoint(1, 100)))
    approved = authorize((request, spec, profile))
    assert "luminance" in approved.researcher_override.waived_requirements
    assert photometry_is_test_data(profile) and not profile.has_verified_luminance_mapping




def test_early_configuration_failure_keeps_deliberate_decision(setup, monkeypatch):
    from psychophysics_lab.core import runner
    approved = authorize(setup)
    monkeypatch.setattr("psychophysics_lab.core.display.preflight_fullscreen_display", lambda p: None)
    def fail(**kwargs):
        raise RuntimeError("injected manifest construction failure")
    monkeypatch.setattr(runner, "_manifest_payload", fail)
    with pytest.raises(RuntimeError, match="manifest construction"):
        run_request(approved, repo_root=ROOT)
    manifest_path = next(Path(approved.data_root).rglob("manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    assert manifest["status"] == "error" and manifest["data_kind"] == "human"
    assert manifest["researcher_override"]["review_sha256"] == approved.researcher_override.review_sha256


@pytest.mark.parametrize("identity", [
    "orientation_task", "line_position_baseline", "line_position_flanker",
    "ellipse_major_axis", "ellipse_centre",
])
def test_other_registered_procedure_gates_use_same_decision(setup, monkeypatch, identity):
    request, _, profile = setup
    spec = get_experiment(identity)
    values = spec.field_defaults()
    if spec.historical:
        values.update(reference_width_px=1920, reference_height_px=1080,
                      start_contrast=.1, trials_per_condition=1)
        if identity == "ellipse_2d":
            values.update(condition_positions_deg="[0.25, 0.5]", decision_scene="fixation_only_development")
    elif identity == "orientation_task":
        values["trial_count"] = 2
    else:
        values["max_trials"] = 2
        if identity.startswith("line_"):
            values["probe_vertical_offset_deg"] = .5
            if identity.endswith("flanker"):
                values["flanker_cpd"] = 2.
        elif identity.startswith("ellipse_"):
            values["ring_increment"] = .1
    request = replace(request, experiment_id=identity, experiment_values=values)
    with pytest.raises(ValueError, match="Human acquisition blocked"):
        validate_setup(request, spec, profile)
    approved = authorize((request, spec, profile))
    displays = inject_display(monkeypatch)
    result = run_request(approved, repo_root=ROOT)
    assert result.accepted_trials > 0 and result.status in {"completed", "max_trials_reached"}
    assert json.loads(result.manifest_file.read_text())["data_kind"] == "human"
    assert displays and all(display.closed for display in displays)
    assert all(check.passed for check in validate_run(result.run_directory))
