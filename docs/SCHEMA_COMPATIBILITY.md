# Persisted-file version and backwards compatibility policy

**Purpose:** keep historical psychophysics data and laboratory calibration interpretable after PsyCoLab changes. This is a documentation policy and an inventory of verified current writers, **not** a migration of existing records.

## Verified current version markers (23 October 2026)

| Object | Writer / format | Current known marker | Notes |
|---|---|---|---|
| Canonical run manifest | `core/runner.py`, `manifest.json` | `schema_version: 3` | Also records data layout, current status, software/Git provenance, registered source SHA-256, selected profile |
| Requested experiment configuration | `core/runner.py`, `experiment_config.json` | `schema_version: 2` | Contains selected input and normalized values; do not substitute current defaults on replay |
| Workspace convenience state | `data/workspace.py`, `psycolab_data_config.json` | `schema_version: 3` | Not the authoritative scientific record |
| Data directory layout | `data/workspace.py` and `docs/DATA_LAYOUT.md` | `data_layout_schema_version: 1` | Separate from a JSON item's own version |
| Canonical trial table | `data/trials.py` | `TRIAL_SCHEMA_VERSION = 1` | Saved dictionary describes columns/meanings for the actual run |
| Active luminance dataset | `config/calibration_dataset.py`, `luminance.json` | `schema_version: 1` plus its evolving `version` | Dataset revision count is not a schema version; physical validation is independent |
| Project-local component inventory | `authoring/components.json` | `schema_version: 1` | Tracks Draft/Test/Ready fingerprints |
| Local repository data-root preference | `data/workspace.py`, `.psycolab_local.json` | `schema_version: 1` | Machine-specific convenience pointer; ignored by Git |
| Monitor profile | `config/models.py`, revisioned profile JSON | `revision` is present | **Do not equate revision with schema**; a uniform schema marker has not been confirmed |
| Resolved scientific configuration, scenario report and derived outputs | Various code paths | **Not fully inventoried** | Check actual writers, readers, version fields and scientific units before assigning schema numbers |

A software version such as `0.2.2`, a Git commit, a monitor `revision` and a schema version are **different identities**. Do not confuse them.

## Reader contract

1. Recognize a known older schema and either load it **without modifying it**, or offer an explicit reviewed migration.
2. Reject an unknown/newer schema with an actionable error. Do not silently reinterpret unknown columns or missing scientific settings.
3. Scientific values, stimulus contrast definitions, angular units, trial response meanings, and presented-versus-next adaptive state must not be guessed or backfilled.
4. Do not fabricate missing photometry/timing measurements or treat a nominal 10-bit display as an accepted calibrated output.
5. Where existing older records legitimately lack a new field, document exactly which neutral/default value is *semantically safe*. If not safe, require researcher input or report an unsupported record rather than guessing.
6. Keep data-root paths portable and avoid tying historical runs to one computer's absolute Windows username/folder layout.

## Migration contract

- Migration is **opt-in**, not a side effect of launching PsyCoLab or pulling Git changes.
- Create an exact-byte backup and record its SHA-256 before changing any mutable configuration; show source/target versions and a human-readable field diff.
- Prefer writing a new output file with a reference to its source, leaving the original untouched. This rule is especially strict for canonical trials, original manifests, raw calibration readings and timing evidence.
- Make migrations idempotent, independently testable and reversible where practical.
- Refuse to coerce scientific parameters, monitor geometry, luminance units or response coding unless the researcher explicitly resolves the ambiguity.
- Test each supported legacy schema version with fixtures, unexpected/unknown versions, corrupted/truncated input, partial data and interrupted writes.
- Never interpret an old scientifically different protocol as the new one because it shares a convenient display name. Preserve stable experiment IDs and the existing documented source-identity compatibility map.

## Next code PRs required

1. Build a **writer/reader inventory** for all persisted JSON/TSV objects, including monitor profile, resolved configuration, scenario report, analysis estimates, presets, calibration evidence and runtime displays.
2. Document which exact old schemas the current code can already read; add non-identifying real historical fixtures.
3. Add shared but minimal format-specific validation. Avoid an indiscriminate 'global schema manager' that obscures scientific ownership.
4. Add targeted, non-destructive migration functions **only for demonstrated compatibility gaps**, with a separately reviewed PR per data family.
5. Update release notes for every intentional compatibility change. Do not claim all data schemas are now versioned from this documentation update.

For acquisition semantics and layout, see [data layout](DATA_LAYOUT.md) and [trial dictionary](TRIAL_DATA_DICTIONARY.md).

## Public read-only data access (trial schema 1)

The supported analysis entrypoint is `psychophysics_lab.data.reader.load_run(path)`.
It reads the run's actual `trials.tsv` header by **column name** into NumPy
text arrays, preserving extra experiment-specific fields and allowing genuinely
older runs to omit later optional fields. The saved dictionary remains the
source for experiment-specific units and response-code meanings; no missing
values are fabricated. The reader accepts known trial schema **1** and explicitly
rejects unknown future numbered schemas until their scientific definitions have
been reviewed. Unversioned archived TSVs can be inspected, but are not certified.

This is **read-side tolerance**, not a change to the current acquisition writer:
`TrialLog` and the strict `validate_run.py` currently use the exact 20-column
trial-schema-1 format. Future appended acquisition fields require a separate
planned schema/writer update, with correct per-run data dictionaries and old-run
regression fixtures. Never rewrite completed canonical observations to add
columns. See [analysing saved run data](ANALYSING_RUN_DATA.md).
