"""Built-in EXPERIMENT and ADAPTIVE declarations (not a stimulus registry).

All visual stimuli are independent LibraryStimulus classes in the single
stimulus_library.py. They register automatically: no companion modules or
extra ID lists. Experiments remain separate to preserve scientific procedures.
"""
EXPERIMENT_MODULES = (
    "psychophysics_lab.experiments.example_experiment",
    "psychophysics_lab.experiments.orientation_task",
    "psychophysics_lab.experiments.orientation_adaptive",
    "psychophysics_lab.experiments.indirect_flanker",
    "psychophysics_lab.experiments.base_flanker",
    "psychophysics_lab.experiments.ellipse_2d",
)
ADAPTIVE_MODULES = ("psychophysics_lab.adaptive.legacy_flanker",)
