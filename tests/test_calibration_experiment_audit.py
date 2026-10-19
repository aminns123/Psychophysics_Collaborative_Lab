"""Headless current-experiment calibration and spatial safety audit.

Legacy CSF executable tests were retired with the old renderer. The current
workflow is covered here and by test_calibration_review_completion.
"""
import math
from dataclasses import replace
from pathlib import Path

import pytest

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.experiments.contrast_sensitivity import (
    SPEC as CSF_SPEC, validate_monitor, maximum_contrast
)
from psychophysics_lab.stimulus_library import ContrastSensitivityGrating
from psychophysics_lab.stimuli.spatial_calibration import (
    resolve_spatial_geometry, validate_requested_cpd
)
from psychophysics_lab.core.display_tests import resolve_test
from psychophysics_lab.core.geometry_check import GeometryCheckRequest

ROOT=Path(__file__).resolve().parents[1]


def test_current_csf_uses_independent_frequency_values():
    values=CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        "frequencies_cpd":"2,4,8", "staircases_per_condition":2,
        "grating_offset_deg":1.75,
    })
    assert values["frequencies_cpd"]=="2,4,8"
    assert values["grating_offset_deg"]==1.75
    from psychophysics_lab.experiments.contrast_sensitivity import make_conditions
    assert len(make_conditions(values))==6


@pytest.mark.parametrize("background",[.1,.25,.5,.75,.9])
def test_grating_range_and_selected_background_are_consistent(background):
    settings=CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        "background_intensity":background,
        "starting_contrast":min(.05,2*min(background,1-background))
    })
    limit=maximum_contrast(settings,{})
    assert limit == pytest.approx(2*min(background,1-background))
    ContrastSensitivityGrating.validate({"background":background,"contrast":limit})
    with pytest.raises(ValueError,match="digital range"):
        ContrastSensitivityGrating.validate({"background":background,"contrast":limit+.01})


def test_spatial_preflight_rejects_unrenderable_selected_cpd():
    profile=replace(load_monitor_profiles(ROOT)["legacy_reference_display"],
                    expected_resolution_px=(1920,1080))
    values=CSF_SPEC.normalise_values(CSF_SPEC.field_defaults() | {
        "frequencies_cpd":"2,500"
    })
    request=SetupRequest("H001","new",CSF_SPEC.id,profile.id,values)
    with pytest.raises(ValueError,match="sampling limit"):
        validate_setup(request,CSF_SPEC,profile,mode="configuration")


def test_display_geometry_procedure_uses_physical_monitor_not_unverified_optical_claim():
    profile=replace(load_monitor_profiles(ROOT)["legacy_reference_display"],
                    expected_resolution_px=(1920,1080))
    req=GeometryCheckRequest(profile.id,"visual_angle_deg",5.)
    bar,plan=resolve_test(profile,req,(1920,1080))
    assert bar.realised_length_mm>0
    assert plan
    assert profile.calibration_status!="verified"


@pytest.mark.parametrize("angle",[0.,float("inf"),float("nan")])
def test_nonfinite_spatial_orientation_cannot_bypass_sampling_check(angle):
    profile=load_monitor_profiles(ROOT)["legacy_reference_display"]
    geom=resolve_spatial_geometry(profile,(1920,1080))
    with pytest.raises(ValueError):
        validate_requested_cpd((4.,),geom,orientation_rad=angle)


def test_unqualified_setup_is_not_automatically_lab_verified():
    from psychophysics_lab.config.human_readiness import experiment_readiness
    p=load_monitor_profiles(ROOT)["legacy_reference_display"]
    v=CSF_SPEC.field_defaults()
    result=validate_setup(SetupRequest("H001","new",CSF_SPEC.id,p.id,v),
                          CSF_SPEC,p,mode="configuration")
    report=experiment_readiness(result,CSF_SPEC,p,repo_root=ROOT)
    assert not report["human_ready"]
    assert report["simulation_available"]
