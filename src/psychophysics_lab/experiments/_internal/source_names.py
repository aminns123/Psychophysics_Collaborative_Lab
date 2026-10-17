"""Source rename compatibility, separate from immutable saved-run identities.

The historical contrast_sensitivity ID already has different scientific semantics.
The new public file must not reassign it. Only this pre-existing rename is exempt
from the normal filename == SPEC.id rule; new experiment files still follow it.
"""
SOURCE_IDS = {"contrast_sensitivity": "csf_thesis"}


def source_name(identity):
    return next((name for name, saved_id in SOURCE_IDS.items() if saved_id == identity), identity)
