"""Registry contracts for the supported public one-file experiment catalogue."""
import pytest
from psychophysics_lab.experiments._internal.registry import get_experiment, list_experiments
from psychophysics_lab.experiments.contrast_sensitivity import make_conditions


def test_public_csf_is_registered_once_without_retired_thesis_ids():
    specs = list_experiments()
    assert "contrast_sensitivity" in {spec.id for spec in specs}
    assert get_experiment("contrast_sensitivity").id == "contrast_sensitivity"
    assert all(not spec.historical for spec in specs)
    for retired in ("legacy_contrast_sensitivity","csf_thesis","base_flanker",
                    "indirect_flanker","ellipse_2d"):
        with pytest.raises(KeyError):
            get_experiment(retired)


def test_csf_selected_frequency_list_and_adaptation_belong_to_public_spec():
    spec = get_experiment("contrast_sensitivity")
    settings = spec.normalise_values(spec.field_defaults() | {
        "frequencies_cpd": "1,3,6.5", "staircases_per_condition": 2,
        "n_down": 3, "n_up": 1, "grating_offset_deg": 1.25
    })
    assert settings["n_down"] == 3
    assert settings["grating_offset_deg"] == 1.25
    conditions = make_conditions(settings)
    assert [row["frequency_cpd"] for row in conditions] == [
        1.,1.,3.,3.,6.5,6.5
    ]
    assert len({row["id"] for row in conditions}) == 6
