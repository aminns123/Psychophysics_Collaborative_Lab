# Changelog

Notable changes to PsyCoLab. For a reproducible laboratory analysis or acquisition, retain the exact software tag/commit, scientific source hashes, experiment settings and monitor calibration provenance.

## Unreleased

- **Issue #81 compatibility audit (proposed):** inventory current run, profile, photometry, preset, simulation and derived-analysis writers/readers, distinguishing known schema markers from profile and data revisions.
- **Read-only historical-shape regressions (proposed):** exercise unversioned trial tables, older monitor metadata, legacy summary-only luminance, old workspace requests, moved archives, malformed/unknown formats and truncated journals. Fixtures are synthetic/non-identifying, not measured participant or hardware evidence.
- **Small reader safeguard (proposed):** reject unknown newer `manifest.json` schema versions, without modifying existing acquisition records or the fixed trial schema.
- **No scientific protocol, calibration gate, acquisition writer or saved raw-data format changes.** Actual historical laboratory archives and end-to-end international extension compatibility remain separate tasks.



## 0.3.0 — prepared pre-release (not tagged or published yet)

- **New public data reader:** `psychophysics_lab.data.reader.load_run(path)` reads an existing run folder or `trials.tsv` into named NumPy text arrays, a manifest and the saved column definitions.
- **Backwards-compatible access:** tolerates additional named columns in known trial schema 1, retains absent historical columns as absent, and rejects unknown numbered trial schemas.
- **Researcher documentation:** new `docs/ANALYSING_RUN_DATA.md` guide and a Learn / Help link to a copyable Python example.
- **Version metadata:** Python package version advances from `0.2.2` to `0.3.0`, corresponding to the future GitHub tag `v0.3.0`.
- **Scientific scope:** no changes to canonical acquisition writer, existing twenty trial fields, trial schema version, calibration, adaptive algorithms or participant presentation.
- **Focused validation:** 25 tests passed on the user's Windows Python 3.11 environment on 24 October 2026; full-suite and physical qualification are separate release gates.

Read the proposed [v0.3.0 release notes](docs/releases/v0.3.0.md) before publishing.

## v0.0.1 — published 24 October 2026

The first GitHub release is preserved at its historical commit `f2b981f`. The software at that commit identified internally as `0.2.2`; this inconsistency is not rewritten in an already-published archive. See the [original release](https://github.com/aminns123/Psychophysics_Collaborative_Lab/releases/tag/v0.0.1).

## Historical development / governance notes (predating the next release)

### International laboratory governance and documentation

- Document the three-layer architectural direction: shared core, curated public experiments/stimuli, and proposed independent lab-local extensions.
- Explain safe Git updates, local scientific edits, forks/branches, local TUI presets and external calibration/acquisition storage.
- Clarify experiment/stimulus contribution requirements and distinguish scientific software readiness from physical acquisition qualification.
- Record known persisted-file schemas and a no-silent-migration compatibility policy.
- Introduce release evidence requirements, including licensing, package/environment reproducibility and laboratory hardware checks.
- No scientific runner, stimulus, adaptive, calibration or participant-data-format change is part of this documentation update.

### Earlier merged work

- **PR #78 — Slate Precision (Design E):** visual palette, Setup context layout and researcher screen grouping, with TUI regression tests.
- **PR #77 — Laboratory Control Console (Design B):** researcher-facing sidebar, shared header, responsive navigation and nested-page layout.
- **PR #76 — Response-key guidance toggle:** optional response-stage instructions, defaulting to prior behaviour.
- **PR #75 — CSF envelope boundary:** smooth finite Gaussian grating support, documented cutoff.
- **PRs #73–#74 — authoring/source cleanup and follow-up:** retired implementations and updates to tests for the current scientific pipeline.

The above are PR summaries, not separate version releases. For exact semantics and tests, inspect the corresponding PR diff and documented experiment configurations.

### Version policy

See [Release policy](docs/RELEASE_POLICY.md), [schema compatibility](docs/SCHEMA_COMPATIBILITY.md) and [international roadmap](docs/INTERNATIONAL_LAB_ROADMAP.md). Historical runs must retain their own source and profile provenance independently of this text.
