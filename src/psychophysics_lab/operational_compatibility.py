"""Retain portable identity for reviewed, non-scientific source changes."""

# The v0.4.0 portable format fingerprints both modules. The recovery change
# recognises an additional verified interpreter location and leaves experiment
# and configuration semantics intact. The sharing change applies this mapping.
# Each mapping requires the exact reviewed bytes after newline normalization.
# Run provenance continues to record the actual files, including these changes.
_V040_EQUIVALENT = {
    "src/psychophysics_lab/core/environment.py": (
        "6144c5da604e15f380962877a87ec372081e037ab2d787bf3546567134b8e577", "d83355fbee467d75c8e91cb3a9ff0029dba3be9477186317192ece8fff0c2302",
    ),
    "src/psychophysics_lab/config/sharing.py": (
        "9ecaf56d1f47aec0c0366f90ca46cb70c685fcff9ecf9a256e6bac0d9a2ec48d", "9bcc911d368883fd8b3d456c81f0943dbaca88142ed4df814725fbfe959c2c9e",
    ),
}


def portable_engine_inventory(inventory):
    if all(inventory.get(path) == reviewed for path, (reviewed, _) in _V040_EQUIVALENT.items()):
        return inventory | {path: baseline for path, (_, baseline) in _V040_EQUIVALENT.items()}
    return inventory
