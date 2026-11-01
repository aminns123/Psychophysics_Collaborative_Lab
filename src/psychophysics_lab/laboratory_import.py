"""User-controlled laboratory Python import and reviewable official contribution.

No experiment code is executed during an import, IDs are never rewritten,
existing source is never overwritten, and an 'official contribution' never
mutates the maintained package or commits a Git branch. Both actions use the
ONE trusted laboratory root and ordinary Test -> Ready path.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil

from . import extensions
from .data.session import atomic_write_json


MAX_IMPORT_BYTES = 2_000_000


def _candidate(repo_root, source):
    current = extensions.configured(repo_root)
    if current is None:
        raise ValueError("Enable and explicitly trust a laboratory extensions folder first.")
    root, namespace = current
    original = Path(source)
    if not original.is_absolute():
        raise ValueError("Select an absolute path to the experiment .py file.")
    file = extensions._plain(original)
    if file.suffix.lower() != ".py" or not file.is_file():
        raise ValueError("Import requires one existing .py experiment file.")
    if not file.stem.startswith(namespace + "__"):
        raise ValueError(
            f"File must be named {namespace}__study_name.py; rename the file "
            "and declare the same SPEC.id inside its Python source."
        )
    if len(file.stem) > 128:
        raise ValueError("Experiment filename is too long.")
    if file.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("Experiment source exceeds the 2 MB import limit.")
    raw = file.read_bytes()
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("Experiment source exceeds the 2 MB import limit.")
    try:
        tree = ast.parse(raw.decode("utf-8-sig"), filename=str(file))
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError(f"Experiment Python has a syntax/encoding error: {exc}") from exc
    has_spec = any(
        isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SPEC" for target in node.targets
        ) or isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id == "SPEC"
        for node in tree.body
    )
    if not has_spec:
        raise ValueError("Experiment must export a top-level SPEC from experiment(...).")
    return root, namespace, file, raw


def import_experiment(repo_root, source):
    """Copy a checked candidate into trusted experiments/ as an untested draft.

    This reads/AST-parses source; it NEVER imports/executes Python and never
    copies or overwrites any stimulus library, JSON, data, or source dependency.
    The author must review Python, ensure all relevant stimuli exist in the
    trusted root's stimulus_library.py, refresh and run Test -> Ready.
    """
    root, namespace, file, raw = _candidate(repo_root, source)
    target = root / "experiments" / file.name
    target = extensions._plain(target)
    if target == file:
        raise ValueError("This experiment is already in your trusted laboratory folder.")
    if not target.parent.is_dir() or target.parent != root / "experiments":
        raise ValueError("The configured laboratory experiments folder is missing or unsafe.")
    # Exclusive creation prevents an import from overwriting laboratory work,
    # including a race with another process creating the same filename.
    try:
        with target.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError(f"Laboratory experiment already exists; no file changed: {target}") from exc
    try:
        if file.read_bytes() != raw:
            raise ValueError("Original experiment changed while copying; import was rolled back.")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "id": target.stem,
        "path": str(target),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "status": "draft",
        "note": (
            "Python copied byte-for-byte; nothing has been tested or made Ready. "
            "Its SPEC.id must equal this filename, source_paths must use "
            f"experiments/{target.name}, and custom stimuli belong in the "
            "trusted laboratory stimulus_library.py. Refresh (F5), inspect "
            "source, Simulate / validate, then Mark Ready."
        ),
    }


def prepare_official_contribution(repo_root, identity):
    """Bundle a Ready lab experiment and referenced sources for PR review.

    The output remains in the trusted laboratory root. It neither writes
    the PsyCoLab repository nor renames local/historical scientific IDs.
    """
    current = extensions.configured(repo_root)
    if current is None:
        raise ValueError("Enable and explicitly trust the laboratory folder first.")
    root, namespace = current
    if not isinstance(identity, str) or not identity.startswith(namespace + "__"):
        raise ValueError("Select a namespaced experiment from this laboratory folder.")
    if extensions.status(repo_root, "experiment", identity) != "ready":
        raise ValueError("Only the exact Tested -> Ready laboratory source can be proposed.")
    from .experiments._internal.registry import get_experiment
    from .stimuli.registry import get_stimulus

    spec = get_experiment(identity)
    if spec.origin_namespace != namespace or spec.historical:
        raise ValueError("Selected experiment is not the active Ready laboratory definition.")
    candidate = extensions.source_at(root, f"experiments/{identity}.py")
    local_stimuli = []
    sources = {f"experiments/{identity}.py", *spec.source_paths}
    if spec.default_config:
        sources.add(spec.default_config)
    for stimulus_id in dict.fromkeys(spec.stimulus_defaults.values()):
        stimulus = get_stimulus(stimulus_id)
        if stimulus.origin_namespace == namespace:
            if extensions.status(repo_root, "stimulus", stimulus_id) != "ready":
                raise ValueError(f"Local stimulus {stimulus_id} must be Ready first.")
            local_stimuli.append(stimulus_id)
            sources.update((stimulus.source_path, *stimulus.source_dependencies))
            if stimulus.default_config:
                sources.add(stimulus.default_config)
    # Inspect every actual declared scientific dependency, not just the
    # principal experiment. Copy only the selected study's referenced sources.
    selected_sources = {
        relative: extensions.source_at(root, relative)
        for relative in sources
    }

    # Preserve a concrete exact-source export including all lab dependencies
    # (the source root is separately required for historical reproducibility).
    inventory = extensions.source_hashes(repo_root)
    fingerprint = extensions.fingerprint(repo_root)
    suffix = hashlib.sha256((identity + fingerprint).encode("utf-8")).hexdigest()[:12]
    directory = root / "contribution_proposals" / (identity + "__" + suffix)
    if directory.exists():
        raise ValueError(f"Review package already exists; no files overwritten: {directory}")
    directory.mkdir(parents=True, exist_ok=False)
    try:
        for relative, source in sorted(selected_sources.items()):
            destination = directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        official_id = identity[len(namespace) + 2:]
        payload = {
            "schema_version": 1,
            "kind": "review_proposal_only",
            "original_laboratory": {"namespace": namespace, "experiment_id": identity},
            "original_readiness": "ready",
            "source_fingerprint": fingerprint,
            "original_source_sha256": inventory,
            "proposed_official": {
                "experiment_id": official_id,
                "experiment_source": f"src/psychophysics_lab/experiments/{official_id}.py",
                "stimulus_id_mappings_for_review": {
                    value: value[len(namespace)+2:] for value in local_stimuli
                },
            },
            "included_files": sorted(selected_sources),
            "included_file_sha256": {
                relative: hashlib.sha256(file.read_bytes()).hexdigest()
                for relative, file in sorted(selected_sources.items())
            },
            "review_required": [
                "Review and explicitly accept any ID/source-path changes in a GitHub PR.",
                "Inspect imports, dependencies and any already-existing official IDs.",
                "Confirm each experiment's original conditions, stimuli, event order and units.",
                "Verify generic software tests, synthetic runs and data consistency.",
                "Add maintainer-level equivalence tests for any changes to accepted science.",
                "Qualify actual apparatus/geometry/photometry/timing before human acquisition.",
            ],
            "status": "not_merged_not_official",
        }
        atomic_write_json(directory / "contribution_manifest.json", payload)
    except Exception:
        shutil.rmtree(directory)
        raise
    return directory
