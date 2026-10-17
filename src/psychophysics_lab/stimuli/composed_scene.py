"""Internal backwards-compatible adapter. Registered science lives in one library."""
from ..stimulus_library import ComposedScene as _Definition

PARAMETERS = _Definition.PARAMETERS
scene = _Definition.scene
validate = _Definition.validate
render = _Definition.render
frequencies = _Definition.frequencies
SPEC = _Definition.SPEC
