"""The only shared registration list contributors need to edit.

After scaffolding, add the dotted module name here, e.g.
EXPERIMENT_MODULES = ("psychophysics_lab.experiments.my_task",)
STIMULUS_MODULES = ("psychophysics_lab.stimuli.my_task",)
Every listed module exports SPEC. Restart PsyCoLab after editing this file.
Imports are explicit; no directory scanning or arbitrary plugin discovery.
"""
EXPERIMENT_MODULES = ("psychophysics_lab.experiments.orientation_task", "psychophysics_lab.experiments.orientation_adaptive")
STIMULUS_MODULES = ("psychophysics_lab.stimuli.teaching_gabor",)
ADAPTIVE_MODULES = ()
