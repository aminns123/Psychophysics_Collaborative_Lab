"""Load the public contribution list atomically into both registries."""
import importlib

_loaded = False
_loading = False


def load_contributions():
    global _loaded, _loading
    if _loaded or _loading:
        return
    from ..contributions import EXPERIMENT_MODULES, STIMULUS_MODULES, ADAPTIVE_MODULES
    from ..adaptive import registry as adaptive
    from . import registry as experiments
    from ..stimuli import registry as stimuli
    before_exp, before_stim = dict(experiments._REGISTRY), dict(stimuli._REGISTRY)
    before_adaptive = dict(adaptive._REGISTRY)
    _loading = True
    try:
        for name in ADAPTIVE_MODULES:
            adaptive.register_algorithm(importlib.import_module(name).SPEC)
        for name in EXPERIMENT_MODULES:
            experiments.register_experiment(importlib.import_module(name).SPEC)
        for name in STIMULUS_MODULES:
            stimuli.register_stimulus(importlib.import_module(name).SPEC)
        # New LibraryStimulus subclasses are discovered in this ONE source file.
        # Researcher-owned IDs never bypass their Ready fingerprint checks.
        from ..stimulus_library import library_stimulus_specs
        from ..authoring import inventory as authored_inventory
        from ..paths import find_repo_root
        authored_ids = {item.name for item in authored_inventory(find_repo_root())
                        if item.kind == "stimulus"}
        for shared in library_stimulus_specs():
            if shared.id not in stimuli._REGISTRY and shared.id not in authored_ids:
                stimuli.register_stimulus(shared)
        # Published researcher components join the ordinary experiment catalogue.
        from ..paths import find_repo_root
        from ..authoring import load_authored
        # Skip and report broken/stale published modules; never block working
        # built-in experiments or silently launch an untested revision.
        problems = load_authored(find_repo_root(), include_drafts=False, tolerate_errors=True)
        if problems:
            import warnings
            warnings.warn("Invalid or untested published components were NOT loaded: "
                          + "; ".join(f"{name}: {reason}" for name, reason in problems.items()),
                          RuntimeWarning)
        # JSON-only experiments reuse the very same experiment registry and
        # RunContext/TrialTimeline executor, never a separate acquisition path.
        from .library_builder import load_library
        library_problems = load_library(tolerate_errors=True)
        if library_problems:
            import warnings
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
