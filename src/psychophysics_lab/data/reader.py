"""Read archived PsyCoLab run data without importing the experiment runner.

The public loader is deliberately permissive about additional trial columns:
their values are preserved as text rather than guessed into scientific types.
The separate validate_run script performs strict acquisition integrity checks.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import numpy as np


# The established 20-column acquisition table is trial schema 1. A newer,
# semantically different schema needs an explicit reader review before use.
SUPPORTED_TRIAL_SCHEMA_VERSIONS = frozenset({1})
# Reading manifest fields is intentionally opaque; the reader can hand back
# historical positive versions, but cannot safely accept an unknown NEWER
# format as though its fields still had current meanings.
LATEST_KNOWN_MANIFEST_SCHEMA_VERSION = 3


def _check_laboratory_provenance(manifest: dict[str, Any]) -> None:
    """Check only the known v1 *format*, without fetching or trusting source.

    This is not a certificate that the saved hashes match any present-day
    experiment or that an original laboratory display was calibrated.
    """
    if "laboratory_extensions" not in manifest:
        return  # Runs before Issue #80 have no such metadata.
    evidence = manifest["laboratory_extensions"]
    if not isinstance(evidence, dict) or (
        type(evidence.get("schema_version")) is not int
        or evidence["schema_version"] != 1
    ):
        version = evidence.get("schema_version") if isinstance(evidence, dict) else None
        raise ValueError(
            f"Unsupported laboratory_extensions schema_version {version!r}; "
            "read with the matching PsyCoLab provenance format."
        )
    identity = evidence.get("experiment_identity")
    components = evidence.get("components")
    hashes = evidence.get("source_sha256")
    if (
        evidence.get("origin") != "laboratory"
        or not isinstance(evidence.get("namespace"), str)
        or not evidence["namespace"]
        or not isinstance(evidence.get("fingerprint"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", evidence["fingerprint"])
        or not isinstance(identity, dict)
        or not all(isinstance(identity.get(key), str) and identity[key]
                   for key in ("namespace", "id"))
        or not isinstance(components, list) or not components
        or not all(
            isinstance(item, dict)
            and item.get("kind") in {"experiment", "stimulus"}
            and all(isinstance(item.get(key), str) and item[key]
                    for key in ("id", "namespace", "software_status"))
            for item in components
        )
        or not isinstance(hashes, dict) or not hashes
    ):
        raise ValueError(
            "Malformed laboratory_extensions schema 1 provenance; "
            "original recorded metadata must be inspected, not reconstructed."
        )
    for name, digest in hashes.items():
        if (
            not isinstance(name, str) or not name or "\\" in name
            or ":" in name or name.startswith("/")
            or ".." in PurePosixPath(name).parts
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError(
                "Malformed laboratory_extensions source_sha256 path or digest; "
                "do not infer source identity from installed files."
            )


def _read_table(path: Path, *, require_column: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = reader.fieldnames
        if not columns or any(not name for name in columns) or len(set(columns)) != len(columns):
            raise ValueError(f"Missing, empty or repeated TSV column name: {path}")
        if require_column and require_column not in columns:
            raise ValueError(f"Missing required {require_column!r} column: {path}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Malformed TSV row (wrong number of fields): {path}")
    return columns, rows


def load_run(path: str | Path) -> dict[str, Any]:
    """Load a run directory (or its trials.tsv) into dictionaries and arrays.

    Returns:
      trials: dict[str, numpy.ndarray] (one text array per actual TSV column)
      manifest: the saved dict, or {} for an older run without a manifest
      data_dictionary: dict keyed by column name, or {} when unavailable
      run_directory: Path to the run folder

    This is a read-only analysis helper, NOT a validation of physical timing,
    calibration, or provenance. Convert numerical columns explicitly with
    astype(float) / astype(int) once their recorded meanings are known.
    """
    supplied = Path(path).expanduser()
    run_directory = supplied if supplied.is_dir() else supplied.parent if supplied.name == "trials.tsv" else None
    if run_directory is None:
        raise ValueError("Supply a run_NNN directory or its trials.tsv file.")
    trials_path = run_directory / "trials.tsv"
    if not trials_path.is_file():
        raise FileNotFoundError(f"Cannot find canonical trials.tsv: {trials_path}")

    manifest_path = run_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.exists() else {}
    if not isinstance(manifest, dict):
        raise ValueError("manifest.json must contain a JSON object.")
    manifest_version = manifest.get("schema_version")
    if manifest_version is not None and (
        type(manifest_version) is not int
        or not 1 <= manifest_version <= LATEST_KNOWN_MANIFEST_SCHEMA_VERSION
    ):
        raise ValueError(
            f"Unsupported manifest schema_version {manifest_version!r}; "
            "inspect the newer format with its corresponding PsyCoLab version."
        )
    _check_laboratory_provenance(manifest)
    version = manifest.get("trial_schema_version")
    if version is not None and (
        type(version) is not int or version not in SUPPORTED_TRIAL_SCHEMA_VERSIONS
    ):
        raise ValueError(
            f"Unsupported trial_schema_version {version!r}; preserve this run and "
            "use a reader explicitly supporting its scientific data meanings."
        )

    columns, rows = _read_table(trials_path, require_column="trial_index")
    trials = {
        column: np.asarray([row[column] for row in rows], dtype=str)
        for column in columns
    }

    dictionary_path = run_directory / "trial_data_dictionary.tsv"
    dictionary: dict[str, dict[str, str]] = {}
    if dictionary_path.is_file():
        _, descriptions = _read_table(dictionary_path, require_column="column_name")
        for definition in descriptions:
            name = definition["column_name"]
            if not name or name in dictionary:
                raise ValueError(f"Empty or duplicated column in trial data dictionary: {name!r}")
            dictionary[name] = definition

    # Do not guess a missing column's type, or silently use *today's* column
    # definitions for historical runs. Extra fields are preserved verbatim.
    return {
        "trials": trials,
        "manifest": manifest,
        "data_dictionary": dictionary,
        "run_directory": run_directory,
    }
