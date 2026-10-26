"""Universal setup vs experiment-specific study parameters and Review semantics."""

from types import SimpleNamespace

from psychophysics_lab.experiments._internal.spec import ConfigField
from psychophysics_lab.ui.config_sections import grouped_config_fields


def test_generic_sections_retain_every_scientific_field_once():
    fields = (
        ConfigField("frequencies_cpd", "Frequencies", "text", "2,8"),
        ConfigField("contrast_method", "Method", "choice", "adaptive",
                    choices=("adaptive", "constant_stimuli")),
        ConfigField("custom_study_condition", "Scientific condition", "text",
                    "ellipse_left,ellipse_right", section="Stimulus conditions"),
        ConfigField("fixed_repetitions", "Presentations per condition",
                    "int", 5, section="Constant stimuli"),
        ConfigField("background_intensity", "Background", "float", 0.5),
        ConfigField("fixation_ms", "Fixation time", "int", 500, section="Timing"),
        ConfigField("max_trials", "Safety ceiling", "int", 100),
        ConfigField("n_down", "Correct responses before decrease", "int", 2),
    )
    spec = SimpleNamespace(
        fields=fields,
        adaptive=SimpleNamespace(controls=("n_down", "max_trials")),
    )
    groups = grouped_config_fields(spec)
    assert groups[0][0] == "Universal setup"
    assert [field.key for _, fields in groups for field in fields] == [
        "contrast_method", "background_intensity", "max_trials",
        "n_down", "fixed_repetitions", "frequencies_cpd",
        "custom_study_condition", "fixation_ms",
    ]
    mapping = {group: {field.key for field in fields} for group, fields in groups}
    assert "n_down" in mapping["Adaptive settings"]
    assert "fixed_repetitions" in mapping["Constant stimuli"]
    assert "frequencies_cpd" in mapping["Experiment-specific parameters"]
    assert "custom_study_condition" in mapping["Stimulus conditions"]
    assert "fixation_ms" in mapping["Timing"]


def test_no_adaptive_or_csf_assumptions_for_a_local_extension():
    spec = SimpleNamespace(fields=(
        ConfigField("my_ratio", "Ellipse aspect", "float", 2.0),
        ConfigField("my_position", "Probe position", "float", 0.2),
        ConfigField("contrast_method", "Strength selector", "choice",
                    "constant_stimuli", choices=("adaptive", "constant_stimuli")),
        ConfigField("fixed_contrasts", "My increments", "text", ".1,.2",
                    section="Constant stimuli"),
    ), adaptive=None)
    groups = grouped_config_fields(spec)
    assert [name for name, _ in groups] == [
        "Universal setup", "Constant stimuli",
        "Experiment-specific parameters",
    ]
    assert sum(len(fields) for _, fields in groups) == len(spec.fields)


def test_review_field_origin_explains_scientific_role():
    from psychophysics_lab.experiments._internal.registry import get_experiment
    from psychophysics_lab.ui.settings_review import (
        describe_settings, review_rows,
    )
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = get_experiment("contrast_sensitivity")
    values = spec.normalise_values({})
    snapshots = resolve_stimuli(spec, values, repo_root=root)
    description = describe_settings(spec, values, snapshots)
    rows = review_rows(spec, values, snapshots, description)
    named = next(row for row in rows
                 if row[0] == "Experiment" and row[1].startswith("Spatial frequencies"))
    assert "Meaning:" in named[3]
    assert "frequencies_cpd" in named[3]
    assert str(values["frequencies_cpd"]) == named[2]
    stimulus_row = next(row for row in rows
                        if row[0] == "grating" and "Spatial frequency" in row[1])
    assert "Stimulus slot: grating" in stimulus_row[3]
    assert "renderer:" in stimulus_row[3]
