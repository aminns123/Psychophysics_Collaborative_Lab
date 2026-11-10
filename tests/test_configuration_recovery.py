"""Recovery cannot become an executable request before deliberate validation."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sys

import pytest

from psychophysics_lab import extensions
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.sharing import make_document, read_document, validate_portable
from psychophysics_lab.configuration_recovery import RecoveryRule, prepare_recovery
from psychophysics_lab.development import execute_user_action
from psychophysics_lab.experiments._internal.registry import get_experiment
from test_configuration_sharing import ROOT, request_for
from test_laboratory_extensions import EXPERIMENT, STIMULUS, enable, lab
from test_parameter_accessibility import OFFICIAL


def prepare(document, *, raw=None, verify_sources=lambda *_: None):
    raw = raw if raw is not None else json.dumps(document).encode()
    return prepare_recovery(document, raw, ROOT, verify_sources=verify_sources)


def row(draft, *suffix):
    return next(item for item in draft.rows if item.path[-len(suffix):] == suffix)


def finish(draft, tmp_path, request, profile, *, reviewed=True):
    return draft.save(tmp_path/"recovered", ROOT, request, profile, reviewed=reviewed,
                      verify_sources=lambda spec, snapshots: extensions.check_run(ROOT, spec, snapshots))


@pytest.mark.parametrize("identity", OFFICIAL)
def test_same_schema_with_missing_field_only_recovers_exact_remaining_values(identity):
    request, profile = request_for(identity)
    complete = make_document(ROOT, request, profile)
    assert validate_portable(complete, ROOT, request, profile)[0].experiment_values == request.experiment_values
    incoming = deepcopy(complete)
    del incoming["presentation"]["show_response_instructions"]
    draft = prepare(incoming)
    assert draft.unresolved == len(draft.rows)
    assert sum(item.status == "Missing" for item in draft.rows) == 1
    draft.accept_compatible()
    assert draft.unresolved == 1
    assert {item.field.key: item.value for item in draft.rows if item.path[0] == "experiment"} == request.experiment_values


def test_historical_ellipse_rejects_strict_and_recovers_explicit_geometry(tmp_path):
    request, profile = request_for()
    # Reproduce the old on-disk shape and observed dimensions using the
    # public example settings. The original lab exports are tested separately.
    old = read_document(ROOT/"docs/examples/ellipse_centre_configuration.json")
    old["schema_version"] = 1
    old["software"]["psycolab_version"] = "0.3.0"
    old["software"]["engine_sha256"] = "a" * 64
    probe = old["stimuli"]["probe"]["parameters"]
    probe.update(length_deg=1.0, width_deg=.013)
    del probe["size_deg"]
    old["experiment"]["values"]["unused_historical"] = 12
    raw = b"\xef\xbb\xbf" + (json.dumps(old, indent=2) + "\r\n").encode()
    source = tmp_path/"old ellipse.json"
    source.write_bytes(raw)
    historical_run = tmp_path/"participant runs"/"trials.tsv"
    historical_run.parent.mkdir()
    historical_run.write_bytes(b"historical synthetic trial bytes\r\n")

    document, original_bytes = read_document(source, include_bytes=True)
    with pytest.raises(ValueError, match="version 1"):
        validate_portable(document, ROOT, request, profile)
    draft = prepare(document, raw=original_bytes)
    assert row(draft, "probe", "parameters", "length_deg").suggestion == 1.0
    assert row(draft, "probe", "parameters", "width_deg").suggestion == .013
    assert row(draft, "probe", "parameters", "size_deg").status == "Missing"
    assert draft.unmapped[("experiment", "values", "unused_historical")] == 12
    draft.accept_compatible()
    assert draft.unresolved == len(draft.rows)
    with pytest.raises(ValueError, match="Resolve all"):
        finish(draft, tmp_path, request, profile)
    assert not (tmp_path/"recovered").exists()

    for item in draft.rows:
        item.decide("accept" if item.suggestion is not None else "default")
    width = row(draft, "probe", "parameters", "width_deg")
    width.decide("reject")
    with pytest.raises(ValueError, match="explicit value"):
        width.decide("replace", "  ")
    width.decide("replace", "0.02")
    with pytest.raises(ValueError, match="Confirm you reviewed"):
        finish(draft, tmp_path, request, profile, reviewed=False)

    recovered, files, saved = finish(draft, tmp_path, request, profile)
    assert recovered.stimulus_snapshots["probe"]["document"]["parameters"]["length_deg"] == 1.0
    assert recovered.stimulus_snapshots["probe"]["document"]["parameters"]["width_deg"] == .02
    assert validate_portable(read_document(saved), ROOT, request, profile)[0].experiment_values == recovered.experiment_values
    assert recovered.researcher_override is None and recovered.participant_id == request.participant_id
    with pytest.raises(ValueError, match="Human acquisition blocked"):
        validate_setup(recovered, get_experiment(recovered.experiment_id), profile, mode="human")
    evidence = saved.parent/"recovery"
    assert (evidence/"original.json").read_bytes() == source.read_bytes() == raw
    report_path = evidence/"decisions.json"
    report = read_document(report_path)
    assert report["original_software"] == old["software"]
    assert report["unmapped"] == [{"path": ["experiment", "values", "unused_historical"], "value": 12,
                                  "status": "Obsolete or unrecognised"}]
    width_report = next(item for item in report["parameters"] if item["path"][-1] == "width_deg")
    assert width_report["decisions"] == [{"action": "accept", "value": .013},
                                        {"action": "reject", "value": None},
                                        {"action": "replace", "value": .02}]
    origin = recovered.stimulus_snapshots["probe"]["configuration_origin"]["recovered_from"]
    assert origin == {"original_sha256": hashlib.sha256(raw).hexdigest(),
                      "decisions_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}
    assert len(files) == len(recovered.stimulus_snapshots) + 2
    assert historical_run.read_bytes() == b"historical synthetic trial bytes\r\n"
    from scripts.validate_run import validate_run
    from simulations.run import simulate
    result, _ = simulate(repo_root=ROOT, data_root=tmp_path/"virtual output", experiment_id=recovered.experiment_id,
                         values=recovered.experiment_values, stimulus_snapshots=recovered.stimulus_snapshots,
                         seed=41, analyse=False)
    assert all(check.passed for check in validate_run(result.run_directory))
    recorded = read_document(result.run_directory/"experiment_config.json")["request"]
    assert recorded["stimulus_snapshots"]["probe"]["configuration_origin"]["recovered_from"] == origin


@pytest.mark.parametrize("change,error", [
    (lambda d: d.update(schema_version=999), "Portable configuration schema"),
    (lambda d: d.update(format="unknown"), "portable configuration files only"),
    (lambda d: d["experiment"].update(experiment_id="downloaded.module"), "experiment.*not installed"),
    (lambda d: d["stimuli"]["probe"].update(stimulus_id="downloaded.module"), "probe.*stimulus.*not installed"),
    (lambda d: d["stimuli"]["probe"].update(schema_version=3), "Stimulus schema"),
    (lambda d: d["experiment"].update(values=[]), "values must be a JSON object"),
])
def test_bad_formats_and_missing_dependencies_have_no_recovery(change, error):
    request, profile = request_for()
    incoming = make_document(ROOT, request, profile)
    change(incoming)
    with pytest.raises(ValueError, match=error):
        prepare(incoming)
    assert "downloaded.module" not in sys.modules


def test_unrecognized_method_invalid_values_and_new_defaults_remain_unresolved(tmp_path):
    request, profile = request_for()
    incoming = make_document(ROOT, request, profile)
    incoming["software"]["source_sha256"] = "e" * 64
    incoming["experiment"]["values"].update(contrast_method="other_estimator", response_keys="",
                                            fixation_ms=None, ring_radius_deg=-.5)
    incoming["stimuli"]["probe"]["parameters"].update(length_deg={"expression": "malicious()"}, width_deg=-.1)
    draft = prepare(incoming)
    assert row(draft, "contrast_method").status == row(draft, "response_keys").status == "Invalid"
    assert row(draft, "fixation_ms").status == row(draft, "length_deg").status == "Invalid"
    assert row(draft, "ring_radius_deg").status == row(draft, "width_deg").status == "Out of range"
    assert row(draft, "contrast_method").default == "adaptive"
    assert row(draft, "n_down").status == "Check meaning"
    assert draft.unmapped[("stimuli", "probe", "parameters", "length_deg")] == {"expression": "malicious()"}
    with pytest.raises(ValueError, match="Resolve all"):
        finish(draft, tmp_path, request, profile)
    assert not (tmp_path/"recovered").exists()


def test_unidentified_stimulus_values_and_retired_slots_stay_unmapped():
    request, profile = request_for()
    incoming = make_document(ROOT, request, profile)
    del incoming["stimuli"]["probe"]["stimulus_id"]
    incoming["stimuli"]["retired_slot"] = {"schema_version": 999, "opaque": [42]}
    draft = prepare(incoming)
    assert row(draft, "probe", "stimulus_id").status == "Missing"
    width = row(draft, "probe", "parameters", "width_deg")
    assert width.status == "Ambiguous" and width.suggestion is None
    assert draft.unmapped[width.path] == incoming["stimuli"]["probe"]["parameters"]["width_deg"]
    assert draft.unmapped[("stimuli", "retired_slot")] == incoming["stimuli"]["retired_slot"]
    assert all(item.status != "Compatible" for item in draft.rows)


def test_combined_validation_and_source_changes_prevent_publication(tmp_path):
    request, profile = request_for()
    incoming = make_document(ROOT, request, profile)
    incoming["experiment"]["values"].update(response_keys="1,1")
    draft = prepare(incoming)
    draft.accept_compatible()
    assert not draft.unresolved
    with pytest.raises(ValueError, match="(?i)keys"):
        finish(draft, tmp_path, request, profile)
    row(draft, "response_keys").decide("replace", "1,2")
    draft.local_software["engine_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="source changed"):
        finish(draft, tmp_path, request, profile)
    assert not (tmp_path/"recovered").exists()


def test_ready_laboratory_experiment_and_stimulus_declare_versioned_rules(lab, tmp_path):
    # Add declarations to disposable, trusted source before Test and Ready.
    declaration = (
        '\nfrom psychophysics_lab.configuration_recovery import RecoveryRule\n'
        'CONFIGURATION_RECOVERY_RULES = {(%r, %r): (RecoveryRule(1, "a"*64, "b"*64, '
        '%r, %r, %r, %r, %r, %r, %r, scale=%r),)}\n'
    )
    experiment_source = lab/"experiments"/(EXPERIMENT + ".py")
    with experiment_source.open("a", encoding="utf-8") as stream:
        stream.write(declaration % ("experiment", EXPERIMENT, "old_trials", "trial_count", "int", "", "",
                                     "Number of presented trials", "Only the key changed.", None))
    stimulus_source = lab/"stimulus_library.py"
    with stimulus_source.open("a", encoding="utf-8") as stream:
        stream.write(declaration % ("stimulus", STIMULUS, "length_arcmin", "line_length_deg", "float",
                                     "arcmin", "degrees", "Full line length", "60 arcminutes per degree.", 1/60))
    enable(lab)
    assert execute_user_action(ROOT, "preview", STIMULUS, {}) == 0
    extensions.publish(ROOT, "stimulus", STIMULUS)
    assert execute_user_action(ROOT, "test", EXPERIMENT, {"trial_count": 4}) == 0
    extensions.publish(ROOT, "experiment", EXPERIMENT)

    request, profile = request_for(EXPERIMENT)
    incoming = make_document(ROOT, request, profile)
    incoming["schema_version"] = 1
    incoming["software"].update(source_sha256="a"*64, engine_sha256="b"*64)
    values = incoming["experiment"]["values"]
    del values["trial_count"]
    values["old_trials"] = 4
    target = next(s for s in incoming["stimuli"].values() if s["stimulus_id"] == STIMULUS)["parameters"]
    del target["line_length_deg"]
    target["length_arcmin"] = 90
    draft = prepare(incoming)
    assert row(draft, "trial_count").status == row(draft, "line_length_deg").status == "Declared migration"
    assert row(draft, "trial_count").suggestion == 4 and row(draft, "line_length_deg").suggestion == 1.5
    incoming["software"]["engine_sha256"] = "c"*64
    stale = prepare(incoming)
    assert row(stale, "trial_count").status == row(stale, "line_length_deg").status == "Missing"
    incoming["software"]["engine_sha256"] = "b"*64
    values["trial_count"] = 9
    assert row(prepare(incoming), "trial_count").status == "Ambiguous"
    del values["trial_count"]

    for item in draft.rows:
        item.decide("accept")
    recovered, _, path = finish(draft, tmp_path, request, profile)
    assert recovered.experiment_values["trial_count"] == 4
    assert extensions.status(ROOT, "experiment", EXPERIMENT) == "ready"
    report = read_document(path.parent/"recovery"/"decisions.json")
    assert any(item["rule"] and item["rule"]["old_units"] == "arcmin" for item in report["parameters"])
