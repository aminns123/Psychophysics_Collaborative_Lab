"""Read-only Review must describe the actual selected scientific method."""
import copy
from dataclasses import replace
import importlib
import hashlib
import json
import random
from pathlib import Path

import pytest

from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.stimulus_parameters import resolve_stimuli
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.methods.contrast import ConstantContrastMethod
from psychophysics_lab.ui.review_authority import authority_for_row
from psychophysics_lab.ui.review_files import targets_for_rows
from psychophysics_lab.ui.settings_review import describe_settings, review_rows
from psychophysics_lab.data.reader import load_run
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run


ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ("contrast_sensitivity", "ellipse_centre", "ellipse_major_axis")


def selected(identity, method, **changes):
    spec = get_experiment(identity)
    values = {"contrast_method": method, "max_trials": 10000, "response_keys": "Z,X"}
    if identity.startswith("ellipse"):
        values["ring_increment"] = .03
    values.update(changes)
    values = spec.normalise_values(values)
    snapshots = resolve_stimuli(spec, values, repo_root=ROOT)
    return spec, values, snapshots


def review(spec, values, snapshots, **kwargs):
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    description = describe_settings(spec, values, snapshots, profile=profile, **kwargs)
    rows = review_rows(spec, values, snapshots, description, refresh_hz=profile.refresh_rate_hz)
    targets = targets_for_rows(spec, snapshots, description, rows,
                               {"experiment": None, "stimuli": {}}, ROOT)
    return description, rows, targets


@pytest.mark.parametrize("identity", IDENTITIES)
@pytest.mark.parametrize("method", ("adaptive", "constant_stimuli"))
def test_all_selected_inputs_measurements_units_and_source_routes_are_truthful(identity, method):
    spec, values, snapshots = selected(identity, method)
    before = copy.deepcopy((values, snapshots))
    rng = random.getstate()
    description, rows, targets = review(spec, values, snapshots)
    assert (values, snapshots) == before
    assert random.getstate() == rng
    assert len(rows) == len(set(rows))  # no duplicate table rows
    assert description["trial_event_function"] == "trial_events"
    assert [p["name"] for p in description["session_phases"]] == ["ready", "settle"]
    assert description["session_phases"][0]["key"] == "SPACE"
    for field in spec.fields:
        inputs = [row for row in rows if row[0] in {"Experiment", "Adaptive"}
                  and row[1] == field.display_label]
        assert len(inputs) == 1, field.key
        assert inputs[0][2] == str(values[field.key])
    assert description["measurements"]
    assert all(item["units"] != "Units not declared" for item in description["measurements"].values())
    assert all(any(row[0] == "Recorded measurements" and row[1] == f"{name} ({item['units']})"
                   for row in rows) for name, item in description["measurements"].items())
    for index, row in enumerate(rows):
        target = targets[index]
        assert target["kind"] != "unavailable", row
        if target.get("path") is not None:
            assert target["path"].is_file()
            assert 1 <= target["line"] <= len(target["path"].read_text(encoding="utf-8-sig").splitlines())
        authority = authority_for_row(spec, values, snapshots, description, row, target,
                                      {"experiment": None, "stimuli": {}})
        if target.get("key") in description["inactive_fields"]:
            assert authority["status"] == "Inactive for selected method"
            assert authority["edit_kind"] is None
            assert "validation" in authority["explanation"]
        if target.get("key") == "max_trials":
            assert authority["status"] == "Editable experiment"
    outputs = {row[1]: row[2] for row in rows if row[0] == "Saved data"}
    assert outputs["Canonical trial table"] == "trials.tsv"
    assert outputs["Per-trial journal"] == "trial_events.jsonl"
    assert ("Fixed-level results" if method == "constant_stimuli" else "Adaptive results") in outputs
    if method == "constant_stimuli":
        assert not any(row[0] in {"Adaptive", "Adaptive scale", "Threshold estimation"} for row in rows)
        for name in ("value", "frequency_cpd") if identity == "contrast_sensitivity" else ("value", "x_deg", "aspect_ratio", "ring"):
            assert all(name in condition for condition in description["conditions"]), name
    else:
        expected = 2 if identity == "contrast_sensitivity" else 3 if identity == "ellipse_centre" else 18
        assert ("Conditions", "Number of distinct scientific conditions", str(expected)) in [row[:3] for row in rows]


def test_fixed_centre_headroom_matches_actual_method_on_selected_display():
    spec, values, snapshots = selected("ellipse_centre", "constant_stimuli",
                                       ring_increment=.49, aspect_ratios="1", fixed_contrasts="0,.01")
    description, rows, _ = review(spec, values, snapshots)
    maximum = next(row[2] for row in rows if row[:2] == ("Intensity", "Maximum nominal probe intensity"))
    assert float(maximum) == pytest.approx(.5841346154, abs=1e-10)
    assert all(c["maximum_probe_increment"] == pytest.approx(.0841346153846154)
               for c in description["conditions"])
    assert description["resolution"]["condition_definitions"]
    assert "fixed_repeat" in description["measurements"]
    assert "staircase_repeat" not in description["measurements"]


def test_fixed_centre_invalid_overlap_is_refused_without_changing_draft():
    spec, values, snapshots = selected("ellipse_centre", "constant_stimuli",
                                       ring_increment=.49, aspect_ratios="1", fixed_contrasts=".1")
    before = copy.deepcopy((values, snapshots))
    with pytest.raises(ValueError, match="overlap exceeds digital gamut"):
        review(spec, values, snapshots)
    assert (values, snapshots) == before


@pytest.mark.parametrize("identity", IDENTITIES)
@pytest.mark.parametrize("method", ("adaptive", "constant_stimuli"))
def test_review_measurements_match_recorded_journal_and_full_source_provenance(tmp_path, monkeypatch, identity, method):
    monkeypatch.setattr("psychophysics_lab.analysis.previews.create_run_figures", lambda **kwargs: None)
    changes = {"max_trials": 2} if method == "adaptive" else {"fixed_repetitions": 1, "fixed_contrasts": "0,.01"}
    spec, values, snapshots = selected(identity, method, **changes)
    description, _, _ = review(spec, values, snapshots)
    artifact, _ = simulate(repo_root=ROOT, data_root=tmp_path, experiment_id=identity,
                            values=values, seed=0, analyse=False, observer=TeachingObserver(.65))
    presentations = json.loads((artifact.run_directory / "trial_presentations.json").read_text())["trials"]
    assert presentations
    assert all(set(row["measurements"]) == set(description["measurements"]) for row in presentations)
    assert len(load_run(artifact.run_directory)["trials"]["trial_index"]) == artifact.accepted_trials
    assert len(artifact.trial_log_file.read_text().splitlines()[0].split("\t")) == 20
    manifest = json.loads(artifact.manifest_file.read_text())
    for relative in spec.source_paths:
        assert manifest["registered_source_sha256"][relative] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    assert all(check.passed for check in validate_run(artifact.run_directory))


@pytest.mark.parametrize("identity", IDENTITIES)
def test_fixed_review_never_progresses_or_executes_the_method(identity, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Review must not execute or advance scientific trials")
    for name in ("next_trial", "accept_response", "complete"):
        monkeypatch.setattr(ConstantContrastMethod, name, forbidden)
    spec, values, snapshots = selected(identity, "constant_stimuli")
    description, _, _ = review(spec, values, snapshots)
    assert description["phases"]


@pytest.mark.parametrize("identity", ("ellipse_centre", "ellipse_major_axis"))
def test_ellipse_controls_route_to_actual_selected_study_inputs(identity):
    spec, values, snapshots = selected(identity, "adaptive")
    description, rows, targets = review(spec, values, snapshots)
    stimulus = importlib.import_module("psychophysics_lab.stimuli.registry").get_stimulus("detection_scene")
    labels = {field.key: field.display_label for field in stimulus.parameters}
    for slot in ("first", "second"):
        for parameter, control in spec.stimulus_parameter_controls[slot].items():
            index = next(i for i, row in enumerate(rows) if row[:2] == (slot, labels[parameter]))
            assert targets[index]["kind"] == "experiment_json"
            assert targets[index]["key"] == control
            authority = authority_for_row(spec, values, snapshots, description, rows[index], targets[index], {})
            assert authority["status"] == "Experiment-controlled"
            assert authority["field"] == control


def test_legacy_callable_reviewer_is_not_called_for_fixed_mode():
    spec, values, snapshots = selected("contrast_sensitivity", "constant_stimuli")
    def adaptive_only(run):
        pytest.fail("Legacy adaptive-only callback must not be called for fixed Review")
    legacy = replace(spec, method_reviewer=adaptive_only)
    description, rows, _ = review(legacy, values, snapshots)
    assert description["resolution"]["trial_selection_method"] == "constant_stimuli"
    assert any(row[:2] == ("Experiment", "Software safety ceiling (not scientific completion) (responses)")
               for row in rows)


@pytest.mark.parametrize("reviewer", ({"constant_stimuli": None}, {1: lambda run: None}, []))
def test_invalid_method_reviewer_declarations_fail_explicitly(reviewer):
    with pytest.raises(TypeError, match="reviewer"):
        replace(get_experiment("contrast_sensitivity"), method_reviewer=reviewer)
