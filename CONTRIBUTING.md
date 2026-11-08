# Contributing to PsyCoLab

PsyCoLab welcomes contributions that make experiments easier to read, configure,
test and reproduce. Start with the [scientist-first authoring model](docs/SCIENTIST_FIRST_AUTHORING.md)
and the [contributor checklist](docs/CONTRIBUTING_EXPERIMENTS.md).

- Start new science in an [independent laboratory extension](docs/LABORATORY_EXTENSIONS.md)
  with a unique identity. Propose a reviewed change to official PsyCoLab on a
  dedicated branch or fork targeting `develop`.
- Use **Windows 11 and 64-bit Python 3.11** for the supported researcher workflow.
- Never silently change scientific or stimulus behaviour. Scientific changes
  require explicit review, including mathematics, timings, response mappings,
  contrast definitions, monitor calibration and geometry.
- Keep the experiment's choices, methods and shared-runner connection in one
  A1/A2/B Python file with a matching `SPEC` and one `STIMULI` map. Use the
  existing Draft/Test/Ready source checks where applicable.
- Declare units, validation and help text so the generic Review editor can expose
  the intended scientific values. Save and share selected values through the
  [existing JSON workflow](docs/SHARING_CONFIGURATIONS.md).
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

Tests and the portability check should pass before commit. Hosted Windows CI
runs scientific smoke, four full-suite shards and the required Windows check.
Native Windows 11 researcher acceptance and physical display, rendering and
timing claims require separate evidence.
For data-integrity work, test `scripts/validate_run.py` against synthetic runs.

Describe the problem, resulting behaviour and validation in each contribution.
Keep scientific changes explicit and separate from infrastructure cleanup.

## Licensing

PsyCoLab software uses the [BSD 3-Clause licence](LICENSE). Confirm that you
have permission to submit your contribution under those terms. Record
authorship, preferred credit and any third-party material or notices in the PR.
See the [third-party notices](THIRD_PARTY_NOTICES.md) and
[release policy](docs/RELEASE_POLICY.md) for distribution scope.
