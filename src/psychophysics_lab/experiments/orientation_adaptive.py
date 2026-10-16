"""An independent experiment reuses the same stimulus and registered staircase."""
from .orientation_task import definition
SPEC = definition("orientation_adaptive", adaptive=True, source_path=__file__)
