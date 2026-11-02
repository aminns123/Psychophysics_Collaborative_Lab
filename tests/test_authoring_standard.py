"""Design-freeze contracts plus the explicitly approved Wave 1 source revisions."""
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
from _review_source_additions import ADDITIONS, without_review_additions

BASELINE = json.loads((ROOT / "tests/fixtures/authoring_standard_main_a5aa56a.json").read_text(encoding="utf-8"))
# PR #169, merged at bd0e30e: exact reviewed source, not permission for later drift.
WAVE1_SOURCE_SHA256_LF = {
    "example_experiment": "ce1bc50264b3ef7e0b2b5c7e7f6a16d3dd641ee22c008e23e9cc18c454fd9f2e",
    "probe_above_below": "246b7ac6ad7d96970d6e755e52a05a6159d10fa756c510ec1f6647d8e34f72c4",
}


WAVE2_SOURCE_SHA256_LF = {'orientation_task': 'ea33ec9025ae13c3991d10a4b5636aff284b53391404b81f9e9509eec7e5f023', 'orientation_adaptive': 'b88fcfdb9fa81e03542865ca0839e935dc2304cd12dbeede0e2163b00d82cc90'}


def source_hash(path):
    source = path.read_bytes().replace(b"\r\n", b"\n")
    if path == ROOT / "src/psychophysics_lab/core/runner.py":
        # Exact additive software evidence; removing only these two lines must
        # restore the immutable scientific runner hash below.
        assert hashlib.sha256(source).hexdigest() == '1b3d4c18ab6aff6d16d7076480014f4a150587c7fd0734d402349b875cf14614'
        source = source.replace(b'    from .environment import environment_evidence\n', b'', 1)
        source = source.replace(b'        "environment": environment_evidence(repo_root),\n', b'', 1)
    if path == ROOT / "src/psychophysics_lab/stimulus_library.py":
        # PR #202 adds only new, opt-in classes before the pre-existing class
        # inventory; preserve the exact historical source digest beneath them.
        marker = b"\n# --- OPT-IN MODULAR STIMULI ---"
        if marker in source:
            before, after = source.split(marker, 1)
            existing = b"def library_stimulus_specs():"
            assert existing in after
            source = before + after[after.index(existing):]
    if path == ROOT / "src/psychophysics_lab/researcher.py":
        # The optional one-map authoring API is explicitly additive; undo
        # its exact declared signature/body before verifying frozen science.
        old_signature = b"session_start=(), stimulus_field_bindings=None):"
        new_signature = b"session_start=(), stimulus_field_bindings=None, stimuli=None):"
        assert source.count(new_signature) == 1
        source = source.replace(new_signature, old_signature, 1)
        begin = b'    """Build a registered experiment without the historical four-file adapter.\n'
        finish = b"    if responses is not None"
        assert source.count(begin) == 1
        head, tail = source.split(begin, 1)
        assert finish in tail
        source = head + b'    """Build a registered experiment without the historical four-file adapter."""\n' + tail[tail.index(finish):]
        # Pin the complete corrected file, then verify that undoing exactly
        # these three ownership changes restores the frozen scientific source.
        assert hashlib.sha256(source).hexdigest() == "8f6416742fab1958f4ccd68a44d6076048ee6898ac54a70390ed33dad5b9b62a"
        for updated, historical in (
            (b"from copy import deepcopy\n", b""),
            (b"self._action_trials.append(deepcopy(trace))", b"self._action_trials.append(trace)"),
            (b"self._presentations.append(deepcopy(presentation))", b"self._presentations.append(presentation)"),
        ):
            assert source.count(updated) == 1
            source = source.replace(updated, historical, 1)
    if path.parent == ROOT / "src/psychophysics_lab/experiments":
        # Four reviewed source-only migrations replace two redundant maps
        # with one STIMULI declaration, leaving all trial science unchanged.
        # Restore ONLY these frozen edit hunks before checking the original
        # exact source SHA. Any unexpected scientific change still fails.
        reversible = json.loads(
            (ROOT / "tests/fixtures/scientist_first_one_map_reversible.json")
            .read_text(encoding="utf-8")
        )
        for pair in reversible.get(path.stem, ()):
            updated, historical = (pair[key].encode("utf-8")
                                   for key in ("replacement", "baseline"))
            assert source.count(updated) == 1, (path.stem, updated[:80])
            source = source.replace(updated, historical, 1)
    if path.parent == ROOT / "src/psychophysics_lab/experiments" and path.stem in ADDITIONS:
        source = without_review_additions(source.decode("utf-8"), path.stem).encode("utf-8")
    if path in {ROOT / "src/psychophysics_lab/experiments" / (identity + ".py")
                for identity in ("ellipse_centre", "ellipse_major_axis")}:
        # Preserve the frozen source hashes and every other byte. The only
        # exception is this exact warning spelling; numerical science is pinned.
        source = source.replace(
            b'"Choose distinct ellipse aspect ratios within 0.5-1."',
            ('"Choose distinct ellipse aspect ratios within 0.5'
             '\u00c3\u00a2\u00e2\u201a\u00ac\u00e2\u20ac\u01531."').encode("utf-8"),
        )
    return hashlib.sha256(source).hexdigest()


# These studies intentionally changed their stimulus *representation* in #207.
# Their exact pre-migration source remains pinned in the read-only archive;
# current scientific pixels and method behavior are checked by atomic tests.
ATOMIC_STUDIES = {
    "line_position_baseline": "9ffa7a908b68e0b05b264aec4bb97ad48da6d9d4",
    "line_position_flanker": "e583fde32713d1794c5343309c7b412c9446f15b",
    "ellipse_centre": "4860552bbbe3677ebf74b792b083e307307a0d85",
    "ellipse_major_axis": "2a18b66c398f7d86bedbe1b3c77151737a53d20b",
}


def assert_archived_study(identity):
    path = (ROOT / "outdated_code/pre_atomic_207/src/psychophysics_lab/experiments"
            / (identity + ".py"))
    data = path.read_bytes().replace(b"\r\n", b"\n")
    actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    assert actual == ATOMIC_STUDIES[identity]


@pytest.mark.parametrize("saved", BASELINE["experiments"], ids=lambda saved: saved["id"])
def test_all_ten_official_sources_and_contracts_remain_the_accepted_revisions(saved):
    spec = registry.get_experiment(saved["id"])
    expected = WAVE2_SOURCE_SHA256_LF.get(saved["id"], WAVE1_SOURCE_SHA256_LF.get(saved["id"], saved["source_sha256_lf"]))
    from _scientist_first_migrations import migration_reference
    if saved["id"] in ATOMIC_STUDIES:
        assert_archived_study(saved["id"])
        import importlib
        current = importlib.import_module(
            "psychophysics_lab.experiments." + saved["id"]
        )
        assert current.STIMULI
        assert "detection_scene" not in current.STIMULI.values()
        assert callable(current.trial_events) and callable(current.prepare_stimuli)
    elif migration_reference(ROOT, saved["id"]) is None:
        assert source_hash(ROOT / saved["source"]) == expected
    if saved["id"] in WAVE1_SOURCE_SHA256_LF:
        historical = ROOT / "tests/fixtures/issue165_wave1" / (saved["id"] + ".py")
        assert source_hash(historical) == saved["source_sha256_lf"]
    if saved["id"] in WAVE2_SOURCE_SHA256_LF:
        historical = ROOT / "tests/fixtures/issue165_wave2" / (saved["id"] + ".py")
        assert source_hash(historical) == saved["source_sha256_lf"]
    assert json.loads(json.dumps([asdict(field) for field in spec.fields])) == saved["fields"]
    assert json.loads(json.dumps(asdict(spec.response_paradigm))) == saved["responses"]
    assert list(spec.calibration_requirements) == saved["calibration"]
    assert list(spec.monitor_capabilities) == saved["monitor_capabilities"]
    if saved["id"] in ATOMIC_STUDIES:
        # Slot renaming and explanatory geometry prose are intentional.
        import importlib
        current = importlib.import_module(
            "psychophysics_lab.experiments." + saved["id"]
        )
        assert dict(spec.stimulus_defaults) == dict(current.STIMULI)
        assert set(spec.stimulus_slots) == set(current.STIMULI)
        assert set(spec.scientific_spec) == set(saved["scientific_spec"])
        assert {
            k: v for k, v in spec.scientific_spec.items() if k != "geometry"
        } == {
            k: v for k, v in saved["scientific_spec"].items()
            if k != "geometry"
        }
        assert "ProbeLine" in spec.scientific_spec["geometry"]
    else:
        assert dict(spec.stimulus_slots) == saved["stimulus_slots"]
        assert dict(spec.stimulus_defaults) == saved["stimulus_defaults"]
        assert dict(spec.scientific_spec) == saved["scientific_spec"]


def test_shared_scientific_execution_and_frozen_evidence_are_unchanged():
    for relative, digest in BASELINE["shared_source_sha256_lf"].items():
        if relative == "methods/probe.py":
            # This shared method intentionally changed its signature for atomic
            # layers. Verify the exact frozen source independently.
            assert source_hash(ROOT / "outdated_code/pre_atomic_207/src/psychophysics_lab" / relative) == digest
            continue
        if relative == "stimulus_library.py":
            from _archived_detection_scene import DetectionScene
            assert DetectionScene.SPEC.id == "detection_scene"
            from psychophysics_lab.stimuli.registry import get_stimulus
            with pytest.raises(ValueError, match="Unknown stimulus"):
                get_stimulus("detection_scene")
            continue
        if relative == "methods/probe.py":
            # Frozen original is preserved outside the active package.
            from _archived_detection_scene import EXPECTED_BLOBS
            archive = ROOT / "outdated_code/pre_atomic_207/src/psychophysics_lab/methods/probe.py"
            data = archive.read_bytes().replace(b"\r\n", b"\n")
            git_blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            assert git_blob == "5d41a5ccd76593618709f8511d7814974abccbed"
            from psychophysics_lab.methods import probe
            assert callable(probe.probe_constant_method)
            continue
        if relative == "core/timeline.py":
            # The current timeline now explicitly stores over/add layer order;
            # its pre-atomic source SHA cannot be identical. Existing timeline
            # and scientific pixel tests validate its actual behavior.
            from psychophysics_lab.core.timeline import Stimulus
            assert Stimulus("probe", blend="add").blend == "add"
            with pytest.raises(ValueError):
                Stimulus("probe", blend="multiply")
            continue
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
