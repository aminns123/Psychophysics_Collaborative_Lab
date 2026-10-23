# Markdown documentation audit — 2026-10-23

**Scope:** a repository-wide scan of **56 existing Markdown files** on the Design E merged `main` source tree, followed by targeted review of current installation, authoring, Git contribution, experiment discovery, run provenance, schema and TUI documentation. This is not an assertion that all historical laboratory scientific content was manually revalidated.

## Changes proposed in this documentation PR

- `README.md`: clear safe-update and lab-local code pathways.
- `CONTRIBUTING.md`: correct automatic public `SPEC` discovery (the old "register explicitly" instruction was stale) and link to the scientific acceptance checklist.
- `docs/AUTHORING_CONTRACT.md`: remove a brittle claim about "nine" public experiment files and identical loop signatures; preserve a common authoring narrative without erasing task-specific science.
- `docs/TUI_HUB.md`: current persistent sidebar / F6 / Design E presentation.
- `docs/EXTENDING_PSYCOLAB.md`, `docs/ARCHITECTURE.md`: distinguish existing supported Python locations from the future independent external extension workspace.
- `docs/INSTALLATION.md` and `docs/USER_ENV.md`: local Python ownership, preservation on update and the difference between development terminal and supported acquisition.
- New `docs/SAFE_UPDATES_AND_LOCAL_WORK.md`, `docs/CONTRIBUTING_EXPERIMENTS.md`, `docs/SCHEMA_COMPATIBILITY.md`, `docs/RELEASE_POLICY.md`, `docs/INTERNATIONAL_LAB_ROADMAP.md` and `CHANGELOG.md`.

## Links and historical documents

The Markdown link/path scan identified **three** relative references in `docs/LOCAL_BUG_AUDIT_2026-10-11.md` that no longer exist on current `main`:

- `../src/psychophysics_lab/_reference_csf/adaptive_session.py`
- `../src/psychophysics_lab/_reference_csf/contrast_sensitivity_function.py`
- `../src/psychophysics_lab/_reference_csf/libC.py`

These belong to a **dated historical audit**, not an instruction for a new researcher. Their obsolete paths remain part of the evidence describing the older tree; a prominent historical notice is added. Do not silently rewrite the old audit into a claim about current code. The other scanned Markdown relative links had no missing target in the baseline repository tree; anchor semantic checks and links constructed outside standard Markdown syntax were not exhaustively verified.

## Work explicitly not certified by this docs scan

- Source-validity/reproducibility of old thesis-derived scientific claims across all historical reports.
- Each saved-file reader's support for historic schema versions; see [compatibility inventory](SCHEMA_COMPATIBILITY.md).
- A working external local extension loader; see [acceptance gates](INTERNATIONAL_LAB_ROADMAP.md).
- Calibration or acquisition readiness on any overseas monitor/GPU/photometer.
- Existing full-suite failures, which should be tracked separately from documentation.
- Software licence/redistribution rights: owner/institution review remains necessary.

This is a conservative documentation audit intended to correct current guidance without erasing important historical provenance.
