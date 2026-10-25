# Issue #81 — persisted-data compatibility inventory (24 October 2026)

**Status: first read-only audit; not a claim that every historical data format is supported.**

This is an inventory of the files that current PsyCoLab source actually writes or
loads. It distinguishes **schema versions** from **software versions, profile
revisions, dataset revisions, scientific protocol IDs and analysis versions**.
Do not invent a schema marker for a format whose writer does not emit one.

This audit made *no* changes to the experiment runner, stimulus code, adaptive
equations, data acquisition headers, raw photometer measurements or TUI layout.

## Canonical acquisition records

| Saved file | Current writer | Relevant reader / validator | Known marker | Meaning and compatibility constraint |
| --- | --- | --- | --- | --- |
| `run_NNN/manifest.json` | `core/runner.py` | `data/reader.py`, `scripts/validate_run.py`, `analysis/*.py` | `schema_version=3`; separate `trial_schema_version=1` | Run identity, status, experiment, profile and source hashes. The public reader returns its metadata without silently migrating it. It rejects newer unknown manifest schema versions; the strict validator supports current v3. |
| `trials.tsv` | `data/trials.TrialLog` | `data/reader.load_run`, `analysis/primary.py`, `analysis/previews.py`, `analysis/thresholds.py`, `scripts/validate_run.py` | Trial-schema **1** (20 core columns) | Authoritative accepted responses; `presented_*` means actual presented strength, `next_*` is post-response. Public reading uses names and preserves additive fields. Writer and strict validator still require exactly the current 20 columns. |
| `trial_data_dictionary.tsv` | `data/trials.write_trial_data_dictionary` | `data/reader.py`, `scripts/validate_run.py`, `analysis/previews.py` | `trial_schema_version=1` on dictionary rows | Per-run column order, logical type, units, meaning and experiment-specific codes. Never substitute today's dictionary for one missing from an archived run. |
| `trials_readable.txt` | `data/trials.write_readable_trial_table` | Human readers and `scripts/validate_run.py` | No independent schema | Derived fixed-width copy of TSV; rebuildable, **not** canonical. |
| `experiment_config.json` | `core/runner.py` | `scripts/validate_run.py`, run inspection | `schema_version=2` | Normalised scientific choices and portable request snapshot. Do not replay with present-day defaults. |
| `monitor_profile.json` | `core/runner.py` snapshot of `MonitorProfile.to_dict()` | `config/monitor._profile_from_dict`, validator | No universal schema marker observed; `revision` is **not** a schema | Geometry, display binding, photometry/qualification metadata as captured for that run; identity and evidence are experiment-specific. |
| `runtime_display.json` | `researcher.RunContext.initialise` and runner/graphics runtime | `analysis/thresholds.py`, `scripts/validate_run.py` | No uniform marker confirmed | Observed/declared runtime display, mode, geometry and timing status; software timing is not measured photon timing. |
| `resolved_experiment.json` | `researcher.RunContext.save_resolution` | `analysis/primary.py`, `analysis/previews.py`, `analysis/thresholds.py` | **No top-level schema marker** in the generic writer | Exact experiment-owned scientific protocol and estimator; do not re-interpret it from a newer experiment implementation with the same name. |
| `stimulus_parameters.json` | `core/runner.py` | Run validator, source/stimulus snapshot inspection | `schema_version=1` | Exact selected stimulus slots and saved parameter documents; snapshot hashes and sources matter. |
| `trial_context.json` | `core/runner.py` | Validator, run inspection | `schema_version=1` and `trial_schema_version=1` | Trial-level provenance, digital contrast context, monitor/profile and synthetic timebase declarations. |
| `adaptive_session.json` | `researcher.RunContext.save_adaptive` or retained adapter | `scripts/validate_run.py`, `analysis/thresholds.py` | Adapter-dependent; **do not assume a universal version** | Staircase identity, reversals, state, completion. The algorithm and its scientific meaning must match the run. |
| `trial_events.jsonl` | `researcher.RunContext` via `data/session.append_json_record` | `data/session.read_json_records`, validator | `schema_version=1` **per journal object** | Append-only event trace. Truncated final line is explicitly rejected, not silently discarded. |
| `procedure_lifecycle.json` | `researcher.RunContext._save_lifecycle` | `scripts/validate_run.py` | `schema_version=1` | Counts and declared completion, independent of raw data; never infer trial success from a filename alone. |
| `trial_actions.json`, `trial_presentations.json`, `adaptive_history.json` | `researcher.RunContext` | Validator and inspection tools | Each current writer uses `schema_version=1` | Procedure/action provenance; different from canonical trial responses. |
| `primary_thresholds.json` | `researcher.RunContext.save_primary` and `analysis/previews.py` | Analysis/preview tools | No uniform top-level marker established here | Experiment-declared derived estimates; keep apart from the participant's raw observations. |
| `state/*.runtime.json`, `state/*.initial.json`, `state/*.final.json` | `researcher.configure`, `core/runner.py` | Diagnostics/validator, retained adapters | No uniform independent marker | Run-owned scientific state snapshots, copied rather than migrated on read. |
| `legacy_response.txt` | Retained adapter / run bridge | Historical analysis only | Legacy positional structure, **not** trial schema 1 | Not the preferred current data. Legacy post-response contrasts are not the current presented contrasts. |
| `scenario_report.json`, `SYNTHETIC_DATA.json`, `UNCALIBRATED_TEST_DATA.json` | `simulations/scenarios/run.py`, `core/runner.py` | Validator/scenario consumers | Scenario report `schema_version=1`; synthetic/test markers not uniformly schema-versioned | Explicitly non-human or uncalibrated trial provenance; never treat as certified participant observations. |

## Local configuration and laboratory evidence

| Saved file / family | Current writer | Reader / validation | Known marker | Meaning and risk |
| --- | --- | --- | --- | --- |
| `psycolab_data_config.json` | `data/workspace.save_workspace_state` | `load_workspace_state`, `request_from_workspace_state` | `schema_version=3`; separate `data_layout_schema_version=1` | Convenience state, not canonical evidence. Restored requests intentionally drop old absolute data-root paths and past researcher overrides. |
| `runs_index.csv` | `data/index.upsert_run_index` | `data/index.py` and TUI | **No schema marker**, fixed header | Convenience catalogue keyed by UUID. Writer refuses a mismatching header rather than rewriting unknown format. Run directory is authoritative. |
| `configs/monitors/*.json` and `<local>/profiles/<id>/revision_*.json` | Reference files, `config/local.save_profile` | `config/monitor.load_monitor_profiles` | No universal schema; local `revision` and `profile_uuid` | Physical geometry, photometer mapping and declared qualification. Older optional fields have documented defaults in `_profile_from_dict`; do not equate those with measured evidence. |
| `<local>/profiles/<id>/current/{profile,geometry,timing,snapshot}.json` | `config/local.save_profile` | Calibration and readiness inspection | `profile_revision` and snapshot hash, not an object schema | Convenient projections of committed monitor revision, *not* independently certified measurement. |
| `<local>/profiles/<id>/current/luminance.json` and `.history/luminance_*.json` | `config/calibration_dataset.save_active` | `load_active`, `import_observations` | `schema_version=1` plus **dataset `version`**, not the same thing | Raw or legacy summary-only intensity/luminance mapping. History and physical snapshot are safeguards. Reader refuses wrong identity/schema; never upgrade in place. |
| `calibration_templates/luminance_*.json`, `pilot_luminance.json` | `config/calibration_templates.py`, `core/luminance_session.py` | `read_luminance_measurements`, `import_observations` | `format=psycolab.luminance.measurements`, `schema_version=1` | Importable human measurements or explicitly labelled demonstration/test data; reading does not qualify calibration. |
| `calibration_sessions/<profile>/*/session.json` | `core/luminance_session.py` | Calibration import/recovery | `schema_version=1`, `kind=physical_luminance_measurement_session` | Human-entered photometer session; physical provenance distinct from validated instrument readings. Some pilot metadata contains a machine-specific `source_session_file`; do **not** assume portable absolute paths. |
| `diagnostics/output_precision/<profile>/*/session.json` and `review_*.json` | `core/precision_session.py` | `latest_precision`, `precision_status` | Session `schema_version=1`; review marker may differ | Graphics output test declarations/readings/review, not guaranteed 10-bit physical output. |
| `configs/experiments/*.json` | Versioned project experiment source/configuration | `config/experiment_parameters.settings_snapshot` | `schema_version=1` | Experiment-scoped selected defaults, checked against stable experiment ID and registered field keys. |
| `<local>/presets/<experiment>/*.json` | `config/local.save_preset` / `update_preset` | `load_presets` | Writer emits `schema_version=1` | Local experiment choices. Version-1 presets load/update normally; **unversioned** old-shaped presets may be read with a warning but are not updated in place; explicit newer/invalid schema markers are skipped with warnings, leaving files unchanged. |
| `<local>/parameter_files/<experiment>/*.json` | `ui/parameter_files.ensure_json` / `replace_reviewed_json` | `load_experiment_json` | `schema_version=1` | Explicit researcher-editable copy, exact experiment ID and fields required; original changes tracked with hashes/backups. |
| `configs/stimuli/*.json`, `<local>/stimulus_presets/<id>/*.json` | Committed stimulus configs / `config/stimulus_parameters.save_parameter_preset` | `load_parameters` / `validate_document` | `schema_version=1` | Stimulus parameter semantics owned by registered stimulus ID; unknown/newer versions rejected. |
| `authoring/components.json` | `authoring._save` | `authoring.inventory` | `schema_version=1` | Draft/Test/Ready fingerprints; source provenance is distinct from participant data. |
| `<local>/preferences.json`, repo `.psycolab_local.json` | `config/local.save_preferences`, `data/workspace.remember_data_root` | Corresponding local preference loaders | No uniform shared schema; repo-local data-root preferences record `schema_version=1` | Machine-specific, **not** portable or canonical scientific evidence. |

## Derived analysis, not acquisition

| Product | Writer | Marker / reader | Meaning |
| --- | --- | --- | --- |
| `analysis/staircase_preview.json`, `analysis/analysis_status.json`, preview PNGs | `analysis/previews.py` | `analysis_status.json` currently reports `schema_version=1`; previews are derived | Diagnostics; absence must not fabricate a threshold. |
| `analysis/primary_thresholds.json`, `analysis/threshold_vs_condition.png`, `analysis/sensitivity_vs_condition.png` | `analysis/previews.py` | Experiment-declared estimator and canonical `trials.tsv` | Quick-look/declared primary estimates, not raw evidence. |
| `analysis/thresholds/<timestamp>/threshold_analysis.json` and TSV tables | `analysis/thresholds.analyse_thresholds` | `schema_version=1`, source-file SHA-256 | Versioned exploratory estimates, retaining reversal subset/convention. |
| `analysis/latest_threshold_analysis.json` | `analysis/thresholds.py` | `analysis_version` pointer; not a file schema | Convenience pointer to latest derived analysis; source file remains authoritative. |
| `analysis/staircase_thresholds.tsv`, `analysis/threshold_by_condition.tsv`, `analysis/threshold_analysis.json` | `analysis/primary.py` | Estimator-owned, not universally versioned | Derived parameter estimates for eligible completed staircases. |

## Compatibility facts verified by code and regression fixtures

1. Trial schema **1** is written with exactly 20 defined fields, and the strict current validator expects that exact header. The public `load_run` uses **field names**, can read extra columns for an unchanged supported trial schema, rejects unknown numbered trial schemas, and does **not** rewrite a source directory.
2. `load_run` now also rejects unknown **newer manifest** schema markers (greater than current `3`) or invalid marker types. Older positive manifest markers are returned **as opaque metadata**, not reconstructed as today's schema.
3. An old-shape monitor JSON missing `revision` can load with revision zero, but it is **not** a measurement or schema qualification. Profile `revision` is an edit counter, not `schema_version`.
4. If old profiles only contain luminance means and no active raw data file, `load_active` produces **in-memory summary-only** legacy observations. It does **not invent measurement repetitions** or write converted photometry to disk.
5. Old saved workspace requests can omit response-guidance flags. Restoring one does **not** restore a previous researcher override or machine-specific data-root path.
6. A wrong/newer `luminance.json` schema is rejected without overwriting that evidence; an interrupted JSONL last record is rejected instead of silently dropping it.
7. Synthetic *old-shape* committed fixtures are marked explicitly as demonstrations and contain no real participant identities or photometer measurements. They are **not real historical laboratory archives**. The existing simulation-run test in `tests/test_public_run_reader.py` supplies actual *software-generated* run evidence.

## Known gaps — do not claim Issue #81 closed

- **Real historical fixtures** have not been supplied. Gather non-identifying, owner-approved copies of older complete runs and calibration records before declaring all old releases readable. Do **not** upload raw participant-identifiable material to public GitHub.
- The wider manifest, resolved procedure, profile/current projections, all analysis products and many optional diagnostic JSONs do **not** share a universal schema; their formats need separate family-specific tests where active readers depend on them.
- The preset loader now prevents newer/invalid schema markers from being used; read-only legacy unversioned files remain inspectable, with a warning. Genuine old preset parameters still require scientist review against the current experiment definition; the loader does not infer scientific equivalence.
- Some luminance pilot metadata records an **absolute** `source_session_file` path. This is provenance/context, not portable file identity; future portable exports should store a relative reference without rewriting historical files.
- Issue **#80** adds optional `laboratory_extensions` metadata to new schema-3 manifests; existing readers remain independent of installed source. See [laboratory extensions](LABORATORY_EXTENSIONS.md). The proposed **Issue #81 Stage 3** read-only guard recognises v1 of this *nested* provenance format, rejects explicit newer/malformed metadata, and still reads a relocated archived run without installed scientific Python. It checks **structure**, not the truth of source hashes or laboratory calibration.
- **Workspace schema guard (Stage 3 proposed):** `psycolab_data_config.json` accepts missing/older positive workspace schema markers up to version 3 and rejects explicit future, null or malformed markers. It independently checks the known `data_layout_schema_version=1` when present, preserving original bytes and preventing outdated software from rewriting an unknown workspace. This is a convenience file, not physical or acquisition evidence.
- **Explicit versus absent schema markers (Stage 3 proposed):** unversioned historical manifests remain readable, while an explicitly present `null` in either `schema_version` or `trial_schema_version` is now rejected rather than treated as omitted.
- Physical display validation, luminance calibration and timing verification remain separate from parser compatibility. A successful test says nothing about photons or hardware.
- No migration is necessary for the formats tested here. If a demonstrated old format cannot be used safely, implement **explicit opt-in, backup + hash, write-new** conversion as a different scoped PR. Never rewrite originals on `load_run`, `load_active` or ordinary TUI startup.

## Running the focused Windows checks

Use Python 3.11 and a disposable test directory **outside the data root**:

```powershell
$testRoot = Join-Path $env:LOCALAPPDATA "PsyCoLab_Test_Temp"
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
.\.venv\Scripts\python.exe -m pytest `
  --basetemp="$testRoot\pytest_issue81" `
  -p no:cacheprovider -q `
  tests\test_issue_81_read_compatibility.py `
  tests\test_public_run_reader.py `
  tests\test_calibration_dataset_management.py `
  tests\test_validate_run.py
```

Review results **before merging**. This audit does not assume that GitHub Actions billing, the full test suite or physical laboratory verification are complete.

## Issue #80 additions (backward-compatible; no migration)

- Machine-local `preferences.json` optionally contains `extensions`: explicit enabled flag, absolute machine-local root and portable namespace. Disabled by default; this path is not canonical run identity.
- Machine-local `extension_readiness.json` has `schema_version=1` and a `components` object keyed by kind/ID, containing exact fingerprint and an explicit Ready flag. Unsupported records fail without rewriting the file.
- The laboratory-owned `psycolab_extensions.json` has `schema_version=1` and `namespace`; PsyCoLab reads it, never generates or migrates it at runtime.
- New schema-3 run manifests may contain `laboratory_extensions` with its own `schema_version=1`, namespace, experiment/component identities, source SHA-256 and readiness fingerprint. Paths are relative to the named laboratory root. The existing exact parameter snapshots, software provenance and 20-column trial-schema-1 records remain authoritative.
- No historical record is modified. `load_run()` still reads archived data without importing any installed experiment or extension.


## Issue #81 Stage 3 — Windows acceptance (proposed PR)

New non-identifying fixtures exercise copied/relocated archives containing
Issue #80's laboratory provenance, without installing their external Python.
Tests also verify that newer or damaged provenance, workspace and data-layout
versions raise actionable errors **without any write, mtime change or scientific
parameter conversion**. See
`tests/test_issue_81_extension_archive_compatibility.py`.

```powershell
$testRoot = Join-Path $env:LOCALAPPDATA "PsyCoLab_Test_Temp"
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
.\.venv\Scripts\python.exe -m pytest `
  --basetemp="$testRoot\pytest_issue81_stage3" `
  -p no:cacheprovider -q `
  tests\test_issue_81_extension_archive_compatibility.py `
  tests\test_issue_81_read_compatibility.py `
  tests\test_public_run_reader.py `
  tests\test_laboratory_extensions.py `
  tests\test_tui_save_persistence.py `
  tests\test_preset_schema_compatibility.py
```

**Status:** code and tests are in review; this specific new suite has **not**
yet been run on the maintainer's Windows machine. Do not describe the change
as independently verified until that output is supplied. Prior Issue #80
tests and virtual-run provenance are valuable evidence but not a replacement
for genuine owner-approved historical lab records.
