"""Versioned old-scene setup import; historical run files remain untouched.

These tests intentionally build old-schema documents without registering
DetectionScene: dropping the old renderer must not break saved-setting import.
"""
from copy import deepcopy

import pytest

from psychophysics_lab.config.stimulus_parameters import (
    migrate_legacy_detection_snapshots, resolve_stimuli, snapshot,
)
from psychophysics_lab.experiments._internal.registry import get_experiment


@pytest.fixture(params=(
    "line_position_baseline", "line_position_flanker",
    "ellipse_centre", "ellipse_major_axis",
))
def legacy_configuration(request):
    spec = get_experiment(request.param)
    overrides = {"background_intensity": 0.5}
    if request.param.startswith("line_"):
        overrides["probe_vertical_offset_deg"] = 0.4
        if request.param.endswith("flanker"):
            overrides["flanker_cpd"] = 2.0
    else:
        overrides["ring_increment"] = 0.1
    values = spec.normalise_values(overrides)
    parameters = {
        "size_deg": 14.0, "background": 0.5, "contrast": 0.02,
        "probe_length_deg": 0.133, "probe_width_deg": 0.013,
        "probe_present": True, "probe_x_deg": 0.0, "probe_y_deg": 0.0,
        "ring_present": False, "ring_radius_deg": 0.6,
        "ring_y_deg": 0.0, "aspect_ratio": 1.0,
        "ring_increment": 0.1, "flanker_present": False,
        "flanker_cpd": 2.0,
    }
    legacy = {
        slot: snapshot(
            {"schema_version": 1, "stimulus_id": "detection_scene",
             "parameters": dict(parameters)},
            file_identity=f"{slot}_old.json",
        )
        for slot in (("fixation", "first", "second")
                     if request.param.startswith("ellipse_")
                     else ("fixation", "first"))
    }
    return spec, values, legacy


def test_legacy_scene_setup_maps_to_one_atomic_probe_and_preserves_source(legacy_configuration):
    spec, values, legacy = legacy_configuration
    before = deepcopy(legacy)
    result = resolve_stimuli(spec, values, legacy)
    assert set(result) == set(spec.stimulus_slots)
    probe = result["probe"]
    assert probe["document"]["stimulus_id"] == "probe_line"
    assert probe["document"]["parameters"]["length_deg"] == pytest.approx(.133)
    assert probe["document"]["parameters"]["width_deg"] == pytest.approx(.013)
    assert probe["migrated_from"]["first"]["resolved_sha256"] == legacy["first"]["resolved_sha256"]
    assert legacy == before
    if "ellipse" in result:
        assert result["ellipse"]["document"]["stimulus_id"] == "ellipse_ring"
    if "flanker" in result:
        assert result["flanker"]["document"]["stimulus_id"] == "flanker_grating"
    assert result["fixation"]["document"]["stimulus_id"] == "gaussian_scene_fixation"


def test_inconsistent_old_dimensions_are_not_silently_chosen(legacy_configuration):
    spec, values, legacy = legacy_configuration
    legacy["fixation"] = deepcopy(legacy["fixation"])
    old_doc = deepcopy(legacy["fixation"]["document"])
    old_doc["parameters"]["probe_width_deg"] = 0.09
    legacy["fixation"] = snapshot(old_doc, file_identity="changed.json")
    with pytest.raises(ValueError, match="dimensions disagree"):
        migrate_legacy_detection_snapshots(spec, values, legacy)


def test_inconsistent_old_background_requires_explicit_choice(legacy_configuration):
    spec, values, legacy = legacy_configuration
    old_doc = deepcopy(legacy["first"]["document"])
    old_doc["parameters"]["background"] = .4
    legacy["first"] = snapshot(old_doc, file_identity="changed.json")
    with pytest.raises(ValueError, match="background differs"):
        migrate_legacy_detection_snapshots(spec, values, legacy)


def test_mixed_atomic_and_old_source_slots_are_rejected(legacy_configuration):
    spec, values, legacy = legacy_configuration
    legacy["probe"] = {"document": {"stimulus_id": "probe_line"}}
    with pytest.raises(ValueError, match="Mixed legacy/current"):
        migrate_legacy_detection_snapshots(spec, values, legacy)
