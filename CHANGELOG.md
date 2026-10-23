# Changelog

Notable PsyCoLab changes are recorded here. This file begins a maintained change history; it is **not** a claim that any named production release or version tag has been published. Older historical details remain in Git commits and their pull requests.

## Unreleased — international laboratory governance and documentation

- Document the three-layer architectural direction: shared core, curated public experiments/stimuli, and proposed independent lab-local extensions.
- Explain safe Git updates, local scientific edits, forks/branches, local TUI presets and external calibration/acquisition storage.
- Clarify experiment/stimulus contribution requirements and distinguish scientific software readiness from physical acquisition qualification.
- Record known persisted-file schemas and a no-silent-migration compatibility policy.
- Introduce release evidence requirements, including licensing, package/environment reproducibility and laboratory hardware checks.
- No scientific runner, stimulus, adaptive, calibration or participant-data-format change is part of this documentation update.

## Recent merged changes (not formally tagged releases)

- **PR #78 — Slate Precision (Design E):** visual palette, Setup context layout and researcher screen grouping, with TUI regression tests.
- **PR #77 — Laboratory Control Console (Design B):** researcher-facing sidebar, shared header, responsive navigation and nested-page layout.
- **PR #76 — Response-key guidance toggle:** optional response-stage instructions, defaulting to prior behaviour.
- **PR #75 — CSF envelope boundary:** smooth finite Gaussian grating support, documented cutoff.
- **PRs #73–#74 — authoring/source cleanup and follow-up:** retired implementations and updates to tests for the current scientific pipeline.

The above are PR summaries, not separate version releases. For exact semantics and tests, inspect the corresponding PR diff and documented experiment configurations.

## Version policy

See [Release policy](docs/RELEASE_POLICY.md), [schema compatibility](docs/SCHEMA_COMPATIBILITY.md) and [international roadmap](docs/INTERNATIONAL_LAB_ROADMAP.md). Historical runs must retain their own source and profile provenance independently of this text.
