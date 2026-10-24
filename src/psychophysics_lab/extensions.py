"""Opt-in laboratory sources. Path validation is not a Python sandbox.

Source is never written here. Local configuration owns trust and readiness;
ordinary registries, development tools and the canonical runner own execution.
"""
from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
from types import ModuleType

from .config.local import config_root, preferences, save_preferences
from .data.session import atomic_write_json
from .data.locking import file_lock

MANIFEST = "psycolab_extensions.json"
_loaded = {}  # (kind, id) -> exact imported source fingerprint
_errors = {}
_development = False  # enabled only by the explicit software development command


def _plain(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f"Symlink/junction source paths are not supported: {part}")
    return path.resolve()


def _separate(left, right):
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        raise ValueError("Extensions, framework, local configuration and acquisition data must be separate folders.")


def validate_root(root, repo_root, data_root=None):
    if not Path(root).is_absolute():
        raise ValueError("Choose an absolute extensions folder path.")
    root = _plain(root)
    from .paths import default_data_root
    from .data.workspace import preferred_data_root
    if data_root is None:
        data_root = preferred_data_root(Path(repo_root), default_data_root(Path(repo_root)))
    for other in (Path(repo_root).resolve(), config_root(Path(repo_root)),
                  Path(data_root or default_data_root(Path(repo_root))).resolve()):
        _separate(root, other)
    if not root.is_dir():
        raise ValueError(f"Extensions folder is missing: {root}")
    manifest = source_at(root, MANIFEST)
    document = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict) or set(document) != {"schema_version", "namespace"} or type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Extensions manifest requires schema_version=1 and namespace.")
    namespace = document["namespace"]
    if not isinstance(namespace, str) or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", namespace) or "__" in namespace or namespace in {"official", "psychophysics_lab"}:
        raise ValueError("Use a unique laboratory namespace of 3-64 lowercase letters, digits or single underscores.")
    source_at(root, "stimulus_library.py")
    if not _plain(root / "experiments").is_dir():
        raise ValueError("Extensions need an experiments directory and stimulus_library.py.")
    return root, namespace


def suggested_root(repo_root):
    """Stable, editable first-run default outside the Git checkout."""
    return Path(repo_root).resolve().parent / "PsyCoLab_Extensions"


def initialise_starter(repo_root, root=None, *, data_root=None):
    """Copy the bundled teaching study once; NEVER overwrite laboratory work.

    This only prepares source files. It does not trust or execute Python,
    register components, set software Ready or change participant data.
    Returns (path, created). Existing valid roots are preserved untouched.
    """
    from .paths import default_data_root
    from .data.workspace import preferred_data_root

    repo_root = Path(repo_root).resolve()
    target = Path(root) if root is not None else suggested_root(repo_root)
    if not target.is_absolute():
        raise ValueError("Choose an absolute folder for laboratory extensions.")
    target = _plain(target)
    chosen_data = Path(data_root or preferred_data_root(
        repo_root, default_data_root(repo_root)
    )).resolve()
    for protected in (repo_root, config_root(repo_root), chosen_data):
        _separate(target, protected)

    if target.exists():
        if not target.is_dir():
            raise ValueError(f"Extension destination is not a directory: {target}")
        if any(target.iterdir()):
            try:
                validate_root(target, repo_root, chosen_data)
            except (ValueError, OSError) as exc:
                raise ValueError(
                    f"Existing folder was left unchanged: {target}. "
                    "It is not a complete extension root; select its actual "
                    "manifest-containing subfolder or choose a new/empty folder."
                ) from exc
            return target, False

    template = repo_root / "examples" / "laboratory_extensions"
    if not all((template / part).exists() for part in (
        MANIFEST, "stimulus_library.py", "experiments", "presets"
    )):
        raise ValueError("Bundled laboratory starter files are missing.")

    if target.exists():  # An existing EMPTY directory is safe to initialise.
        shutil.copytree(template, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Stage in the same parent so a failed copy cannot leave a misleading
        # half-populated source root. Never replace an existing target.
        staging = Path(tempfile.mkdtemp(prefix=".psycolab_starter_", dir=target.parent))
        try:
            shutil.copytree(template, staging, dirs_exist_ok=True)
            if target.exists():
                raise ValueError(
                    f"Destination appeared during setup; left unchanged: {target}"
                )
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    validate_root(target, repo_root, chosen_data)
    return target, True


def initialise_default(repo_root, *, data_root=None):
    """First ordinary TUI launch only; never undo a researcher's selection."""
    setting = preferences(config_root(Path(repo_root))).get("extensions")
    if setting is not None:
        # Both enabled and deliberately disabled settings are respected.
        return None
    return initialise_starter(repo_root, data_root=data_root)


def source_at(root, relative):
    if not isinstance(relative, str):
        raise ValueError("Source paths must be strings.")
    value = PurePosixPath(relative)
    if value.is_absolute() or any(p in {"..", "."} for p in value.parts) or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe relative source path: {relative}")
    path = _plain(Path(root) / value)
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError(f"Missing or escaping extension source: {relative}")
    return path


def configured(repo_root=None, data_root=None):
    from .paths import find_repo_root
    repo_root = Path(repo_root or find_repo_root())
    setting = preferences(config_root(repo_root)).get("extensions", {})
    if not isinstance(setting, dict) or type(setting.get("enabled", False)) is not bool:
        raise ValueError("Invalid extensions preference; explicitly enable or disable the folder again.")
    if not setting.get("enabled", False):
        return None
    root, namespace = validate_root(setting.get("root", ""), repo_root, data_root)
    if namespace != setting.get("namespace"):
        raise ValueError("Extension namespace changed. Explicitly trust the folder again.")
    return root, namespace


def configure(repo_root, root=None, *, trusted=False, data_root=None):
    if root is None:
        # Disabling stops code execution but keeps the researcher's chosen
        # location visible for a future deliberate re-enable.
        local = config_root(Path(repo_root))
        old = preferences(local).get("extensions", {})
        setting = {"enabled": False}
        if isinstance(old, dict) and isinstance(old.get("root"), str):
            setting["root"] = old["root"]
        save_preferences(local, extensions=setting)
    else:
        if not trusted:
            raise ValueError("Explicitly trust this Python code: extensions can execute with your machine permissions; this is not a sandbox.")
        path, namespace = validate_root(root, repo_root, data_root)
        save_preferences(config_root(Path(repo_root)), extensions={"enabled": True, "root": str(path), "namespace": namespace})
    # Never keep old extension definitions selectable after disabling/changing roots.
    unload()


def unload():
    from .experiments._internal import registry as experiments
    from .stimuli import registry as stimuli
    for registry in (experiments._REGISTRY, stimuli._REGISTRY):
        for key, spec in list(registry.items()):
            if getattr(spec, "origin_namespace", ""):
                del registry[key]
    for name in list(sys.modules):
        if name.startswith("_psycolab_lab_"):
            del sys.modules[name]
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, _LaboratoryImports)]
    _loaded.clear()
    _errors.clear()


def source_path(repo_root, component, relative):
    namespace = getattr(component, "origin_namespace", "")
    if namespace:
        current = configured(repo_root)
        if current is None or current[1] != namespace:
            raise ValueError("This laboratory extension is disabled or its root changed.")
        return source_at(current[0], relative)
    path = (Path(repo_root) / relative).resolve()
    if not path.is_relative_to(Path(repo_root).resolve()) or not path.is_file():
        raise ValueError(f"Registered source missing or outside the framework: {relative}")
    return path


def source_hashes(repo_root):
    current = configured(repo_root)
    if current is None:
        return {}
    root, _ = current
    paths = [MANIFEST, "stimulus_library.py"]
    # Conservatively include all local science and presets, even if imported
    # indirectly. Tests and Git bookkeeping are not scientific dependencies.
    for folder in ("experiments", "presets"):
        base = root / folder
        if not base.exists():
            continue
        _plain(base)
        pending = [base]
        while pending:
            directory = _plain(pending.pop())
            for path in sorted(directory.iterdir()):
                _plain(path)  # reject a junction BEFORE descending into it
                if path.is_dir():
                    pending.append(path)
                elif path.suffix in {".py", ".json"}:
                    paths.append(path.relative_to(root).as_posix())
    return {name: hashlib.sha256(source_at(root, name).read_bytes()).hexdigest() for name in sorted(paths)}


def fingerprint(repo_root):
    framework = Path(repo_root) / 'src/psychophysics_lab'
    shared = [framework/'stimulus_library.py', framework/'researcher.py']
    shared += list((framework/'adaptive').glob('*.py'))
    shared += list((framework/'stimuli').glob('*.py'))
    payload = {'laboratory': source_hashes(repo_root), 'framework_science': {
        path.relative_to(repo_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in shared if path.is_file()}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _records_path(repo_root):
    return config_root(Path(repo_root)) / "extension_readiness.json"


def records(repo_root):
    path = _records_path(repo_root)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1 or not isinstance(data.get("components"), dict):
        raise ValueError("Unsupported extension readiness record; original file preserved.")
    for key, item in data["components"].items():
        if not isinstance(key, str) or not isinstance(item, dict) or type(item.get("ready")) is not bool or not isinstance(item.get("fingerprint"), str) or not re.fullmatch("[0-9a-f]{64}", item["fingerprint"]):
            raise ValueError("Invalid extension readiness record; original file preserved.")
    return data["components"]


def status(repo_root, kind, identity):
    item = records(repo_root).get(f"{kind}:{identity}", {})
    if item.get("fingerprint") != fingerprint(repo_root):
        return "draft"
    return "ready" if item.get("ready") is True else "tested"


def record_test(repo_root, kind, identity, before):
    if before != fingerprint(repo_root) or _loaded.get((kind, identity)) != before:
        raise ValueError("Extension source changed during testing; restart and retest this exact revision.")
    with file_lock(_records_path(repo_root).with_suffix(".lock")):
        items = records(repo_root)
        items[f"{kind}:{identity}"] = {"fingerprint": before, "ready": False}
        atomic_write_json(_records_path(repo_root), {"schema_version": 1, "components": items})


def publish(repo_root, kind, identity):
    with file_lock(_records_path(repo_root).with_suffix(".lock")):
        items = records(repo_root)
        item = items.get(f"{kind}:{identity}")
        if item is None or item.get("fingerprint") != fingerprint(repo_root):
            raise ValueError("Run a successful --dev-preview or --dev-test on this exact source revision first.")
        # An experiment's simulation exercises its selected local stimuli too.
        item["ready"] = True
        atomic_write_json(_records_path(repo_root), {"schema_version": 1, "components": items})


class _LaboratoryImports(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Compile declared-root helpers from current bytes, never stale pyc files."""
    def __init__(self, prefix, root, repo_root, expected):
        self.prefix, self.root, self.repo_root, self.expected = prefix, root, repo_root, expected

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith(self.prefix + '.'):
            return None
        relative = fullname[len(self.prefix)+1:].replace('.', '/')
        for candidate, package in ((relative + '.py', False), (relative + '/__init__.py', True)):
            if (self.root / candidate).exists():
                source = source_at(self.root, candidate)
                spec = importlib.util.spec_from_file_location(fullname, source, loader=self,
                    submodule_search_locations=[str(source.parent)] if package else None)
                return spec
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if fingerprint(self.repo_root) != self.expected:
            raise ValueError('Local source changed before a helper import; restart and retest.')
        relative = Path(module.__spec__.origin).relative_to(self.root).as_posix()
        source = source_at(self.root, relative)
        if relative not in source_hashes(self.repo_root):
            raise ValueError('Local helpers must live in experiments/ and be fingerprinted.')
        exec(compile(source.read_bytes(), str(source), 'exec'), module.__dict__)


def _module(name, path):
    # Compile current bytes rather than trusting timestamp-based .pyc caches.
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), name.rpartition(".")[0]
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def _package(name, path):
    module = ModuleType(name)
    module.__path__, module.__package__ = [str(path)], name
    sys.modules[name] = module


def load(repo_root, *, development=False):
    """Register through the existing registries, rollback failures, never replace IDs."""
    from .experiments._internal import registry as experiments
    from .stimuli import registry as stimuli
    from .adaptive import registry as adaptive
    from .stimulus_library import LibraryStimulus
    try:
        current = configured(repo_root)
        if current is None:
            return {}
        root, namespace = current
        _errors.pop("root", None)
        fp = fingerprint(repo_root)
        prefix = "_psycolab_lab_" + namespace
        sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, _LaboratoryImports)]
        sys.meta_path.insert(0, _LaboratoryImports(prefix, root, repo_root, fp))
        _package(prefix, root)
        _package(prefix + ".experiments", root / "experiments")
        files = [("stimulus", "stimulus_library.py")]
        for path in sorted((root / "experiments").glob("*.py")):
            try:
                tree = ast.parse(source_at(root, path.relative_to(root).as_posix()).read_text(encoding="utf-8-sig"))
            except (SyntaxError, UnicodeError) as exc:
                _errors[path.relative_to(root).as_posix()] = str(exc)
                continue
            if any(isinstance(node, (ast.Assign, ast.AnnAssign)) and any(isinstance(target, ast.Name) and target.id == "SPEC" for target in (node.targets if isinstance(node, ast.Assign) else [node.target])) for node in tree.body):
                files.append(("experiment", path.relative_to(root).as_posix()))
            elif path.stem.startswith(namespace + "__"):
                _errors[path.relative_to(root).as_posix()] = "Experiment file must export SPEC; correct the declaration/imports and restart."
    except Exception as exc:
        _errors["root"] = str(exc)
        return dict(_errors)
    for kind, relative in files:
        registries = (experiments._REGISTRY, stimuli._REGISTRY, adaptive._REGISTRY)
        saved = [dict(registry) for registry in registries]
        imported_before = dict(_loaded)
        try:
            if any(item[0] == kind and value == fp for item, value in _loaded.items()) and kind == "stimulus":
                continue
            name = prefix + "." + relative[:-3].replace("/", ".")
            module = _module(name, source_at(root, relative))
            specs = ([cls.SPEC for cls in vars(module).values() if isinstance(cls, type) and cls is not LibraryStimulus and issubclass(cls, LibraryStimulus) and cls.__module__ == name]
                     if kind == "stimulus" else [module.SPEC])
            # Imports must not mutate a registry before collision validation.
            if any(registry != old for registry, old in zip(registries, saved)):
                raise ValueError("Export SPEC / LibraryStimulus classes; do not register components during import.")
            seen = set()
            for spec in specs:
                if spec.id in seen:
                    raise ValueError(f"Duplicate component ID: {spec.id}")
                seen.add(spec.id)
                if not spec.id.startswith(namespace + "__"):
                    raise ValueError(f"Use a namespace-prefixed ID: {namespace}__name (received {spec.id}).")
                key = (kind, spec.id)
                registry = stimuli if kind == "stimulus" else experiments
                if spec.id in registry._REGISTRY:
                    if _loaded.get(key) == fp:
                        continue
                    raise ValueError(f"Duplicate or changed component ID: {spec.id}; restart after editing.")
                if kind == "experiment" and (spec.procedure is None or spec.procedure.__module__ != name or spec.historical):
                    raise ValueError("External experiments must define their own normal RunContext procedure in this file.")
                declared = ((spec.source_path, *spec.source_dependencies) if kind == "stimulus" else spec.source_paths)
                for source in (*declared, *((spec.default_config,) if spec.default_config else ())):
                    source_at(root, source)
                    if source not in source_hashes(repo_root):
                        raise ValueError("Declare scientific dependencies inside experiments/ or presets/, or stimulus_library.py.")
                if kind == "experiment" and spec.data_directory_name and not spec.data_directory_name.startswith(namespace + "__"):
                    raise ValueError("External data directory names must use the laboratory namespace prefix.")
                if kind == "experiment" and spec.id != Path(relative).stem:
                    raise ValueError("External experiment SPEC.id must equal its filename.")
                spec = replace(spec, origin_namespace=namespace, display_name=f"[Lab {namespace}] {spec.display_name}",
                               **({"source_path": relative} if kind == "stimulus" else {"source_paths": tuple(dict.fromkeys((relative, *spec.source_paths)))}))
                # Keep the defining module's SPEC consistent with runtime references.
                if kind == "experiment":
                    module.SPEC = spec
                # Stimuli can be previewed; readiness is checked for every selected
                # local stimulus at the runner, including built-in experiments.
                if kind == "stimulus" or development or status(repo_root, kind, spec.id) == "ready":
                    (stimuli.register_stimulus if kind == "stimulus" else experiments.register_experiment)(spec)
                    _loaded[key] = fp
                _errors.pop(relative, None)
        except Exception as exc:
            for registry, old in zip(registries, saved):
                registry.clear(); registry.update(old)
            _loaded.clear(); _loaded.update(imported_before)
            _errors[relative] = f"{type(exc).__name__}: {exc}. Check the source/imports and dependencies, then restart."
    try:
        if fingerprint(repo_root) != fp:
            raise ValueError("Source changed while importing; restart and retest.")
    except (ValueError, OSError) as exc:
        unload()
        _errors["root"] = str(exc)
    return dict(_errors)


def inventory(repo_root):
    current = configured(repo_root)
    if current is None:
        return []
    root, namespace = current
    result = []
    # List drafts without importing their Python merely to inspect status.
    for path in sorted((root / "experiments").glob("*.py")):
        if path.stem.startswith(namespace + "__"):
            result.append({"kind": "experiment", "id": path.stem, "path": path,
                           "status": status(repo_root, "experiment", path.stem)})
    from .stimuli.registry import _REGISTRY
    for spec in _REGISTRY.values():
        if spec.origin_namespace == namespace:
            result.append({"kind": "stimulus", "id": spec.id, "path": root / spec.source_path,
                           "status": status(repo_root, "stimulus", spec.id)})
    return result


def check_run(repo_root, spec, snapshots, *, development=False, data_root=None):
    from .stimuli.registry import get_stimulus
    components = [("experiment", spec)] + [("stimulus", get_stimulus(value["document"]["stimulus_id"])) for value in snapshots.values()]
    local = [(kind, item) for kind, item in components if getattr(item, "origin_namespace", "")]
    if not local:
        return None
    if repo_root is None:
        from .paths import find_repo_root
        repo_root = find_repo_root()
    current = configured(repo_root, data_root)
    if current is None:
        raise ValueError("Laboratory extensions are disabled.")
    fp = fingerprint(repo_root)
    for kind, item in local:
        if item.origin_namespace != current[1] or _loaded.get((kind, item.id)) != fp:
            raise ValueError("Laboratory source changed since import; restart and retest before running.")
        if not (development and _development) and status(repo_root, kind, item.id) != "ready":
            raise ValueError(f"{item.id} is not software Ready. Use --dev-preview/--dev-test and --dev-ready; researcher override cannot waive this.")
    return {"schema_version": 1, "origin": "laboratory", "namespace": current[1],
            "experiment_identity": {"namespace": spec.origin_namespace or "official", "id": spec.id},
            "components": [{"kind": kind, "id": item.id, "namespace": item.origin_namespace,
                            "software_status": status(repo_root, kind, item.id)} for kind, item in local],
            "source_sha256": source_hashes(repo_root), "fingerprint": fp}


def permits_source(repo_root, path):
    path = Path(path)
    try:
        current = configured(repo_root)
        return current is not None and source_at(current[0], path.absolute().relative_to(current[0]).as_posix()) == path.resolve()
    except (ValueError, OSError):
        return False
