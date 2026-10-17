"""Validated experiment settings, separate from Python scientific actions."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def settings_snapshot(spec):
    relative = PurePosixPath(spec.default_config)
    if relative.is_absolute() or ".." in relative.parts or "\\" in spec.default_config:
        raise ValueError("Experiment settings must be a repository-relative JSON path.")
    # Authored modules live in src/psychophysics_lab/experiments. This also works
    # for scaffolds in independent checkouts, without changing process cwd.
    source = Path(spec.procedure.__globals__["__file__"]).resolve()
    path = next(parent.parent for parent in source.parents if parent.name == "src") / relative
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    if (not isinstance(document, dict) or set(document) != {"schema_version", "experiment_id", "values"}
            or document["schema_version"] != 1 or document["experiment_id"] != spec.id
            or not isinstance(document["values"], dict)):
        raise ValueError("Experiment JSON requires schema_version=1, matching experiment_id and values.")
    unknown = set(document["values"]) - {f.key for f in spec.fields}
    if unknown:
        raise ValueError(f"Unknown experiment settings: {sorted(unknown)}")
    # Same public declarations validate the JSON, TUI and CLI.
    values = spec.normalise_values(document["values"], use_config=False)
    return {"file_identity": relative.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "document": document, "values": values}
