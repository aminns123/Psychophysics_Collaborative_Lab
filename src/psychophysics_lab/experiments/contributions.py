"""Load the public contribution list atomically into both registries."""
import importlib

_loaded = False
_loading = False


def load_contributions():
    global _loaded, _loading
    if _loaded or _loading:
        return
    from ..contributions import EXPERIMENT_MODULES, STIMULUS_MODULES
    from . import registry as experiments
    from ..stimuli import registry as stimuli
    before_exp, before_stim = dict(experiments._REGISTRY), dict(stimuli._REGISTRY)
    _loading = True
    try:
        for name in EXPERIMENT_MODULES:
            experiments.register_experiment(importlib.import_module(name).SPEC)
        for name in STIMULUS_MODULES:
            stimuli.register_stimulus(importlib.import_module(name).SPEC)
        _loaded = True
    except Exception:
        experiments._REGISTRY.clear()
        experiments._REGISTRY.update(before_exp)
        stimuli._REGISTRY.clear()
        stimuli._REGISTRY.update(before_stim)
        raise
    finally:
        _loading = False
