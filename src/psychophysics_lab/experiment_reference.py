"""No-code regression references for scientist-authored experiments.

A researcher presses Test, then 'Save as reference'. Subsequent Test results
can be compared to that exact selected-value/seed baseline. No scientist
writes pytest or stores participant data. A difference is shown for *human*
scientific assessment, not automatically declared wrong.

References remain external to the Git checkout; old official baselines and
human acquisition archives are never edited.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from . import extensions


SCIENCE_FILES = ("trials.tsv", "trial_actions.json", "trial_presentations.json")


def source_digest(repo_root, spec):
    """Source identity is deterministic and scoped to declared experiment files."""
    digest = hashlib.sha256()
    digest.update(spec.id.encode("utf-8"))
    for path in sorted(spec.source_paths):
        file = extensions.source_path(repo_root, spec, path)
        if not file.is_file():
            raise ValueError(f"Declared experiment source unavailable: {path}")
        digest.update(path.encode("utf-8"))
        digest.update(file.read_bytes())
    return digest.hexdigest()


def _latest_test(repo_root, identity):
    from .development import user_data_root
    from .experiments._internal.registry import get_experiment
    root = user_data_root(repo_root)
    spec = get_experiment(identity)
    report = root / "software_test_reports" / (identity + ".json")
    if not report.is_file() or report.is_symlink():
        raise ValueError("Run Simulate / validate first to create a current software test.")
    payload = json.loads(report.read_text(encoding="utf-8"))
    if payload.get("experiment_id") != identity or payload.get("result") != "pass":
        raise ValueError("The selected experiment has no successful synthetic Test report.")
    if payload.get("source_digest") != source_digest(repo_root, spec):
        raise ValueError("Scientific Python changed since Test; rerun Simulate / validate first.")
    simulation = payload.get("synthetic_run") or {}
    if simulation.get("passed") is not True or simulation.get("status") != "completed":
        raise ValueError("An incomplete synthetic run cannot form a reference.")
    run = Path(simulation.get("run_directory", ""))
    if not run.is_dir() or run.is_symlink() or not run.resolve().is_relative_to(root.resolve()):
        raise ValueError("Synthetic run directory is missing or outside USER_env_data.")
    digests = {}
    for name in SCIENCE_FILES:
        path = run / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Cannot verify synthetic scientific output: {name}")
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return root, payload, digests


def save_reference(repo_root, identity):
    """Create an immutable named scientific behaviour example after Test."""
    root, report, digests = _latest_test(repo_root, identity)
    folder = root / "scientific_references" / identity
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = folder / (timestamp + ".json")
    reference = {
        "schema_version": 1,
        "experiment_id": identity,
        "scientific_validation": "researcher_review_required",
        "source_digest_when_recorded": report["source_digest"],
        "selected_values": report["selected_values"],
        "synthetic_seed": report["synthetic_seed"],
        "synthetic_accepted_trials": report["synthetic_run"]["accepted_trials"],
        "science_file_sha256": digests,
        "interpretation": (
            "A same-seed software behaviour reference, not scientific approval. "
            "The researcher must inspect intentional changes and qualify real display hardware."
        ),
    }
    # A unique exclusive file keeps earlier named references untouched.
    with target.open("x", encoding="utf-8") as stream:
        json.dump(reference, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return target


def compare_latest_reference(repo_root, identity):
    """Compare a fresh successful Test with the last captured named reference."""
    root, report, digests = _latest_test(repo_root, identity)
    folder = root / "scientific_references" / identity
    paths = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not paths:
        raise ValueError("Save a successful Test as reference before comparing edits.")
    path = paths[-1]
    reference = json.loads(path.read_text(encoding="utf-8"))
    if reference.get("experiment_id") != identity or reference.get("schema_version") != 1:
        raise ValueError("Reference belongs to another experiment or unsupported schema.")
    differences = []
    if reference["selected_values"] != report["selected_values"]:
        differences.append("Selected scientific settings changed.")
    if reference["synthetic_seed"] != report["synthetic_seed"]:
        differences.append("Synthetic observer seed changed.")
    if reference["synthetic_accepted_trials"] != report["synthetic_run"]["accepted_trials"]:
        differences.append("Accepted trial count changed.")
    for name in SCIENCE_FILES:
        if reference["science_file_sha256"].get(name) != digests[name]:
            differences.append(f"Saved synthetic {name} changed.")
    return {
        "reference_path": str(path),
        "same_scientific_behaviour": not differences,
        "differences": differences,
        "reference_source_digest": reference["source_digest_when_recorded"],
        "tested_source_digest": report["source_digest"],
        "note": (
            "A difference is not automatically a bug; decide whether to accept "
            "a new version of the scientific protocol. Equal synthetic hashes "
            "do not prove physically calibrated stimulus presentation."
        ),
    }
