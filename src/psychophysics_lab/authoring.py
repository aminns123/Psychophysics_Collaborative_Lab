"""Project-local, explicit draft/ready authoring inventory.

Manually written experiment/adaptive files registered by researchers are listed.
Drafts are loaded in USER_env, never in the normal human-acquisition catalogue.
All new stimuli live directly in stimulus_library.py. 'Ready' means
software-tested; it is *not* physical calibration or ethical approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import json
import keyword
from pathlib import Path
import re

from .data.session import atomic_write_json

KINDS = {"stimulus": "stimuli", "experiment": "experiments", "adaptive": "adaptive"}
NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
MANIFEST = Path("authoring/components.json")


@dataclass(frozen=True)
class Component:
    kind: str
    name: str
    status: str
    tested_fingerprint: str = ""

    @property
    def module(self) -> str:
        return f"psychophysics_lab.{KINDS[self.kind]}.{self.name}"


def _valid(kind: str, name: str) -> None:
    if kind not in KINDS or not NAME.fullmatch(name) or keyword.iskeyword(name):
        raise ValueError("Use stimulus/experiment/adaptive and a lowercase Python module name.")


def _path(repo_root: Path, kind: str, name: str) -> Path:
    _valid(kind, name)
    return repo_root / "src" / "psychophysics_lab" / KINDS[kind] / (name + ".py")


def inventory(repo_root: Path) -> tuple[Component, ...]:
    path = Path(repo_root) / MANIFEST
    if not path.is_file():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "components"} or raw["schema_version"] != 1 or not isinstance(raw["components"], list):
        raise ValueError("Invalid authoring manifest (expected schema_version=1 and components array).")
    result = []
    seen = set()
    for row in raw["components"]:
        if not isinstance(row, dict) or set(row) - {"kind", "name", "status", "tested_fingerprint"}:
            raise ValueError("Invalid component entry in authoring manifest.")
        item = Component(**row)
        _valid(item.kind, item.name)
        if item.status not in {"draft", "ready"} or (item.kind, item.name) in seen:
            raise ValueError("Duplicate component or unknown authoring status.")
        if not isinstance(item.tested_fingerprint, str):
            raise ValueError("Invalid validation fingerprint.")
        seen.add((item.kind, item.name))
        result.append(item)
    return tuple(result)


def _save(repo_root: Path, items: tuple[Component, ...]) -> None:
    from dataclasses import asdict
    path = Path(repo_root) / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, {"schema_version": 1, "components": [asdict(item) for item in items]})


def stage(repo_root: Path, kind: str, name: str) -> Component:
    """Track a scaffold. Do not promote it to normal acquisition automatically."""
    root = Path(repo_root).resolve()
    _path(root, kind, name).relative_to(root)
    if not _path(root, kind, name).is_file():
        raise ValueError(f"Write src/psychophysics_lab/{KINDS[kind]}/{name}.py first; no file is generated.")
    if kind == "experiment":
        settings = root / "configs/experiments" / (name + ".json")
        if not settings.is_file():
            raise ValueError(f"Write {settings.relative_to(root)} before registering this experiment.")
    records = inventory(root)
    if any(i.kind == kind and i.name == name for i in records):
        raise ValueError("Component is already registered in the authoring inventory.")
    item = Component(kind, name, "draft")
    _save(root, records + (item,))
    return item


def fingerprint(repo_root: Path, item: Component) -> str:
    """Hash scientific code and associated experiment/stimulus JSON, not hardware calibration."""
    root = Path(repo_root).resolve()
    source = _path(root, item.kind, item.name)
    paths = [source]
    # Shared-library authors must retest when their drawing mathematics change.
    # Parse imports without executing an untested author module. Existing modules
    # that do not use the shared library retain their historical fingerprint.
    import ast
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    shared = any(
        (isinstance(node, ast.ImportFrom) and (node.module or "").endswith("stimulus_library"))
        or (isinstance(node, ast.Import) and any(alias.name.endswith("stimulus_library") for alias in node.names))
        or (isinstance(node, ast.ImportFrom) and node.module == "psychophysics_lab"
            and any(alias.name == "stimulus_library" for alias in node.names))
        for node in ast.walk(tree))
    if shared:
        paths.append(root / "src/psychophysics_lab/stimulus_library.py")
    if item.kind in {"stimulus", "experiment"}:
        config = root / "configs" / KINDS[item.kind] / (item.name + ".json")
        if not config.is_file():
            raise ValueError(f"Missing configuration: {config}")
        paths.append(config)
    digest = hashlib.sha256()
    for path in paths:
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or unsafe component file: {path}")
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def mark_tested(repo_root: Path, kind: str, name: str) -> Component:
    """Record a successful preview/simulation result for the exact current sources."""
    records = inventory(repo_root)
    target = next((item for item in records if item.kind == kind and item.name == name), None)
    if target is None:
        raise ValueError("Register the component as a draft before testing.")
    fp = fingerprint(repo_root, target)
    from dataclasses import replace
    updated = replace(target, status="draft", tested_fingerprint=fp)
    _save(repo_root, tuple(updated if i == target else i for i in records))
    return updated


def publish(repo_root: Path, kind: str, name: str) -> Component:
    records = inventory(repo_root)
    target = next((item for item in records if item.kind == kind and item.name == name), None)
    if target is None:
        raise ValueError("Unknown authoring component.")
    if not target.tested_fingerprint or target.tested_fingerprint != fingerprint(repo_root, target):
        raise ValueError("Source or JSON changed since last successful test; test this version again before publishing.")
    if kind == "experiment":
        # Software-ready dependencies must also be published before this
        # experiment can appear in the human-acquisition catalogue.
        importlib.invalidate_caches()
        spec = importlib.reload(importlib.import_module(target.module)).SPEC
        for dependency_kind, dependencies in (
            ("adaptive", (spec.adaptive.algorithm_id,) if spec.adaptive else ())):
            for dependency in dependencies:
                authored = next((i for i in records if i.kind == dependency_kind and i.name == dependency), None)
                if authored is not None and (authored.status != "ready" or
                                            authored.tested_fingerprint != fingerprint(repo_root, authored)):
                    raise ValueError(f"Publish and retest dependent {dependency_kind} '{dependency}' first.")
    from dataclasses import replace
    updated = replace(target, status="ready")
    _save(repo_root, tuple(updated if i == target else i for i in records))
    return updated


def load_authored(repo_root: Path, *, include_drafts: bool = False,
                  tolerate_errors: bool = False) -> dict[str, str]:
    """Load declared modules, rolling back failed registrations individually.

    A broken *draft* cannot prevent students from testing another module.
    Strict callers still raise; normal acquisition loads only ready components.
    """
    from .adaptive import registry as adaptive
    from .stimuli import registry as stimuli
    from .experiments import registry as experiments
    # Older single-file stimulus drafts are migrated to stimulus_library.py.
    # This loader is for independent experiments and adaptive code only.
    items = [i for i in inventory(repo_root) if i.kind != "stimulus" and (include_drafts or i.status == "ready")]
    items.sort(key=lambda i: (i.kind == "experiment", i.kind, i.name))
    problems = {}
    importlib.invalidate_caches()
    registries = (adaptive, stimuli, experiments)
    for item in items:
        before = tuple(dict(registry._REGISTRY) for registry in registries)
        try:
            source = _path(Path(repo_root), item.kind, item.name)
            if not source.is_file() or not source.resolve().is_relative_to(Path(repo_root).resolve()):
                raise ValueError(f"Component source missing or outside project: {source}")
            if not include_drafts and item.status == "ready":
                if not item.tested_fingerprint or item.tested_fingerprint != fingerprint(repo_root, item):
                    raise ValueError(f"{item.module} has changed since successful testing; retest it in USER_env.")
            module = importlib.import_module(item.module)
            spec = module.SPEC
            if getattr(spec, "id", None) != item.name:
                raise ValueError(f"{item.module} exports mismatched SPEC.id")
            registry = {"stimulus": stimuli, "experiment": experiments, "adaptive": adaptive}[item.kind]
            existing = registry._REGISTRY.get(item.name)
            if existing is None:
                {"stimulus": stimuli.register_stimulus, "experiment": experiments.register_experiment,
                 "adaptive": adaptive.register_algorithm}[item.kind](spec)
            elif existing != spec:
                raise ValueError(f"Conflicting component ID: {item.name}")
        except Exception as exc:
            for registry, saved in zip(registries, before):
                registry._REGISTRY.clear()
                registry._REGISTRY.update(saved)
            if not tolerate_errors:
                raise
            problems[f"{item.kind}:{item.name}"] = f"{type(exc).__name__}: {exc}"
    return problems


