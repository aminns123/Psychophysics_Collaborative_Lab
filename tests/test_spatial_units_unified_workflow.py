"""Physical frequency geometry and one-review human/virtual workflow (headless)."""
import asyncio
import math
from dataclasses import replace
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.experiments.contrast_sensitivity import (
    CSF_SPEC, resolved_condition_frequencies
)
from psychophysics_lab.stimuli.spatial_calibration import (
    resolve_spatial_geometry, validate_requested_cpd, angle_deg_at_pixel,
    shader_radians_for_cpd_at_centre,
)
from psychophysics_lab.ui.setup import PsyCoLabSetupApp, ReviewScreen, ExperimentConfigScreen
from psychophysics_lab.ui.unified_run import VirtualObserverOptionsScreen
from psychophysics_lab.core.simulation_request import SimulationLaunchRequest
from simulations.csf import DEFAULT_VALUES
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]


def test_frequency_units_preserve_period_and_legacy_semantics():
    assert resolved_condition_frequencies("2,8", "cycles_per_degree") == (2.,8.)
    assert resolved_condition_frequencies("0.5,0.125", "degrees_per_cycle") == (2.,8.)
    assert resolved_condition_frequencies("63,252", "legacy_shader_radians") == (63.,252.)
    assert CSF_SPEC.field_defaults()["condition_unit"] == "cycles_per_degree"
    assert CSF_SPEC.field_defaults()["condition_values"] == "2,8"
    assert CSF_SPEC.normalise_values({"condition_values":"63,252"})["condition_unit"] == "legacy_shader_radians"
    assert CSF_SPEC.normalise_values({"condition_values":"2,8",
                                      "condition_unit":"cycles_per_degree"})["condition_unit"] == "cycles_per_degree"


def test_pixel_pitch_and_cpd_to_grating_phase_both_axes():
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    geometry = resolve_spatial_geometry(profile, (1920,1080))
    assert geometry.pixel_pitch_m[0] == pytest.approx(.61/1920)
    assert geometry.pixel_pitch_m[1] == pytest.approx(.35/1080)
    assert geometry.pixels_per_degree_at_centre[0] != pytest.approx(
        geometry.pixels_per_degree_at_centre[1], rel=.0001
    )
    cpd = 4.
    for theta in (0., math.pi/2):
        size = 200
        phase = shader_radians_for_cpd_at_centre(cpd,size,geometry,theta)
        expected = 2*math.pi*cpd * size / geometry.pixels_per_degree_at_centre[
            0 if theta==0 else 1
        ]
        assert phase == pytest.approx(expected,rel=1e-12)
        assert phase/(2*math.pi) > 0
    pitch = geometry.pixel_pitch_m[0]
    angle = angle_deg_at_pixel(50,pitch,geometry.viewing_distance_m)
    expected = math.degrees(math.atan(50*pitch/geometry.viewing_distance_m))
    assert angle == pytest.approx(expected)
    validate_requested_cpd((2.,8.),geometry)
    with pytest.raises(ValueError,match="sampling limit"):
        validate_requested_cpd((500.,),geometry)


def test_preflight_rejects_unrenderable_physical_frequencies_when_resolution_known():
    p = replace(load_monitor_profiles(ROOT)["legacy_reference_display"],
                expected_resolution_px=(1920,1080))
    values = dict(DEFAULT_VALUES,
                  condition_unit="cycles_per_degree",condition_values="2,500",
                  number_conditions=2)
    request = SetupRequest("H001","new","contrast_sensitivity",
                           "legacy_reference_display",values)
    with pytest.raises(ValueError,match="sampling limit"):
        validate_setup(request, CSF_SPEC,p)


def test_virtual_pipeline_converts_degrees_per_cycle_to_physical_cpd(tmp_path):
    root = tmp_path / "synthetic_data"
    artifacts,_ = simulate(
        data_root=root,repo_root=ROOT,seed=11,
        values={"condition_unit":"degrees_per_cycle",
                "condition_values":"0.5,0.125",
                "number_conditions":2,
                "max_trials":80},
    )
    import json
    conditions=json.loads((artifacts.run_directory/"state"/"conditions.runtime.json").read_text())
    assert conditions["condition_list"]==[2.,8.]
    assert conditions["condition_unit"]=="cycles_per_degree"
    assert conditions["entered_condition_unit"]=="degrees_per_cycle"
    assert (artifacts.run_directory/"analysis"/"staircases.png").is_file()


def test_review_can_choose_real_or_virtual_with_one_condition_configuration(tmp_path,monkeypatch):
    from psychophysics_lab.ui.unified_run import VirtualObserverOptionsScreen
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    base = dict(DEFAULT_VALUES, condition_unit="cycles_per_degree",
                condition_values="2,8", number_conditions=2)
    checked = CSF_SPEC.normalise_values(base)
    request = SetupRequest("H001","new","contrast_sensitivity",profile.id,
                           checked, str(tmp_path/"external"))
    async def scenario():
        app = PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"external")
        captured=[]
        monkeypatch.setattr(app,"exit",lambda result=None: captured.append(result))
        async with app.run_test(size=(100,30)) as pilot:
            app.push_screen(ReviewScreen(request=request))
            await pilot.pause()
            screen=app.screen
            assert screen.query_one("#run",Button).label.plain=="Run human experiment"
            assert screen.query_one("#run-simulation",Button).label.plain=="Run simulation"
            screen.query_one("#run-simulation",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,VirtualObserverOptionsScreen)
            options=app.screen
            assert options.request.experiment_values==checked
            options.query_one("#virtual-observer-0-0",Input).value="0.06"
            options.query_one("#virtual-seeds-0",Input).value="61,62"
            options.query_one("#virtual-run",Button).press()
            await pilot.pause()
            assert len(captured)==1
            launched=captured[0]
            assert isinstance(launched,SimulationLaunchRequest)
            assert launched.experiment_values==checked
            assert launched.seeds==(61,62)
            assert launched.observer_parameters["threshold"]==pytest.approx(.06)
            assert not (tmp_path/"external").exists()
    asyncio.run(scenario())


def test_calibration_widget_is_non_photometric_and_numerically_meaningful(tmp_path):
    from psychophysics_lab.ui.setup import DisplayCheckScreen
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(100,30)) as pilot:
            app.query_one("#nav-display",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            warning=str(app.screen.query_one("#spatial-calibration-summary",Static).render())
            assert "resolution" in warning
    asyncio.run(scenario())
