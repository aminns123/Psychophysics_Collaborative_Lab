"""Readable feedback must retain validation, isolation and readiness safeguards."""
import json
from pathlib import Path

import pytest

from psychophysics_lab.experiments._internal.registry import get_experiment
from simulations.run import simulate
from scripts.validate_run import validate_run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identity", ["contrast_sensitivity", "contrast_sensitivity_windowed"])
@pytest.mark.parametrize("frequencies,valid", [
    ("0.5,32", True), ("0.499,2", False), ("2,32.001", False),
    ("2,nan", False), ("2,inf", False), ("2,2", False),
])
def test_csf_frequency_bounds_and_readable_error(identity, frequencies, valid):
    spec = get_experiment(identity)
    values = {"frequencies_cpd": frequencies}
    if valid:
        assert spec.normalise_values(values)["frequencies_cpd"] == frequencies
    else:
        with pytest.raises(ValueError, match="0.5-32 cycles/degree") as error:
            spec.normalise_values(values)
        assert str(error.value).isascii()
    assert values == {"frequencies_cpd": frequencies}


@pytest.mark.parametrize("fault,error_type", [
    ("missing", ValueError), ("invalid", SyntaxError), ("stale", ValueError),
])
def test_published_source_warning_preserves_failure_and_other_study(tmp_path, monkeypatch, fault, error_type):
    from psychophysics_lab import authoring, contributions, extensions, paths
    from psychophysics_lab.adaptive import registry as adaptive
    from psychophysics_lab.stimuli import registry as stimuli
    from psychophysics_lab.experiments._internal import contributions as loader, registry, library_builder

    get_experiment("contrast_sensitivity")  # Load genuine valid official definitions first.
    for module in (registry, stimuli, adaptive):
        monkeypatch.setattr(module, "_REGISTRY", dict(module._REGISTRY))
    name = "issue140_" + fault
    source = tmp_path / "src/psychophysics_lab/experiments" / (name + ".py")
    source.parent.mkdir(parents=True)
    if fault != "missing":
        source.write_text("def unfinished(\n" if fault == "invalid" else "SPEC = None\n", encoding="utf-8")
    manifest = tmp_path / authoring.MANIFEST
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"schema_version": 1, "components": [
        {"kind": "experiment", "name": name, "status": "ready", "tested_fingerprint": "old-revision"},
    ]}), encoding="utf-8")
    original_manifest = manifest.read_bytes()
    original_source = source.read_bytes() if source.exists() else None
    monkeypatch.setattr(paths, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(loader, "_loaded", False)
    monkeypatch.setattr(contributions, "EXPERIMENT_MODULES", ())
    monkeypatch.setattr(contributions, "ADAPTIVE_MODULES", ())
    monkeypatch.setattr(library_builder, "load_library", lambda **kwargs: {})
    monkeypatch.setattr(extensions, "load", lambda root: {})

    with pytest.warns(RuntimeWarning, match="published components") as caught:
        loader.load_contributions()
    message = str(caught[0].message)
    assert f"experiment:{name}" in message
    assert error_type.__name__ in message
    assert "other valid experiments remain available" in message
    assert "known, reviewed Git revision" in message
    assert "restart PsyCoLab" in message and "Draft/Test/Ready" in message
    assert "not approved automatically" in message
    assert name not in registry._REGISTRY

    # A genuine selected-study run still executes and validates after the warning.
    artifacts = simulate(repo_root=ROOT, data_root=tmp_path / "data",
        experiment_id="contrast_sensitivity", values={"contrast_method": "constant_stimuli",
            "frequencies_cpd": "2", "fixed_contrasts": "0.1", "fixed_repetitions": 2}, analyse=False)[0]
    assert artifacts.accepted_trials == 2
    assert artifacts.status == "completed"
    assert not [check for check in validate_run(artifacts.run_directory) if not check.passed]
    # Strict callers retain the original failure; nothing restores or certifies source.
    with pytest.raises(error_type):
        authoring.load_authored(tmp_path)
    assert manifest.read_bytes() == original_manifest
    assert (source.read_bytes() if source.exists() else None) == original_source
