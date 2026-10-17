"""Builtin examples and reference experiments.

New Build-generated modules are tracked through authoring/components.json,
tested in USER_env and promoted Ready without editing this file.
"""
EXPERIMENT_MODULES = ("psychophysics_lab.experiments.example_experiment", "psychophysics_lab.experiments.orientation_task", "psychophysics_lab.experiments.orientation_adaptive")
STIMULUS_MODULES = ("psychophysics_lab.stimuli.example_stimulus", "psychophysics_lab.stimuli.teaching_gabor", "psychophysics_lab.stimuli.fixation_cross", "psychophysics_lab.stimuli.vertical_line_probe")
STIMULUS_MODULES += ("psychophysics_lab.stimuli.composed_scene",)
EXPERIMENT_MODULES += (
    "psychophysics_lab.experiments.indirect_flanker",
    "psychophysics_lab.experiments.base_flanker",
    "psychophysics_lab.experiments.ellipse_2d",
)
ADAPTIVE_MODULES = ("psychophysics_lab.adaptive.legacy_flanker",)
