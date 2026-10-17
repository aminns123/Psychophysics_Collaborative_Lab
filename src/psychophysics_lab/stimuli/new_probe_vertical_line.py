"""Compatibility import for original researcher's vertical-line ID.

Scientific definition now lives in stimulus_library.ResearcherVerticalLine.
Legacy data and IDs remain unchanged. Retest this source before human use.
"""
from ..stimulus_library import ResearcherVerticalLine as _Definition

PARAMETERS = _Definition.PARAMETERS
render = _Definition.render
SPEC = _Definition.SPEC
