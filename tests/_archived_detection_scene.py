"""Read-only scientific oracle from archived pre-atomic source code.

Do not import the old LibraryStimulus module into the running application.
Extract ONLY the historical DetectionScene class and probe_limit function
from the byte-identical Git archives, with no registration side effects.
"""
import ast
import copy
import hashlib
from pathlib import Path

import numpy as np

from psychophysics_lab.experiments._internal.spec import ConfigField
from psychophysics_lab.stimuli.registry import StimulusSpec


ROOT = Path(__file__).resolve().parents[1] / "outdated_code" / "pre_atomic_207"
ARCHIVED_STIMULI = ROOT / "src/psychophysics_lab/stimulus_library.py"
ARCHIVED_LIMITS = ROOT / "src/psychophysics_lab/experiments/_internal/detection_limits.py"
# Exact pre-migration Git blob SHA (Git's sha1('blob <size>\0' + data)).
EXPECTED_BLOBS = {
    ARCHIVED_STIMULI: "284e1dcd0faa031aff04fa4e44cf98a0c0b4e8b5",
    ARCHIVED_LIMITS: "d572f3a6659f5046fade1f98be81ee3a9ad64f3f",
}


def _source(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    actual = hashlib.sha1(
        f"blob {len(data)}\0".encode() + data
    ).hexdigest()
    if actual != EXPECTED_BLOBS[path]:
        raise AssertionError(
            f"Historical comparison source changed at {path}: {actual}; "
            "never rewrite a frozen scientific oracle"
        )
    return ast.parse(data, filename=str(path))


def _extract(path, kind, name):
    tree = _source(path)
    node = next(
        node for node in tree.body
        if isinstance(node, kind) and node.name == name
    )
    return copy.deepcopy(node)


class _HistoricalNoRegistration:
    """Archived source must not register anything into live PsyCoLab."""


_class = _extract(ARCHIVED_STIMULI, ast.ClassDef, "DetectionScene")
_scope = {
    "__name__": "_archived_detection_scene",
    "np": np,
    "ConfigField": ConfigField,
    "StimulusSpec": StimulusSpec,
    "LibraryStimulus": _HistoricalNoRegistration,
}
exec(
    compile(
        ast.fix_missing_locations(ast.Module(body=[_class], type_ignores=[])),
        str(ARCHIVED_STIMULI), "exec"
    ),
    _scope,
)
DetectionScene = _scope["DetectionScene"]

_limit = _extract(ARCHIVED_LIMITS, ast.FunctionDef, "probe_limit")
# The historical function imported DetectionScene from the live stimulus
# library; provide the extracted archived class instead, without any import.
_limit.body = [
    stmt for stmt in _limit.body
    if not (
        isinstance(stmt, ast.ImportFrom) and
        stmt.module == "psychophysics_lab.stimulus_library"
    )
]
exec(
    compile(
        ast.fix_missing_locations(ast.Module(body=[_limit], type_ignores=[])),
        str(ARCHIVED_LIMITS), "exec"
    ),
    _scope,
)
probe_limit = _scope["probe_limit"]
