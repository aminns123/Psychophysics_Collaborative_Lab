"""Indirect flanker procedure; shared paired task code lives in flanker_protocol."""
from .flanker_protocol import definition, run_protocol


def procedure(run):
    return run_protocol(run, family="indirect")


SPEC = definition("indirect_flanker", procedure)
