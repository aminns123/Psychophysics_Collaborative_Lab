"""Researcher-selected scientific fields must drive execution, not frozen defaults.

Regression tests deliberately choose nondefault physical values. The field
definitions belong at the top of each public experiment Python file.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from psychophysics_lab.experiments import (
    contrast_sensitivity as csf,
    probe_above_below as probe,
    ellipse_centre as centre,
    ellipse_major_axis as axis,
)


class StubRun:
    def __init__(self, values):
        self.values = values
        self.responses = SimpleNamespace(alternatives=("above", "below"))
        self.stimulus_snapshots = {}
        self.initialisation = None

    def stimulus_parameters(self, slot, **kwargs):
        return dict(kwargs)

    def initialise(self, **kwargs):
        self.initialisation = kwargs


@pytest.mark.parametrize("module", [probe])
@pytest.mark.parametrize("distance_deg", [0.5, 1.25, 3.0])
def test_above_below_probes_follow_selected_offset_in_conditions_and_timeline(module, distance_deg):
    values = module.SPEC.normalise_values(
        module.SPEC.field_defaults() | {"trial_count": 4, "probe_vertical_offset_deg": distance_deg}
    )
    assert next(f for f in module.SPEC.fields if f.key == "probe_vertical_offset_deg").units == "degrees"
    conditions = module.make_conditions(values)
    assert len(conditions) == 4
    assert {c["probe_y_deg"] for c in conditions} == {-distance_deg, distance_deg}
    assert all(c["probe_y_deg"] == (distance_deg if c["target"] == 0 else -distance_deg)
               for c in conditions)
    for condition in conditions:
        phases = module.make_trial(values, condition).resolve(values).phases
        probe_placements = next(phase.placements for phase in phases if phase.name == "probe")
        assert probe_placements[-1].y_deg == condition["probe_y_deg"]
    run = StubRun(values)
    module.initialise_experiment(run, conditions)
    assert run.initialisation["resolution"]["probe_vertical_offset_deg"] == distance_deg
    for label, sign in [("above_timeline", 1), ("below_timeline", -1)]:
        timeline = run.initialisation["resolution"][label]
        probe_phase = next(ph for ph in timeline["phases"] if ph["name"] == "probe")
        assert probe_phase["stimuli"][-1]["y_deg"] == sign * distance_deg


@pytest.mark.parametrize("bad", [-1.0, 0.0, float("nan"), float("inf")])
def test_above_below_rejects_invalid_offsets(bad):
    for module in (probe,):
        with pytest.raises(ValueError):
            module.SPEC.normalise_values(
                module.SPEC.field_defaults() | {"probe_vertical_offset_deg": bad}
            )


def test_retired_probe_settings_remain_readable_without_importing_removed_source():
    import json
    from psychophysics_lab.authoring import inventory, load_authored

    root = Path(__file__).resolve().parents[1]
    path = root / "configs/experiments/new_probe_vertical_line_stimulus.json"
    source = json.loads(path.read_text(encoding="utf-8"))

    # The former experiment's Python source is absent by design. Its saved
    # settings stay readable, but no published Ready entry may reference it.
    assert source["experiment_id"] == "new_probe_vertical_line_stimulus"
    assert source["values"]["probe_vertical_offset_deg"] == 2.0
    assert not (root / "src/psychophysics_lab/experiments/new_probe_vertical_line_stimulus.py").exists()
    assert ("experiment", "new_probe_vertical_line_stimulus") not in {
        (item.kind, item.name) for item in inventory(root)
    }
    assert "experiment:new_probe_vertical_line_stimulus" not in load_authored(
        root, tolerate_errors=True
    )


@pytest.mark.parametrize("radius,y", [(0.4, -1.1), (0.8, 1.25)])
@pytest.mark.parametrize("module,y_key", [(centre, "ellipse_centre_y_deg"), (axis, "major_axis_y_deg")])
def test_ellipse_geometry_uses_researcher_selected_radius_and_vertical_centre(module, y_key, radius, y):
    values = module.SPEC.normalise_values(module.SPEC.field_defaults() | {
        "ring_increment": 0.05, "ring_radius_deg": radius,
        y_key: y, "aspect_ratios": "0.5,1",
    })
    assert next(f for f in module.SPEC.fields if f.key == "ring_radius_deg").units == "degrees"
    assert next(f for f in module.SPEC.fields if f.key == y_key).units == "degrees"
    condition = module.make_conditions(values)[0] | {"target": 0, "contrast": 0.01}
    stimuli = module.prepare_stimuli(StubRun(values), condition, {})
    assert stimuli["first"]["ring_radius_deg"] == radius
    assert stimuli["second"]["ring_radius_deg"] == radius
    assert stimuli["first"]["probe_y_deg"] == y
    assert stimuli["first"]["ring_y_deg"] == y
    assert stimuli["second"]["probe_y_deg"] == y
    assert stimuli["second"]["ring_y_deg"] == y
    assert stimuli["first"]["probe_x_deg"] == condition["x_deg"]


@pytest.mark.parametrize("module", [centre, axis])
def test_ellipse_rejects_inner_axis_that_collapses(module):
    with pytest.raises(ValueError, match="inner-axis inset"):
        module.SPEC.normalise_values(module.SPEC.field_defaults() | {
            "ring_increment": 0.02, "ring_radius_deg": 0.2, "aspect_ratios": "0.5,1"
        })


@pytest.mark.parametrize("sigma", [0.3, 0.85, 1.5])
def test_csf_gaussian_sigma_is_an_experiment_field_and_drives_grating(sigma):
    values = csf.SPEC.normalise_values(csf.SPEC.field_defaults() | {
        "grating_sigma_deg": sigma, "grating_offset_deg": 1.3
    })
    assert next(f for f in csf.SPEC.fields if f.key == "grating_sigma_deg").units == "degrees"
    condition = {"frequency_cpd": 2.0, "contrast": 0.05}
    params = csf.prepare_stimuli(StubRun(values), condition, {})
    assert params["grating"]["sigma_deg"] == sigma
    assert params["grating"]["spatial_frequency_cpd"] == condition["frequency_cpd"]
    for side, sign in ((0, -1), (1, 1)):
        trial = csf.make_trial(values, {"target": side}).resolve(values)
        assert trial.phases[1].placements[0].x_deg == sign * values["grating_offset_deg"]


@pytest.mark.parametrize("bad", [0.0, -0.1, float("nan"), float("inf")])
def test_csf_sigma_rejects_invalid_width(bad):
    with pytest.raises(ValueError):
        csf.SPEC.normalise_values(csf.SPEC.field_defaults() | {"grating_sigma_deg": bad})



# Every public experiment must remain understandable from its first section.
from psychophysics_lab.experiments import (
    example_experiment, line_position_baseline, line_position_flanker,
    orientation_task, orientation_adaptive,
)

PUBLIC_FILES = (
    csf, probe, centre, axis, example_experiment,
    line_position_baseline, line_position_flanker, orientation_task,
    orientation_adaptive,
)


@pytest.mark.parametrize("module", PUBLIC_FILES)
def test_all_public_experiment_fields_precede_scientific_execution(module):
    import inspect
    source = inspect.getsource(module)
    migrated = hasattr(module, "trial_events")
    parameters = "# 1. PARAMETERS" if migrated else "# 1. SETTINGS AND STIMULI"
    following = "# 2. SESSION START" if migrated else "# 2. CONDITIONS AND TRIAL ORDER"
    if "# PART A1" in source:
        parameters, following = "# PART A1", "SESSION_START = ["
    assert source.index(parameters) < source.index("FIELDS = (")
    assert source.index("FIELDS = (") < source.index(following) < source.index("def procedure")
    for field in module.SPEC.fields:
        if field.key.endswith("_deg"):
            assert field.units == "degrees", (module.__name__, field.key, field.units)
        if field.key.endswith("_ms"):
            assert field.units == "ms", (module.__name__, field.key, field.units)
        if field.key.endswith("_cpd"):
            assert "cycles/degree" in field.units, (module.__name__, field.key, field.units)
