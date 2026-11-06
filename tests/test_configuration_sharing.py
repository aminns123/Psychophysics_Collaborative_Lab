"""Portable science uses the existing validated configuration and execution path."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.config.preflight import validate_setup
from psychophysics_lab.config.sharing import (MAX_BYTES, digest, make_document, read_document,
                                            save_local, software_identity, validate_portable, write_export)
from psychophysics_lab.config.stimulus_parameters import document_for, snapshot
from psychophysics_lab.experiments._internal.registry import get_experiment
from psychophysics_lab.stimuli.registry import get_stimulus
from test_parameter_accessibility import OFFICIAL, selected_values

ROOT = Path(__file__).resolve().parents[1]


def request_for(identity="ellipse_centre"):
    spec = get_experiment(identity)
    profile = load_monitor_profiles(ROOT)["legacy_reference_display"]
    request = SetupRequest("PRIVATE_PARTICIPANT", "new", identity, profile.id, selected_values(spec),
                           data_root="C:/PRIVATE_DATA", show_response_instructions=False)
    return validate_setup(request, spec, profile, mode="configuration"), profile


@pytest.mark.parametrize("identity", OFFICIAL)
def test_all_official_complete_round_trip(identity, tmp_path):
    request, profile = request_for(identity)
    document = make_document(ROOT, request, profile)
    output = tmp_path/"shared settings.json"
    write_export(output, document)
    assert read_document(output) == document
    # The recipient's own identity, workspace, display and qualification survive.
    other_profile = replace(profile, id="other_laboratory_display")
    apparatus_before = deepcopy(other_profile.to_dict())
    recipient = replace(request, participant_id="RECIPIENT", data_root=str(tmp_path/"other data"),
                        monitor_profile_id=other_profile.id, monitor_profile_hash=None)
    imported, warnings = validate_portable(read_document(output), ROOT, recipient, other_profile)
    assert not warnings
    assert imported.experiment_values == request.experiment_values
    assert {s: v["document"] for s, v in imported.stimulus_snapshots.items()} == document["stimuli"]
    assert imported.participant_id == recipient.participant_id and imported.data_root == recipient.data_root
    assert imported.monitor_profile_id == other_profile.id
    assert other_profile.to_dict() == apparatus_before
    assert imported.researcher_override is None and imported.show_response_instructions is False
    encoded = output.read_text()
    for secret in ("PRIVATE_PARTICIPANT", "PRIVATE_DATA", "legacy_reference_display", str(ROOT), "monitor_profile", "display_binding"):
        assert secret not in encoded
    assert set(document["experiment"]["values"]) == {f.key for f in get_experiment(identity).fields}
    saved, files, archive = save_local(tmp_path/"local configuration", ROOT, document, recipient, other_profile)
    assert make_document(ROOT, saved, other_profile) == document
    assert read_document(archive) == document and archive.is_file()
    assert len(files) == len(saved.stimulus_snapshots) + 2
    from psychophysics_lab.ui.parameter_files import ensure_unchanged, load_experiment_json
    ensure_unchanged(files)
    assert load_experiment_json(archive.parent/"experiment.json", get_experiment(identity)) == request.experiment_values


@pytest.mark.parametrize("mutation,match", [
    (lambda d: d.update(schema_version=True), "Unsupported"),
    (lambda d: d.update(schema_version=99), "Unsupported"),
    (lambda d: d.update(participant_id="stolen"), "expected exactly"),
    (lambda d: d.update(python="__import__('os').system('anything')"), "expected exactly"),
    (lambda d: d["experiment"].update(experiment_id="../../missing.py"), "not installed"),
    (lambda d: d["experiment"]["values"].pop("ring_radius_deg"), "missing parameters"),
    (lambda d: d["experiment"]["values"].update(ring_radius_deg=-1), "range|positive|radius"),
    (lambda d: d["experiment"]["values"].update(ring_radius_deg={"code":"execute"}), "explicit"),
    (lambda d: d["experiment"]["values"].update(unknown_setting=1), "unsupported parameters"),
    (lambda d: d["stimuli"].pop("probe"), "every declared stimulus"),
    (lambda d: d["stimuli"]["probe"].update(stimulus_id="download.this.module"), "not installed"),
    (lambda d: d["stimuli"]["probe"]["parameters"].pop("width_deg"), "missing parameters"),
    (lambda d: d["stimuli"]["probe"]["parameters"].update(width_deg=-.1), "range|positive"),
    (lambda d: d["stimuli"]["probe"].update(source_path="evil.py"), "expected exactly"),
    (lambda d: d["software"].update(source_sha256="0"*64), "Incompatible"),
    (lambda d: d["software"].update(engine_sha256="0"*64), "Incompatible"),
    (lambda d: d["software"]["dependencies"].update(numpy="0.0"), "Incompatible"),
    (lambda d: d["presentation"].update(show_response_instructions="true"), "boolean"),
])
def test_invalid_import_cannot_write_or_change_working_settings(tmp_path, mutation, match):
    request, profile = request_for()
    original = deepcopy(request)
    document = make_document(ROOT, request, profile)
    mutation(document)
    sentinel = tmp_path/"existing data.txt"
    sentinel.write_text("Preserve historical research data")
    with pytest.raises(ValueError, match=match):
        save_local(tmp_path/"local", ROOT, document, request, profile)
    assert request == original and not (tmp_path/"local").exists()
    assert sentinel.read_text() == "Preserve historical research data"


@pytest.mark.parametrize("raw", [b'{', b'[]', b'{"format":1,"format":2}', b'{"a":NaN}', b'{"a":1e999}', b'\xff', b'['*1200+b']'*1200])
def test_malformed_json_is_rejected(tmp_path, raw):
    path = tmp_path/"bad.json"
    path.write_bytes(raw)
    if raw == b'[]':
        request, profile = request_for()
        with pytest.raises(ValueError, match="Configuration"):
            validate_portable(read_document(path), ROOT, request, profile)
    else:
        with pytest.raises(ValueError):
            read_document(path)


def test_export_never_overwrites_and_import_size_is_bounded(tmp_path):
    path = tmp_path/"existing.json"
    path.write_bytes(b"original")
    with pytest.raises(ValueError, match="already exists"):
        write_export(path, {})
    assert path.read_bytes() == b"original"
    path.write_bytes(b" "*(MAX_BYTES+1))
    with pytest.raises(ValueError, match="size limit"):
        read_document(path)


def test_save_is_new_transaction_and_failed_write_preserves_previous(tmp_path, monkeypatch):
    request, profile = request_for()
    document = make_document(ROOT, request, profile)
    local = tmp_path/"local"
    first = save_local(local, ROOT, document, request, profile)
    before = {p: p.read_bytes() for p in local.rglob("*.json")}
    import psychophysics_lab.data.session as session
    write = session.atomic_write_json
    count = 0
    def failed(path, data):
        nonlocal count
        count += 1
        if count == 3:
            raise OSError("Deliberate disposable save failure")
        return write(path, data)
    monkeypatch.setattr(session, "atomic_write_json", failed)
    with pytest.raises(OSError, match="Deliberate"):
        save_local(local, ROOT, document, request, profile)
    assert {p: p.read_bytes() for p in local.rglob("*.json")} == before
    assert not list(local.rglob(".configuration_*"))
    monkeypatch.setattr(session, "atomic_write_json", write)
    second = save_local(local, ROOT, document, request, profile)
    assert second[2] != first[2]
    assert all(p.read_bytes() == value for p, value in before.items())


def test_compatibility_uses_portable_source_identity_and_accepts_version_label_only_change(tmp_path):
    request, profile = request_for()
    document = make_document(ROOT, request, profile)
    other = tmp_path/"different computer and folder"
    shutil.copytree(ROOT/"src", other/"src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT/"configs", other/"configs")
    for path in (other/"src").rglob("*.py"):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    assert software_identity(other, get_experiment(request.experiment_id), request.stimulus_snapshots) == document["software"]
    imported, _ = validate_portable(document, other, request, profile)
    assert make_document(other, imported, profile) == document
    modified = other/"src/psychophysics_lab/experiments/ellipse_centre.py"
    modified.write_bytes(modified.read_bytes()+b"\n# Different scientific implementation\n")
    with pytest.raises(ValueError, match="Incompatible"):
        validate_portable(document, other, request, profile)
    document["software"]["psycolab_version"] = "compatible-version-label"
    _, warnings = validate_portable(document, ROOT, request, profile)
    assert len(warnings) == 1 and "fingerprints match" in warnings[0]


def test_missing_local_dependency_and_invalid_local_geometry_do_not_create_saves(tmp_path, monkeypatch):
    request, profile = request_for()
    document = make_document(ROOT, request, profile)
    import psychophysics_lab.config.sharing as sharing
    def absent(name):
        raise sharing.PackageNotFoundError(name)
    with monkeypatch.context() as patch:
        patch.setattr(sharing, "version", absent)
        with pytest.raises(ValueError, match="dependency is missing"):
            save_local(tmp_path/"local", ROOT, document, request, profile)
    # Geometry remains the recipient's measured apparatus. A malformed local
    # profile cannot be made valid by importing someone else's chosen settings.
    invalid = replace(profile, viewing_distance_m=0)
    with pytest.raises(ValueError):
        save_local(tmp_path/"local", ROOT, document, request, invalid)
    assert not (tmp_path/"local").exists()


def test_shared_configuration_does_not_qualify_human_acquisition():
    request, profile = request_for()
    before = deepcopy(profile.to_dict())
    candidate, _ = validate_portable(make_document(ROOT, request, profile), ROOT, request, profile)
    with pytest.raises(ValueError):
        validate_setup(candidate, get_experiment(candidate.experiment_id), profile, mode="human")
    assert profile.to_dict() == before


def test_documented_ellipse_example_is_a_working_portable_configuration():
    request, profile = request_for()
    document = read_document(ROOT/"docs/examples/ellipse_centre_configuration.json")
    imported, _ = validate_portable(document, ROOT, request, profile)
    assert imported.stimulus_snapshots["probe"]["document"]["parameters"]["length_deg"] == 1.4
    assert imported.stimulus_snapshots["probe"]["document"]["parameters"]["width_deg"] == .035


def test_ellipse_shared_dimensions_adaptive_trace_and_saved_provenance(tmp_path):
    request, profile = request_for()
    request = replace(request, experiment_values=request.experiment_values | {"max_trials": 12, "staircases_per_condition": 1})
    selected = dict(request.stimulus_snapshots)
    parameters = selected["probe"]["document"]["parameters"] | {"length_deg": 1.4, "width_deg": .035}
    selected["probe"] = snapshot(document_for(get_stimulus("probe_line"), parameters), file_identity="tui_values")
    request = replace(request, stimulus_snapshots=selected)
    document = make_document(ROOT, request, profile)
    imported, _, _ = save_local(tmp_path/"recipient configuration", ROOT, document, request, profile)
    from simulations.run import simulate
    results = []
    for name, chosen in (("source", request), ("recipient", imported)):
        result, _ = simulate(repo_root=ROOT, data_root=tmp_path/name, experiment_id=chosen.experiment_id,
            values=chosen.experiment_values, stimulus_snapshots=chosen.stimulus_snapshots, seed=41, analyse=False,
            configuration_origin=chosen.configuration_origin, show_response_instructions=chosen.show_response_instructions)
        results.append(result)
    assert results[0].trial_log_file.read_bytes() == results[1].trial_log_file.read_bytes()
    for name in ("trial_actions.json", "trial_presentations.json", "adaptive_session.json"):
        assert (results[0].run_directory/name).read_bytes() == (results[1].run_directory/name).read_bytes()
    saved = json.loads((results[1].run_directory/"experiment_config.json").read_text())["request"]
    assert saved["configuration_origin"]["document_sha256"] == digest(document)
    assert saved["experiment_values"] == imported.experiment_values
    assert saved["stimulus_snapshots"] == imported.stimulus_snapshots
    assert saved["show_response_instructions"] is False
    assert '"length_deg": 1.4' in (results[1].run_directory/"trial_events.jsonl").read_text()
    from scripts.validate_run import validate_run
    assert all(c.passed for c in validate_run(results[1].run_directory))
