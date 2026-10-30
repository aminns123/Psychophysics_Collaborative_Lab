"""Presentation-only grouping of experiment configuration fields.

Configure renders only Universal setup. The same declared fields, validators
and stimulus controls are available in Review's generic parameter editor.
Scientific condition/geometry/timing groups never appear in Configure.

The grouping cannot change ConfigField keys, defaults, scientific validation,
saved settings or trial data; experiment authors may keep declaring sections.
"""

from __future__ import annotations

from collections import OrderedDict

# Shared setup *roles*. No experiment ID or grating-specific parameter is
# assumed. A local study may define entirely different scientific conditions.
_COMMON_SETUP_KEYS = frozenset({
    "contrast_method", "max_trials", "trial_count", "random_seed",
})


def grouped_config_fields(experiment):
    """Return ordered (section, fields) pairs for any ExperimentSpec.

    An unknown field declared in the default 'Experiment' section is not
    discarded: it belongs to Review's generic scientific input editor.
    All schema fields are returned exactly once, without mutating the spec.
    """
    adaptive_controls = set(experiment.adaptive.controls) if experiment.adaptive else set()
    by_section = OrderedDict()
    for field in experiment.fields:
        if field.key in _COMMON_SETUP_KEYS:
            section = "Universal setup"
        elif field.section == "Constant stimuli":
            section = "Constant stimuli"
        elif field.key in adaptive_controls or field.section == "Adaptive settings":
            section = "Adaptive settings"
        elif field.section in {"Experiment", "Display and contrast"}:
            section = "Experiment-specific parameters"
        else:
            section = field.section or "Experiment-specific parameters"
        by_section.setdefault(section, []).append(field)

    first = ("Universal setup", "Adaptive settings", "Constant stimuli")
    return [(section, by_section.pop(section)) for section in first if section in by_section] + list(by_section.items())
