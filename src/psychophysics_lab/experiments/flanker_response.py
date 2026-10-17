"""CSF family entry point: retain the scientifically authoritative implementation.

The old 'flanker_Response' is an event-handler name, also used by the line
probe/indirect tasks; it is not an unambiguous experiment identifier. Existing
PsyCoLab CSF runs MUST continue to use contrast_sensitivity and its renderer.
Use simulations.csf_actions for existing fixture-backed action-state parity.
"""
from .contrast_sensitivity import CSF_SPEC as SPEC
