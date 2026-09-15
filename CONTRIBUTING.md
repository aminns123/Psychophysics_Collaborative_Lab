# Contributing to PsyCoLab

PsyCoLab is a general psychophysics framework; CSF is its first reference experiment.
Read [the architecture](docs/ARCHITECTURE.md) before changing package boundaries.

- The supported baseline is **Python 3.11**.
- Never silently change scientific or stimulus behaviour. Scientific changes
  require explicit review, including mathematics, timings, response mappings,
  contrast definitions, monitor calibration and geometry.
- Register new experiments explicitly through the experiment registry. Keep
  experiment-specific assumptions in their specification and implementation.
- Keep acquisition data outside the Git repository. Preserve raw run records;
  put analysis outputs elsewhere.
- Canonical data-schema changes require deliberate versioning and review.
  Preserve accepted-response and presented-versus-next semantics.
- Keep runtime sources within the documented acquisition-source inventory;
  review provenance coverage when adding a new runtime boundary.
- Do not commit local `.venv`, editor settings, caches, participant data,
  runtime logs or temporary artifacts.

## Before committing

Install development dependencies in a local Python 3.11 environment:

```text
python -m pip install -e ".[dev]"
python -m pytest
python scripts/portability_check.py
git diff --check
```

Tests and the portability check should pass before commit. CI runs these safe
headless checks. Physical display validation, OpenGL rendering and stimulus
timing require separately reviewed laboratory tests; CI does not validate them.
For data-integrity work, test `scripts/validate_run.py` against synthetic runs.

Describe the problem, resulting behaviour and validation in each contribution.
Keep scientific changes explicit and separate from infrastructure cleanup.

## Licensing

No software licence has been selected. Repository-owner approval is required
before adding a licence; do not infer licensing terms from this document.
