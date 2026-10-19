"""Current spatial geometry, frequency validation and synthetic workflow.

Retired shader-radian and historical CSF modules are deliberately not imported.
"""
import csv
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.experiments.contrast_sensitivity import (
    SPEC as CSF_SPEC, make_conditions, validate_monitor
)
from psychophysics_lab.stimuli.spatial_calibration import (
    resolve_spatial_geometry, validate_requested_cpd, angle_deg_at_pixel,
    shader_radians_for_cpd_at_centre
)
from psychophysics_lab.stimulus_library import ContrastSensitivityGrating
from simulations.run import simulate

ROOT = Path(__file__).resolve().parents[1]


def test_csf_independent_cpd_field_and_selected_conditions():
    settings = CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        "frequencies_cpd": "1.25,4,11",
        "staircases_per_condition": 2,
    })
    conditions = make_conditions(settings)
    assert len(conditions) == 6
    assert [c["frequency_cpd"] for c in conditions] == [1.25,1.25,4.,4.,11.,11.]
    assert all(c["repeat"] in (1,2) for c in conditions)
    assert next(f for f in CSF_SPEC.fields if f.key == "frequencies_cpd").units == "cycles/degree"


def test_pixel_pitch_and_cpd_to_grating_phase_both_axes():
    profile=load_monitor_profiles(ROOT)["legacy_reference_display"]
    geometry=resolve_spatial_geometry(profile,(1920,1080))
    assert geometry.pixel_pitch_m[0] == pytest.approx(.61/1920)
    assert geometry.pixel_pitch_m[1] == pytest.approx(.35/1080)
    assert geometry.pixels_per_degree_at_centre[0] != pytest.approx(
        geometry.pixels_per_degree_at_centre[1],rel=.0001)
    for theta in (0., math.pi/2):
        phase=shader_radians_for_cpd_at_centre(4.,200,geometry,theta)
        index=0 if theta==0 else 1
        assert phase == pytest.approx(2*math.pi*4*200/geometry.pixels_per_degree_at_centre[index])
    pitch=geometry.pixel_pitch_m[0]
    assert angle_deg_at_pixel(50,pitch,geometry.viewing_distance_m) == pytest.approx(
        math.degrees(math.atan(50*pitch/geometry.viewing_distance_m)))
    validate_requested_cpd((2.,8.),geometry)
    with pytest.raises(ValueError,match="sampling limit"):
        validate_requested_cpd((500.,),geometry)


def test_current_csf_preflight_rejects_frequency_above_nyquist():
    p=replace(load_monitor_profiles(ROOT)["legacy_reference_display"],
              expected_resolution_px=(1920,1080))
    values=CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        "frequencies_cpd":"2,31"
    })
    with pytest.raises(ValueError,match="sampling limit"):
        validate_monitor(values,p)


def test_virtual_pipeline_records_actual_selected_cpd_not_retired_shader_units(tmp_path):
    root=tmp_path/"synthetic_workspace"
    artifacts,_=simulate(
        data_root=root,repo_root=ROOT,seed=23,
        values={"frequencies_cpd":"1.5,7","staircases_per_condition":1,"max_trials":8},
        analyse=False,
    )
    assert artifacts.accepted_trials>0
    resolved=json.loads((artifacts.run_directory/"resolved_experiment.json").read_text())
    params=json.loads((artifacts.run_directory/"experiment_config.json").read_text())
    assert params and resolved
    with artifacts.trial_log_file.open(newline="",encoding="utf-8") as stream:
        rows=list(csv.DictReader(stream,delimiter="\t"))
    assert {float(r["stimulus_condition"]) for r in rows} <= {1.5,7.0}
    assert (artifacts.run_directory/"SYNTHETIC_DATA.json").exists()
    assert (artifacts.run_directory/"analysis").exists()


def test_selected_grating_uses_degree_coordinates_not_shader_radians():
    p={f.key:f.default for f in ContrastSensitivityGrating.PARAMETERS}
    p |= {"spatial_frequency_cpd":2., "sigma_deg":1., "background":.5,
          "contrast":.1}
    x=np.array([0.,.125,.25,.5])
    y=np.zeros_like(x)
    result=ContrastSensitivityGrating.render(p,x,y)
    expected=.5+.05*np.exp(-(x*x)/2)*np.sin(2*np.pi*2*x)
    assert np.allclose(result,expected)
    assert result.min()>=0 and result.max()<=1
