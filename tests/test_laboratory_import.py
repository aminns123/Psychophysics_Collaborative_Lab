"""Import and proposal are filesystem operations, not Python execution.

A new researcher needs no pytest knowledge: these are maintainer tests for the
generic mechanism which the TUI invokes for every laboratory experiment.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from psychophysics_lab import extensions
from psychophysics_lab.laboratory_import import (
    import_experiment, prepare_official_contribution,
)


@pytest.fixture()
def lab(tmp_path, monkeypatch):
    root = tmp_path / "PsyCoLab_Extensions"
    (root / "experiments").mkdir(parents=True)
    (root / "stimulus_library.py").write_text(
        "# Independent laboratory stimulus classes.\n", encoding="utf-8"
    )
    monkeypatch.setattr(extensions, "configured", lambda repo_root, data_root=None: (root, "demolab"))
    return root


def test_import_existing_experiment_without_executing_python(tmp_path, lab):
    source = tmp_path / "demolab__ellipse.py"
    text = (
        "raise RuntimeError('do NOT execute on copy')\n"
        "SPEC = definition()\n"
    )
    source.write_text(text, encoding="utf-8")
    imported = import_experiment(tmp_path, source)
    assert imported["id"] == "demolab__ellipse"
    assert imported["status"] == "draft"
    assert (lab / "experiments" / source.name).read_bytes() == source.read_bytes()
    assert "exact" not in imported["status"]
    with pytest.raises(ValueError, match="already exists"):
        import_experiment(tmp_path, source)
    assert (lab / "experiments" / source.name).read_text() == text


def test_bad_namespace_and_missing_spec_rejected_without_writes(tmp_path, lab):
    short = tmp_path / "ellipse.py"
    short.write_text("SPEC = definition()\n", encoding="utf-8")
    with pytest.raises(ValueError, match="named demolab__"):
        import_experiment(tmp_path, short)

    malformed = tmp_path / "demolab__bad.py"
    malformed.write_text("def missing_spec(): pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level SPEC"):
        import_experiment(tmp_path, malformed)
    malformed.write_text("SPEC = (\n", encoding="utf-8")
    with pytest.raises(ValueError, match="syntax/encoding"):
        import_experiment(tmp_path, malformed)
    assert not list((lab / "experiments").glob("*.py"))


def test_conventional_spec_id_mismatch_is_explained_before_copy(tmp_path, lab):
    file = tmp_path / "demolab__ellipse.py"
    file.write_text(
        'SPEC = experiment(id="ellipse", name="An ellipse")\\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="SPEC.id"):
        import_experiment(tmp_path, file)
    file.write_text(
        'def definition(identity="ellipse"):\\n'
        '    return experiment(id=identity)\\n'
        'SPEC = definition()\\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="default ID"):
        import_experiment(tmp_path, file)
    assert not (lab / "experiments" / file.name).exists()


def test_disabled_laboratory_cannot_import(tmp_path, lab, monkeypatch):
    monkeypatch.setattr(extensions, "configured", lambda repo_root, data_root=None: None)
    file = tmp_path / "demolab__my_study.py"
    file.write_text("SPEC = definition()\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Enable and explicitly trust"):
        import_experiment(tmp_path, file)


def test_import_rejects_symlink_and_never_overwrites(tmp_path, lab):
    file = tmp_path / "demolab__good.py"
    file.write_text("SPEC = definition()\n", encoding="utf-8")
    link = tmp_path / "demolab__alias.py"
    try:
        link.symlink_to(file)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this Windows host.")
    with pytest.raises(ValueError, match="Symlink/junction"):
        import_experiment(tmp_path, link)
    assert not (lab / "experiments" / link.name).exists()


def test_contribution_requires_exact_software_ready(tmp_path, lab, monkeypatch):
    identity = "demolab__ellipse"
    src = lab / "experiments" / (identity + ".py")
    src.write_text("SPEC = definition()\n", encoding="utf-8")
    monkeypatch.setattr(extensions, "status", lambda repo, kind, identity: "draft")
    with pytest.raises(ValueError, match="Ready"):
        prepare_official_contribution(tmp_path, identity)
    assert not (lab / "contribution_proposals").exists()


def test_contribution_preserves_local_id_and_includes_relevant_stimulus(tmp_path, lab, monkeypatch):
    from psychophysics_lab.experiments._internal import registry as experiments
    from psychophysics_lab.stimuli import registry as stimuli

    identity = "demolab__ellipse"
    source = lab / "experiments" / (identity + ".py")
    source.write_text("SPEC = definition()\n", encoding="utf-8")
    stimulus_code = "class LaboratoryEllipse: pass\n"
    (lab / "stimulus_library.py").write_text(stimulus_code, encoding="utf-8")

    # The Test -> Ready mechanism owns this state; no import function may
    # invent it or bypass the existing exact-source fingerprint.
    monkeypatch.setattr(extensions, "status", lambda repo, kind, name: "ready")
    monkeypatch.setattr(extensions, "fingerprint", lambda repo: "f"*64)
    monkeypatch.setattr(
        extensions, "source_hashes",
        lambda repo: {
            "experiments/demolab__ellipse.py": "a"*64,
            "stimulus_library.py": "b"*64,
        },
    )
    monkeypatch.setattr(
        experiments, "get_experiment",
        lambda name: SimpleNamespace(
            origin_namespace="demolab", historical=False,
            stimulus_defaults={"ellipse": "demolab__ellipse_ring", "fixation": "fixation_cross"},
        ),
    )
    monkeypatch.setattr(
        stimuli, "get_stimulus",
        lambda name: SimpleNamespace(
            origin_namespace="demolab" if name.startswith("demolab__") else "",
            id=name,
        ),
    )
    folder = prepare_official_contribution(tmp_path, identity)
    result = json.loads((folder / "contribution_manifest.json").read_text())
    assert result["status"] == "not_merged_not_official"
    assert result["proposed_official"]["experiment_id"] == "ellipse"
    assert result["proposed_official"]["stimulus_id_mappings_for_review"] == {
        "demolab__ellipse_ring": "ellipse_ring"
    }
    assert (folder / "experiments" / (identity + ".py")).read_bytes() == source.read_bytes()
    assert (folder / "stimulus_library.py").read_text() == stimulus_code
    assert (lab / "stimulus_library.py").read_text() == stimulus_code
    with pytest.raises(ValueError, match="already exists"):
        prepare_official_contribution(tmp_path, identity)
