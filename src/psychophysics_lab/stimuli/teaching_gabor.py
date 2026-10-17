"""Compatibility adapter — editable stimulus science lives in stimulus_library.py.

Open src/psychophysics_lab/stimulus_library.py and find class TeachingGabor.
This file preserves the historical import path and stimulus ID.
"""
from ..stimulus_library import TeachingGabor as _Definition

PARAMETERS = _Definition.PARAMETERS
render = _Definition.render
SPEC = _Definition.SPEC
