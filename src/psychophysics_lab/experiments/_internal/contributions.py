"""Load the public contribution list atomically into both registries."""
import importlib
import ast
import warnings
from pathlib import Path

_loaded = False
_loading = False



def discover_experiment_modules():
    """Find local SPEC declarations without executing helpers or managed drafts.

    Manifest-managed files continue through fingerprint-gated load_authored.
    Plain new Python definitions need SPEC.id equal to their filename.
    The documented CSF source rename retains its existing saved-run ID.
    """
    from psychophysics_lab.authoring import inventory
    from psychophysics_lab.paths import find_repo_root
    managed = {i.name for i in inventory(find_repo_root()) if i.kind == "experiment"}
    names = []
    for path in sorted(Path(__file__).parent.parent.glob("*.py")):
        if path.stem.startswith("_") or path.stem in managed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (SyntaxError, OSError, UnicodeError) as exc:
            warnings.warn(f"Experiment {path.name} was not loaded: {exc}. Correct the file and restart PsyCoLab.", RuntimeWarning)
            continue
        declares_spec = any(
            isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
                isinstance(target, ast.Name) and target.id == "SPEC"
                for target in (node.targets if isinstance(node, ast.Assign) else [node.target]))
            for node in tree.body)
        if declares_spec:
            names.append("psychophysics_lab.experiments." + path.stem)
    return tuple(names)


def load_contributions():
    global _loaded, _loading
    if _loaded or _loading:
        return
    from .source_names import SOURCE_IDS
    from psychophysics_lab.contributions import EXPERIMENT_MODULES, ADAPTIVE_MODULES
    from psychophysics_lab.adaptive import registry as adaptive
    from psychophysics_lab.experiments._internal import registry as experiments
    from psychophysics_lab.stimuli import registry as stimuli
    before_exp, before_stim = dict(experiments._REGISTRY), dict(stimuli._REGISTRY)
    before_adaptive = dict(adaptive._REGISTRY)
    _loading = True
    try:
        for name in ADAPTIVE_MODULES:
            spec = importlib.import_module(name).SPEC
            if adaptive._REGISTRY.get(spec.id) != spec:
                adaptive.register_algorithm(spec)
        modules = discover_experiment_modules() if EXPERIMENT_MODULES is None else EXPERIMENT_MODULES
        for name in modules:
            previous = (dict(experiments._REGISTRY), dict(stimuli._REGISTRY), dict(adaptive._REGISTRY))
            try:
                spec = importlib.import_module(name).SPEC
                if EXPERIMENT_MODULES is None and spec.id != SOURCE_IDS.get(name.rsplit(".", 1)[-1], name.rsplit(".", 1)[-1]):
                    raise ValueError(f"{name}: SPEC.id must match its Python filename")
                experiments.register_experiment(spec)
            except Exception as exc:
                if EXPERIMENT_MODULES is not None:
                    raise  # Explicit embedded contribution sets remain atomic.
                for registry, before in zip((experiments._REGISTRY, stimuli._REGISTRY, adaptive._REGISTRY), previous):
                    registry.clear()
                    registry.update(before)
                warnings.warn(f"Experiment {name.rsplit('.', 1)[-1]}.py was not loaded: {exc}. Correct the file and restart PsyCoLab.", RuntimeWarning)
        # The only authoritative non-CSF visual stimulus definitions are
        # classes in stimulus_library.py; no per-stimulus registry entries.
        from psychophysics_lab.stimulus_library import library_stimulus_specs
        for spec in library_stimulus_specs():
            if spec.id not in stimuli._REGISTRY:
                stimuli.register_stimulus(spec)
        # Published researcher components join the ordinary experiment catalogue.
        from psychophysics_lab.paths import find_repo_root
        from psychophysics_lab.authoring import load_authored
        # Skip and report broken/stale published modules; never block working
        # built-in experiments or silently launch an untested revision.
        problems = load_authored(find_repo_root(), include_drafts=False, tolerate_errors=True)
        if problems:
            warnings.warn("Invalid or untested published components were NOT loaded: "
                          + "; ".join(f"{name}: {reason}" for name, reason in problems.items()),
                          RuntimeWarning)
        # JSON-only experiments reuse the very same experiment registry and
        # RunContext/TrialTimeline executor, never a separate acquisition path.
        from psychophysics_lab.experiments._internal.library_builder import load_library
        library_problems = load_library(tolerate_errors=True)
        if library_problems:
            warnings.warn("Invalid/stale JSON library experiments were NOT loaded: "
                          + "; ".join(f"{name}: {reason}" for name, reason in library_problems.items()),
                          RuntimeWarning)
        _loaded = True
    except Exception:
        experiments._REGISTRY.clear()
        experiments._REGISTRY.update(before_exp)
        stimuli._REGISTRY.clear()
        stimuli._REGISTRY.update(before_stim)
        adaptive._REGISTRY.clear()
        adaptive._REGISTRY.update(before_adaptive)
        raise
    finally:
        _loading = False
