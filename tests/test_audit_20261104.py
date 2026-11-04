"""Independent reproductions from the November scientific/reliability audit."""
import csv
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_close_ellipse_ratios_remain_distinct_in_schedule_and_saved_records(tmp_path):
    from psychophysics_lab.experiments import ellipse_modular_centre as study
    from simulations.run import simulate
    from scripts.validate_run import validate_run
    values = {"contrast_method": "constant_stimuli", "aspect_ratios": "0.70000001,0.70000002",
              "fixed_contrasts": "0.01,0.02", "fixed_repetitions": 2, "max_trials": 8,
              "staircases_per_condition": 1}
    selected = study.SPEC.normalise_values(values)
    conditions = study.make_conditions(selected)
    assert len({c["value"] for c in conditions}) == 2
    schedule = study.make_fixed_schedule(selected, 123)
    assert len(schedule) == 8
    run, _ = simulate(repo_root=ROOT, data_root=tmp_path / "data", values=values,
                      experiment_id=study.SPEC.id, seed=123, analyse=False)
    assert run.status == "completed" and run.accepted_trials == 8
    with run.trial_log_file.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len({row["stimulus_condition"] for row in rows}) == 2
    assert all(c.passed for c in validate_run(run.run_directory))


def test_common_ellipse_labels_remain_compatible():
    from psychophysics_lab.experiments import ellipse_modular_centre as study
    values = study.SPEC.normalise_values({"aspect_ratios": "0.7,1"})
    cells = study.make_conditions(values)
    assert all(c["value"].startswith(("ratio=0.7;", "ratio=1;")) for c in cells)
    assert study.SCIENTIFIC_SPEC["version"] == "ellipse_modular_centre-3"


@pytest.mark.parametrize("synthetic", [None, {"passed": True, "status": "completed"}])
def test_failed_saved_data_cannot_be_hidden_by_other_passing_checks(synthetic):
    from psychophysics_lab.experiment_checks import SoftwareCheck, software_check_payload
    from psychophysics_lab.experiments._internal.registry import get_experiment
    from scripts.validate_run import Check
    # Use the same report object shape that validate_run actually returns.
    checks = [SoftwareCheck("Contract", True, "valid")]
    failed = Check("Canonical records", False, "truncated final row")
    report = software_check_payload(get_experiment("example_experiment"), iter(checks),
                                   synthetic_run=synthetic, data_checks=iter([failed]))
    assert report["result"] == "fail"
    assert report["saved_run_validation"][0]["passed"] is False
    assert report["generic_contract_checks"][0]["passed"] is True


def test_threshold_plot_does_not_assert_a_different_contrast_convention(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from psychophysics_lab.analysis.thresholds import _plot, ConditionThreshold
    labels = []
    original = Figure.savefig
    def save(figure, *args, **kwargs):
        labels.append(figure.axes[0].get_ylabel())
        return original(figure, *args, **kwargs)
    monkeypatch.setattr(Figure, "savefig", save)
    output = _plot((ConditionThreshold("2", 1, .1),), tmp_path / "threshold.png")
    assert output.is_file()
    assert "recorded digital units" in labels[0] and "C_disp" not in labels[0]
    assert not plt.get_fignums()


def test_review_qualifies_the_nominal_accuracy_without_changing_saved_science():
    from psychophysics_lab.config.monitor import load_monitor_profiles
    from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
    from psychophysics_lab.experiments._internal.registry import get_experiment
    from psychophysics_lab.ui.settings_review import describe_settings, review_rows
    spec = get_experiment("contrast_sensitivity")
    values = spec.normalise_values({"n_down": 2, "n_up": 1, "logUNIT_UP": .1, "logUNIT_DW": .1})
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    description = describe_settings(spec, values, snapshots, profile=profile)
    assert description["resolution"]["asymptotic_accuracy_target"] == pytest.approx(np.sqrt(.5))
    rows = review_rows(spec, values, snapshots, description)
    row = next(row for row in rows if row[1] == "asymptotic_accuracy_target")
    assert "not guaranteed" in row[3]


def test_orientation_zero_is_a_reproducible_scientific_degeneracy():
    from psychophysics_lab.stimulus_library import TeachingGabor
    parameters = {f.key: f.default for f in TeachingGabor.PARAMETERS}
    grid = np.linspace(-2.5, 2.5, 61)
    x, y = np.meshgrid(grid, grid)
    # Catch trials may be deliberate. Document the identical alternatives;
    # do not change a scientist's accepted orientation or invent a threshold.
    a = TeachingGabor.render(parameters | {"orientation_deg": -0.}, x, y)
    b = TeachingGabor.render(parameters | {"orientation_deg": 0.}, x, y)
    np.testing.assert_array_equal(a, b)
