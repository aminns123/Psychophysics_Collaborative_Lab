"""Built-in EXPERIMENT and ADAPTIVE declarations (not a stimulus registry).

All visual stimuli are independent LibraryStimulus classes in the single
stimulus_library.py. They register automatically: no companion modules or
extra ID lists. Experiments remain separate to preserve scientific procedures.
"""
# None discovers local experiment SPEC declarations. A tuple remains an internal
# override for embedded deployments/tests; researchers never maintain a list.
EXPERIMENT_MODULES = None
ADAPTIVE_MODULES = ("psychophysics_lab.adaptive.legacy_flanker",)
