"""Calibration measurement templates and researcher-facing Textual interactions."""
from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path

import pytest
from textual.widgets import Button, Input, Select, Static

from psychophysics_lab.config.calibration_templates import (
    example_luminance_document, parse_luminance_measurements,
    read_luminance_measurements, template_identity, write_luminance_example
)
from psychophysics_lab.config.monitor import load_monitor_profiles
from psychophysics_lab.core.display_tests import resolve_test
from psychophysics_lab.core.geometry_check import GeometryCheckRequest, record_geometry_measurement
from psychophysics_lab.ui.profiles import ProfileScreen
from psychophysics_lab.ui.setup import DisplayCheckScreen, PsyCoLabSetupApp

ROOT = Path(__file__).resolve().parents[1]


def reference():
    return load_monitor_profiles(ROOT)["legacy_reference_display"]


def finished_document(profile):
    document = example_luminance_document(profile)
    document.update(
        photometer_model_and_method="Photometer XYZ-1; centre patch, stabilised screen",
        measurement_date="2026-10-13",
        notes="Measured after warm-up, fixed OS brightness. Uncertainty to be reviewed.",
    )
    for command, row in zip((0, .25, .5, .75, 1), document["measurements"]):
        row["luminance_cdm2"] = 2 + 320 * (command ** 2.2)
    return document


def test_luminance_example_is_unusable_until_measured_and_never_overwritten(tmp_path):
    p = reference()
    example = write_luminance_example(tmp_path, p)
    assert example.is_file()
    document = json.loads(example.read_text())
    assert document["monitor_profile_id"] == "legacy_reference_display_local"
    assert all(row["luminance_cdm2"] is None for row in document["measurements"])
    with pytest.raises(ValueError, match="At least two REAL"):
        parse_luminance_measurements(document, p)

    recorded = finished_document(p)
    example.write_text(json.dumps(recorded), encoding="utf-8")
    assert write_luminance_example(tmp_path, p) == example
    assert json.loads(example.read_text()) == recorded
    result = read_luminance_measurements(str(example), p)
    assert len(result["luminance_calibration"]) == 5
    assert result["calibration_status"] == "manual_unverified"
    assert result["calibration_date"] == "2026-10-13"


@pytest.mark.parametrize("change,pattern", [
    (lambda d:d.update(measurement_date="not-a-date"), "date"),
    (lambda d:d["measurements"][0].update(luminance_cdm2="not-numeric"), "measured JSON number"),
    (lambda d:d["measurements"][0].update(screen_intensity=2.0), "intensity"),
    (lambda d:d["measurements"][0].update(luminance_cdm2=999.), "increase monotonically"),
    (lambda d:d["measurements"][1].update(screen_intensity=0.), "distinct"),
    (lambda d:d.update(monitor_profile_id="different_monitor"), "another profile"),
    (lambda d:d.update(based_on_revision=4), "another profile"),
])
def test_invalid_files_fail_without_importing_anything(change,pattern):
    p = reference()
    d = finished_document(p)
    change(d)
    with pytest.raises(ValueError, match=pattern):
        parse_luminance_measurements(d,p)


def test_luminance_document_is_bound_to_profile_revision():
    p = reference()
    d = finished_document(p)
    local = replace(p,id="legacy_reference_display_local",origin="local",revision=1)
    with pytest.raises(ValueError,match="another profile/revision"):
        parse_luminance_measurements(d,local)


def test_photometry_patch_exact_normalized_command_and_no_fake_measurement():
    p = reference()
    for c in (0., .25, .5, 1.):
        request=GeometryCheckRequest(p.id,"visual_angle_deg",5.,
                                     test_kind="luminance_patch",digital_command=c)
        bar, plan=resolve_test(p,request,(1920,1080))
        assert plan["luminance_patch"]["digital_command"] == c
        assert plan["luminance_patch"]["patch_rgb"]==[c,c,c]
        assert plan["photometric_verified"] is False
        assert plan["luminance_patch"]["photometry_verified"] is False
    for c in (-.01,1.001,float("nan")):
        with pytest.raises(ValueError,match="digital command"):
            resolve_test(p,GeometryCheckRequest(
                p.id,"visual_angle_deg",5.,test_kind="luminance_patch",
                digital_command=c),(1920,1080))


def test_ruler_measurement_cannot_be_attached_to_a_photometer_diagnostic(tmp_path):
    directory=tmp_path/"diagnostics"/"display_geometry"/"example"/"check_001"
    directory.mkdir(parents=True)
    report=directory/"geometry_check.json"
    report.write_text(json.dumps({
        "request":{"test_kind":"luminance_patch"},
        "resolved_bar":{"intended_length_mm":43.66},
    }))
    with pytest.raises(ValueError,match="Size or Position"):
        record_geometry_measurement(data_root=tmp_path,
                                    report_file=report,measured_length_mm=50.)
    assert "measurement" not in json.loads(report.read_text())


def test_tui_create_open_load_save_roundtrip_preserves_unverified_status(tmp_path, monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR",str(tmp_path/"machine"))
    seen=[]
    monkeypatch.setattr(os,"startfile",lambda path: seen.append(path),raising=False)

    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(106,32)) as pilot:
            app.query_one("#nav-display",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            app.screen.query_one("#edit-profile",Button).press()
            await pilot.pause()
            editor=app.screen
            assert isinstance(editor,ProfileScreen)
            editor.query_one("#profile-luminance-example",Button).press()
            await pilot.pause()
            path=Path(editor.query_one("#profile-luminance-path",Input).value)
            assert path.is_file()
            assert path.is_relative_to((tmp_path/"machine").resolve())
            path.write_text(json.dumps(finished_document(editor.profile)),encoding="utf-8")
            editor.query_one("#profile-luminance-load",Button).press()
            await pilot.pause()
            assert editor.query_one("#profile-calibration_status",Select).value=="manual_unverified"
            assert editor.query_one("#profile-calibration_method",Input).value.startswith("Photometer")
            assert editor.query_one("#profile-calibration_date",Input).value=="2026-10-13"
            assert len(json.loads(editor.query_one("#profile-luminance",Input).value))==5
            assert "UNSAVED" in str(editor.query_one("#profile-luminance-feedback",Static).render())
            editor.query_one("#profile-save",Button).press()
            await pilot.pause()
            assert isinstance(app.screen,DisplayCheckScreen)
            p=app.monitor_profiles["legacy_reference_display_local"]
            assert p.revision==1
            assert p.calibration_status=="manual_unverified"
            assert len(p.luminance_calibration)==5
            assert not p.has_verified_luminance_mapping
            assert p.qualified_experiments==()
            assert p.calibration_method.startswith("Photometer")
            assert p.calibration_date=="2026-10-13"
            assert list((tmp_path/"machine"/"profiles"/p.id).glob("revision_*.json"))
    asyncio.run(scenario())


def test_invalid_tui_load_cannot_mutate_existing_draft(tmp_path,monkeypatch):
    monkeypatch.setenv("PSYCOLAB_CONFIG_DIR",str(tmp_path/"machine"))
    monkeypatch.setattr(os,"startfile",lambda path: None,raising=False)
    async def scenario():
        app=PsyCoLabSetupApp(repo_root=ROOT,data_root=tmp_path/"data")
        async with app.run_test(size=(106,32)) as pilot:
            app.query_one("#nav-display",Button).press()
            await pilot.pause()
            app.screen.query_one("#edit-profile",Button).press()
            await pilot.pause()
            editor=app.screen
            editor.query_one("#profile-luminance-example",Button).press()
            await pilot.pause()
            original=editor.query_one("#profile-luminance",Input).value
            editor.query_one("#profile-luminance-load",Button).press()
            await pilot.pause()
            assert editor.query_one("#profile-luminance",Input).value==original
            assert "NOT loaded" in str(editor.query_one("#profile-save-feedback",Static).render())
    asyncio.run(scenario())


def test_real_values_import_with_no_method_notes_or_date_and_unused_blank_rows():
    p = reference()
    document = example_luminance_document(p)
    document["measurements"][0]["luminance_cdm2"] = 1.2
    document["measurements"][3]["luminance_cdm2"] = 87.1
    result = parse_luminance_measurements(document, p)
    assert len(result["luminance_calibration"]) == 2
    assert result["luminance_calibration"][1]["screen_intensity"] == .75
    assert result["calibration_method"] == ""
    assert result["calibration_notes"] == ""
    assert result["calibration_date"] == ""
    assert result["calibration_status"] == "manual_unverified"
    assert len(result["warnings"]) >= 3


def test_one_observed_pair_is_not_a_usable_luminance_mapping():
    p = reference()
    document = example_luminance_document(p)
    document["measurements"][0]["luminance_cdm2"] = .5
    with pytest.raises(ValueError, match="At least two REAL"):
        parse_luminance_measurements(document, p)




def test_earlier_luminance_file_survives_metadata_only_profile_saves(tmp_path):
    """Regression: the user's JSON targets revision 11, but current profile is 14."""
    from psychophysics_lab.config.local import save_profile
    from psychophysics_lab.config.calibration_workflow import import_and_save_luminance

    root = tmp_path / "local_settings"
    initial = replace(reference(), id="measured_monitor", origin="local")
    current = save_profile(root, initial)
    for index in range(2, 12):
        current = save_profile(
            root, replace(current, notes=f"Unrelated note {index}"),
            expected_revision=current.revision,
        )
    assert current.revision == 11
    document = finished_document(current)
    path = tmp_path / "luminance_readings_from_rev11.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    # These are versioned app metadata edits; no physical geometry was changed.
    for index in range(12, 15):
        current = save_profile(
            root, replace(current, notes=f"New unrelated note {index}"),
            expected_revision=current.revision,
        )
    assert current.revision == 14

    # External parsers without access to saved historical evidence stay strict.
    with pytest.raises(ValueError, match="another profile/revision"):
        read_luminance_measurements(str(path), current)
    parsed = read_luminance_measurements(
        str(path), current, local_config_root=root
    )
    assert len(parsed["luminance_calibration"]) == 5
    assert any("revision 11" in warning for warning in parsed["warnings"])

    persisted, warnings = import_and_save_luminance(current, root, str(path))
    assert persisted.revision == 15
    assert persisted.calibration_status == "manual_unverified"
    assert len(persisted.luminance_calibration) == 5
    assert any("brightness" in text.lower() for text in warnings)
    assert json.loads(path.read_text(encoding="utf-8")) == document


def test_old_luminance_file_rejected_when_physical_setup_changed_and_returned(tmp_path):
    """Matching current configuration is insufficient if an intervening revision changed."""
    from psychophysics_lab.config.local import save_profile

    root = tmp_path / "local_settings"
    old = save_profile(root, replace(reference(), id="geometry_monitor", origin="local"))
    document = finished_document(old)
    path = tmp_path / "old_screen.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    changed = save_profile(
        root, replace(old, viewing_distance_m=old.viewing_distance_m + .1),
        expected_revision=old.revision
    )
    reverted = save_profile(
        root, replace(changed, viewing_distance_m=old.viewing_distance_m),
        expected_revision=changed.revision
    )
    with pytest.raises(ValueError, match="physical setup changed"):
        read_luminance_measurements(
            str(path), reverted, local_config_root=root
        )
    assert json.loads(path.read_text(encoding="utf-8")) == document


def test_old_luminance_file_rejected_when_revisions_missing(tmp_path):
    from psychophysics_lab.config.local import save_profile

    root = tmp_path / "local_settings"
    old = save_profile(root, replace(reference(), id="history_monitor", origin="local"))
    document = finished_document(old)
    path = tmp_path / "old_photometry.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    current = save_profile(
        root, replace(old, notes="Saved a new note"), expected_revision=old.revision
    )
    (root / "profiles" / old.id / "revision_000001.json").unlink()
    with pytest.raises(ValueError, match="revision 1 is missing"):
        read_luminance_measurements(str(path), current, local_config_root=root)


def test_fake_method_warns_and_does_not_certify_human_photometry():
    document = finished_document(reference())
    document["photometer_model_and_method"] = "fake_photometer"
    parsed = parse_luminance_measurements(document, reference())
    assert parsed["calibration_status"] == "manual_unverified"
    assert any("synthetic" in warning for warning in parsed["warnings"])
