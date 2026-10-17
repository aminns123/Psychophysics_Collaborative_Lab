"""Matched baseline: identical protocol, with the grating removed."""
from .flanker_protocol import definition, run_protocol


def procedure(run):
    return run_protocol(run, family="base")


SPEC = definition("base_flanker", procedure)
