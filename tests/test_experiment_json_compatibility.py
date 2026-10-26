"""Additive method fields may default; original and unknown keys stay strict."""
import json
from pathlib import Path
import pytest

from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.ui.parameter_files import load_experiment_json

OFFICIAL = ("contrast_sensitivity", "line_position_baseline", "line_position_flanker",
            "ellipse_centre", "ellipse_major_axis", "orientation_adaptive",
            "orientation_task", "probe_above_below", "example_experiment")


@pytest.mark.parametrize("identity", OFFICIAL)
def test_old_complete_json_fills_only_declared_additions(identity, tmp_path):
    spec = get_experiment(identity)
    required = ({"probe_vertical_offset_deg": .5} if identity.startswith("line_position")
                else {"ring_increment": .1} if identity.startswith("ellipse") else {})
    if identity == "line_position_flanker":
        required["flanker_cpd"] = 2.
    values = spec.normalise_values(required)
    older = {f.key: values[f.key] for f in spec.fields if not f.allow_legacy_default}
    path = tmp_path / "old.json"
    def write(selected):
        path.write_text(json.dumps({"schema_version": 1, "experiment_id": identity,
                                    "values": selected}), encoding="utf-8")
    write(older)
    original = path.read_bytes()
    assert load_experiment_json(path, spec) == values
    assert path.read_bytes() == original
    write(older | {"fixed_repetition": 5})
    with pytest.raises(ValueError, match="no unknown keys"):
        load_experiment_json(path, spec)
    del older[next(iter(older))]
    write(older)
    with pytest.raises(ValueError, match="every declared"):
        load_experiment_json(path, spec)


def test_added_method_values_still_receive_scientific_validation(tmp_path):
    spec = get_experiment("example_experiment")
    path = tmp_path / "bad.json"
    document = {"schema_version": 1, "experiment_id": spec.id,
                "values": spec.normalise_values({}) | {"contrast_method": "constant_stimuli",
                                                       "fixed_contrasts": "nan"}}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        load_experiment_json(path, spec)
