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
import re
from pathlib import Path
import shutil

from . import extensions
from .data.session import atomic_write_json


MAX_IMPORT_BYTES = 2_000_000

# This source is intentionally a DRAFT. Its science must be defined by its author.
# The TUI can inspect and test the result but must not invent the protocol.
SOURCE_TEMPLATE = '''"""New PsyCoLab study: define scientific choices before testing.

A1 describes stimuli, positions, conditions, event order and responses.
A2 describes scientific methods/measurements, stopping and interpretation.
B only connects the scientist's functions to the existing PsyCoLab runner.
This file is a DRAFT: replace the explicit TODOs before Test -> Ready.
"""

from psychophysics_lab.researcher import (
    ConfigField, ResponseParadigm, Show, Stimulus, CollectResponse,
    experiment,
)


# A1 -- WHAT, WHERE AND WHEN
# Edit this map and the named LibraryStimulus classes in your lab stimulus_library.py.
# Existing built-in stimulus IDs can be reused; custom ones require lab registration.
STIMULI = {
    "target": "oriented_line",
    "fixation": "fixation_cross",
}

FIELDS = (
    ConfigField("trial_count", "Number of trials", "int", 6,
                minimum=1, maximum=200, section="Experiment"),
    ConfigField("fixation_ms", "Fixation duration", "int", 500,
                minimum=1, units="ms", section="Timing"),
    ConfigField("stimulus_ms", "Target duration", "int", 200,
                minimum=1, units="ms", section="Timing"),
)
RESPONSES = ResponseParadigm(
    "__EXPERIMENT_ID__", ("option_a", "option_b"), ("F", "J")
)
SESSION_START = []  # Add WaitForKey + Show if your protocol requires readiness.


def trial_events(settings, condition):
    """Trial order. Replace the placeholder choice/target with your own science."""
    # TODO SCIENCE: decide which stimulus is present, its angular X/Y
    # location, target meaning, response event, and appropriate timing.
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("target", duration="stimulus_ms", stimuli=(Stimulus("target"),)),
        CollectResponse(actions=("option_a", "option_b")),
    ]


# A2 -- CONDITIONS, RESPONSE RULES, MEASUREMENT AND STOPPING
def scientific_conditions(settings):
    """TODO SCIENCE: define actual conditions and their selection/order."""
    raise NotImplementedError(
        "A2: define scientific_conditions() and the meaning of each target."
    )


def interpret_response(condition, response):
    """TODO SCIENCE: check the participant's chosen alternative."""
    raise NotImplementedError(
        "A2: define which alternative is correct for each condition."
    )


# B -- FRAMEWORK CONNECTION (normally leave framework internals alone)
def procedure(run):
    """TODO: connect your chosen conditions, trial_events and interpretation.

    Inspect a working A1/A2/B example before implementing this section.
    The unimplemented placeholder deliberately cannot become software Ready.
    """
    raise NotImplementedError(
        "Complete A1/A2 and connect them to RunContext; do not run human trials."
    )


SPEC = experiment(
    id="__EXPERIMENT_ID__",
    name="New laboratory study -- draft",
    description="Incomplete scientist-owned A1/A2/B experiment.",
    fields=FIELDS,
    stimuli=STIMULI,
    responses=RESPONSES,
    session_start=SESSION_START,
    procedure=procedure,
    supports_simulation=True,
    calibration_requirements=("geometry", "timing"),
    monitor_capabilities=("display_binding", "resolution"),
    acquisition_block_reason="Template only: scientific procedure and apparatus qualification required.",
    source_paths=("experiments/__EXPERIMENT_ID__.py",),
)
'''


def create_experiment_starter(repo_root, short_name):
    """Create an untested A1/A2/B Python draft without writing any science."""
    current = extensions.configured(repo_root)
    if current is None:
        raise ValueError("Enable and explicitly trust a laboratory extensions folder first.")
    root, namespace = current
    short = str(short_name).strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", short) or len(short) > 100:
        raise ValueError("Use a short lowercase study ID with letters, numbers and underscores.")
    if short.startswith(namespace + "__"):
        raise ValueError("Enter only the short study ID: PsyCoLab supplies the namespace.")
    identity = f"{namespace}__{short}"
    parent = extensions._plain(root / "experiments")
    if not parent.is_dir():
        raise ValueError("Trusted laboratory experiments folder is missing.")
    source = SOURCE_TEMPLATE.replace("__EXPERIMENT_ID__", identity)
    path = parent / (identity + ".py")
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("This laboratory experiment already exists; it was not overwritten.") from exc
    return {
        "id": identity, "path": str(path), "status": "draft",
        "note": ("New editable A1/A2/B Python file created. The TODOs intentionally "
                 "prevent unqualified acquisition; the source will remain Draft "
                 "until you write its scientific protocol and Test -> Ready."),
    }




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
    if len(file.stem) > 128 or not re.fullmatch(r"[a-z][a-z0-9_]*", file.stem):
        raise ValueError(
            "Experiment ID/filename must use lowercase letters, numbers and underscores only."
        )
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
    # Verify IDs for conventional A1/A2/B authoring patterns *without executing*
    # the imported file. Arbitrary dynamic definitions remain checked by the
    # existing trusted loader and normal Test -> Ready.
    def constant(node):
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    declarations = [
        node.value for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SPEC" for target in node.targets)
    ]
    for expression in declarations:
        if not isinstance(expression, ast.Call):
            continue
        if isinstance(expression.func, ast.Name) and expression.func.id == "experiment":
            for key in expression.keywords:
                if key.arg == "id":
                    identity = constant(key.value)
                    if identity is not None and identity != file.stem:
                        raise ValueError(
                            f"Experiment SPEC.id is {identity!r}, but the file requires "
                            f"{file.stem!r}. Change the declared ID or source filename."
                        )
        if isinstance(expression.func, ast.Name) and expression.func.id == "definition":
            for key in expression.keywords:
                if key.arg == "identity":
                    identity = constant(key.value)
                    if identity is not None and identity != file.stem:
                        raise ValueError(
                            f"Experiment definition identity is {identity!r}; "
                            f"the file requires {file.stem!r}."
                        )
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "definition":
            continue
        args = node.args.args
        defaults = node.args.defaults
        for parameter, value in zip(args[len(args)-len(defaults):], defaults):
            if parameter.arg == "identity":
                identity = constant(value)
                if identity is not None and identity != file.stem:
                    raise ValueError(
                        f"Experiment definition default ID is {identity!r}; "
                        f"the file requires {file.stem!r}. Edit that one declared identity."
                    )
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
            if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
                raise ValueError("Source changed during contribution export; package removed.")
        if extensions.fingerprint(repo_root) != fingerprint:
            raise ValueError("Laboratory scientific source changed during export; package removed.")
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
