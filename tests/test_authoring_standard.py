"""Design-freeze gates; official files stay the accepted, untouched baseline."""
import ast
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pytest
from psychophysics_lab import extensions as ext
from psychophysics_lab.experiments._internal import registry
from psychophysics_lab.data.reader import load_run
from simulations.run import simulate
from simulations.registry import TeachingObserver
from scripts.validate_run import validate_run
from test_scientist_first_examples import lab, module, ready, read, presentations, ROOT, CSF, TEMPORAL, VALUES

BASELINE = json.loads((ROOT / "tests/fixtures/authoring_standard_main_a5aa56a.json").read_text(encoding="utf-8"))


def source_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@pytest.mark.parametrize("saved", BASELINE["experiments"], ids=lambda saved: saved["id"])
def test_all_ten_official_sources_and_contracts_remain_the_accepted_main(saved):
    spec = registry.get_experiment(saved["id"])
    assert source_hash(ROOT / saved["source"]) == saved["source_sha256_lf"]
    assert json.loads(json.dumps([asdict(field) for field in spec.fields])) == saved["fields"]
    assert json.loads(json.dumps(asdict(spec.response_paradigm))) == saved["responses"]
    assert list(spec.calibration_requirements) == saved["calibration"]
    assert list(spec.monitor_capabilities) == saved["monitor_capabilities"]
    assert dict(spec.stimulus_slots) == saved["stimulus_slots"]
    assert dict(spec.stimulus_defaults) == saved["stimulus_defaults"]
    assert dict(spec.scientific_spec) == saved["scientific_spec"]


def test_shared_scientific_execution_and_frozen_evidence_are_unchanged():
    for relative, digest in BASELINE["shared_source_sha256_lf"].items():
        assert source_hash(ROOT / "src/psychophysics_lab" / relative) == digest
    assert source_hash(ROOT / BASELINE["existing_scientific_fixture"]) == BASELINE["existing_scientific_fixture_sha256_lf"]


@pytest.mark.parametrize("identity", [CSF, TEMPORAL])
def test_reference_science_is_locatable_before_framework_integration(lab, identity):
    author = module(identity)
    source = Path(author.__file__).read_text(encoding="utf-8")
    a1, a2, integration = (source.index(header) for header in
        ("# PART A1 — EXPERIMENTAL CHOICES", "# PART A2 — SCIENTIFIC METHODS", "# PART B — FRAMEWORK INTEGRATION"))
    assert a1 < source.index("def trial_events") < a2
    assert a1 < source.index("def trial_measurements") < a2
    assert a1 < source.index("CALIBRATION_REQUIREMENTS =") < a2
    for name in ("interpret_response", "choose_condition", "is_finished"):
        assert a2 < source.index("def " + name) < integration
    assert integration < source.index("def procedure") < source.index("SPEC = experiment")
    assert author.make_trial.__wrapped__ is author.trial_events


def test_factor_levels_tracks_targets_and_fixed_repetitions_are_distinct(lab):
    author = module(CSF)
    settings = author.SPEC.normalise_values(VALUES)
    assert author.scientific_conditions(settings) == [{"frequency_cpd": 2.}, {"frequency_cpd": 8.}]
    tracks = author.make_conditions(settings)
    assert len(tracks) == 4 and all("target" not in track for track in tracks)
    assert [(track["frequency_cpd"], track["repeat"]) for track in tracks] == [(2., 1), (2., 2), (8., 1), (8., 2)]
    assert author.fixed_conditions(settings, 137) == author.fixed_conditions(settings | {"staircases_per_condition": 9}, 137)
    assert len(author.fixed_conditions(settings, 137)) == 2 * 2 * 2
    assert author.RESPONSES.alternatives == ("left", "right")


@pytest.mark.parametrize("conditions", [[{"frequency_cpd": .1}], [{"frequency_cpd": float("nan")}],
    [{"frequency_cpd": 2.}, {"frequency_cpd": 2.}], [], [{}]])
def test_validation_checks_the_authoritative_factor_definition(lab, monkeypatch, conditions):
    author = module(CSF)
    monkeypatch.setattr(author, "scientific_conditions", lambda settings: conditions)
    with pytest.raises(ValueError, match="frequenc"):
        author.SPEC.normalise_values(VALUES)


def test_everyday_python_edits_change_science_without_framework_or_ui_edits(lab, tmp_path):
    # A real source edit exercise, not a human comprehension claim.
    source = lab / "experiments" / (CSF + ".py")
    text = source.read_text(encoding="utf-8")
    changed = text.replace("'text', '2,8',", "'text', '2,4,8',", 1)
    changed = changed.replace('{"name": "left", "key": "LEFT", "x_sign": -1, "y_sign": 0}',
                              '{"name": "above", "key": "UP", "x_sign": 0, "y_sign": 1}')
    changed = changed.replace('{"name": "right", "key": "RIGHT", "x_sign": 1, "y_sign": 0}',
                              '{"name": "below", "key": "DOWN", "x_sign": 0, "y_sign": -1}')
    changed = changed.replace('duration="grating_ms", beep=ONSET_BEEP', 'duration=17, beep=ONSET_BEEP')
    changed = changed.replace('MEASUREMENT_UNITS = {', 'MEASUREMENT_UNITS = {\n    "study_label": "category",', 1)
    changed = changed.replace('return {"spatial_frequency_cpd":', 'return {"study_label": "authoring-exercise", "spatial_frequency_cpd":', 1)
    assert changed != text
    source.write_text(changed, encoding="utf-8")
    ext.unload()
    assert not ext.load(ROOT, development=True)
    selected = {"contrast_method": "constant_stimuli", "fixed_contrasts": ".01", "fixed_repetitions": 2, "max_trials": 12}
    ready(CSF, selected)
    author = module(CSF)
    assert author.SPEC.field_defaults()["frequencies_cpd"] == "2,4,8"
    run, _ = simulate(repo_root=ROOT, data_root=tmp_path / "edited", experiment_id=CSF,
                      values=selected, seed=137, observer=TeachingObserver(.65), analyse=False)
    assert run.accepted_trials == 6
    saved = presentations(run)
    assert len(saved) == 6
    assert {p["measurements"]["spatial_frequency_cpd"] for p in saved} == {2., 4., 8.}
    assert {p["measurements"]["target_name"] for p in saved} == {"above", "below"}
    assert all(p["measurements"]["target_x_deg"] == 0 and abs(p["measurements"]["target_y_deg"]) == 1 for p in saved)
    assert all(p["measurements"]["study_label"] == "authoring-exercise" for p in saved)
    assert read(run, "resolved_experiment.json")["measurement_units"]["study_label"] == "category"
    assert all(trial["plan"]["phases"][1]["duration_ms"] == 17 for trial in read(run, "trial_actions.json")["trials"])
    assert len(load_run(run.run_directory)["trials"]) == 20
    assert all(check.passed for check in validate_run(run.run_directory))


ELLIPSE_UNITS = {"probe_x_deg": "degrees", "probe_y_deg": "degrees",
    "ellipse_aspect_ratio": "minor/major axis ratio", "ring_present": "boolean",
    "target_interval": "interval number, 1=first, 2=second",
    "requested_probe_increment": "digital I_probe - I_background"}


def ellipse_trial_measurements(settings, condition):
    return {"probe_x_deg": condition["x_deg"], "probe_y_deg": settings["major_axis_y_deg"],
            "ellipse_aspect_ratio": condition["aspect_ratio"], "ring_present": condition["ring"],
            "target_interval": condition["target"] + 1,
            "requested_probe_increment": condition["contrast"]}


@pytest.mark.parametrize("method", ["adaptive", "constant_stimuli"])
def test_two_interval_ellipse_accepts_same_measurement_boundary_without_scientific_change(lab, tmp_path, monkeypatch, method):
    from psychophysics_lab.experiments import ellipse_major_axis as ellipse
    from psychophysics_lab.methods import probe
    settings = dict(positions_deg="0", aspect_ratios="1", ring_conditions="base_and_ring", ring_increment=.03,
        staircases_per_condition=1, n_down=1, n_up=1, reversal_termination=4, threshold_reversals=2,
        max_trials=160, fixed_contrasts="0,.01", fixed_repetitions=2, contrast_method=method)
    def execute():
        return simulate(repo_root=ROOT, data_root=tmp_path / "ellipse", experiment_id="ellipse_major_axis",
                        values=settings, seed=137, observer=TeachingObserver(.65), analyse=False)[0]
    baseline = execute()
    original = ellipse.trial_record if method == "adaptive" else probe.fixed_probe_trial_record
    def recorded(run, condition, *state):
        entry = original(run, condition, *state)
        entry["measurements"] |= ellipse_trial_measurements(run.values, condition)
        return entry
    if method == "adaptive":
        monkeypatch.setattr(ellipse, "trial_record", recorded)
    else:
        monkeypatch.setattr(probe, "fixed_probe_trial_record", recorded)
    spec = registry.get_experiment("ellipse_major_axis")
    monkeypatch.setitem(registry._REGISTRY, spec.id, replace(spec,
        scientific_spec=dict(spec.scientific_spec) | {"measurements": ELLIPSE_UNITS}))
    candidate = execute()
    assert candidate.trial_log_file.read_bytes() == baseline.trial_log_file.read_bytes()
    assert read(candidate, "trial_actions.json") == read(baseline, "trial_actions.json")
    for filename in ("adaptive_history.json", "adaptive_session.json", "primary_thresholds.json"):
        if (baseline.run_directory / filename).exists():
            assert read(candidate, filename) == read(baseline, filename)
    rows = load_run(candidate.run_directory)["trials"]
    saved = presentations(candidate)
    assert len(saved) == candidate.accepted_trials
    for p, target in zip(saved, rows["target_alternative"]):
        assert p["measurements"]["target_interval"] == int(target) + 1
        assert set(ELLIPSE_UNITS).issubset(p["measurements"])
    assert all(c.passed for c in validate_run(candidate.run_directory))
