"""Two-interval ellipse/probe reconstruction; unresolved source is never hidden."""
from .flanker_protocol import definition, run_protocol


def procedure(run):
    return run_protocol(run, family="ellipse")


SPEC = definition("ellipse_2d", procedure, ellipse=True)
