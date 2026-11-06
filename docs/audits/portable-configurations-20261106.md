# Portable configuration assessment — 6 November 2026

Base: develop `68a2649` (including the merged local-stimulus/cursor PR).

## Existing architecture

- Experiment documents already use schema 1 with `experiment_id` and complete
  `values`, validated by the installed ExperimentSpec. Local settings and presets
  remain separate from experiment Python and default configurations.
- Stimulus JSON already contains its schema, stimulus ID and complete parameter
  set. Resolved snapshots carry document/file hashes. `resolve_stimuli` applies
  declared slot families and field bindings; the experiment's actual planning
  and `prepare_stimuli` paths supply trial-controlled overrides.
- The same SetupRequest supplies Review, Test and Run. Review links selected
  JSON files, checks their bytes and loaded sources, and delegates edits to the
  existing editors. Scientific inputs include conditions, timing, responses and
  adaptive settings; no parallel list of these parameters is necessary.
- Runs already save effective experiment values, exact stimulus snapshots,
  trial/adaptive records, source/environment fingerprints and local apparatus
  provenance. Existing qualified-acquisition checks are independent of settings
  validity.

## Minimal extension

One small portable container embeds the existing experiment/stimulus documents
with response guidance and software identity. The existing experiment-document
validator is factored for reuse, rather than reimplemented. The declared fields,
stimulus validator, resolve/preflight and actual planning path remain authoritative.

Save and approved Import stage ordinary local JSON documents and their portable
copy in a new unique directory, then publish the directory atomically. Failed
validation/cancelled imports do not update active requests or drafts. Failed
writes remove the private staging directory; previous saves/data are preserved.
Review remains the settings interface. A file browser and read-only differences
table add no new scientific controls.

Source fingerprints reuse the existing inventories and source-digest helper,
with newline normalization for portable comparison outside the runner. Existing raw-byte
runner fingerprints and historical reference semantics remain unchanged. Missing
implementations and changed scientific sources/engines/dependency versions are
rejected, without importing code specified by a file. Different application
version labels alone warn when all checked scientific identities match.

The existing selected stimulus snapshots optionally record the transfer document's
canonical content hash and software identity. This survives Test, Run, simulation
and existing editor handoffs. The request model and scientific runner are unchanged,
including the exact frozen runner byte hash; no baseline test or fixture is weakened.
The local profile, calibration and saved run's effective settings remain separate
and authoritative; imported acquisition overrides are cleared.

## Verification

Regression coverage checks every official experiment's complete document and
Review import, independent recipient settings, changed/missing sources and
dependencies, LF/CRLF and folder differences, malformed/duplicate/nonfinite JSON,
size limits, failed-save rollback, cancellation, changed files during preview,
different experiment IDs, prior Review restoration and immutable source/data.

The two-researcher ellipse demonstration includes Save, export, native file
browsing, differences, approval, Review, Test and simulation handoff. A controlled
seed comparison checks byte-identical trial logs, presentation/action records
and adaptive state, plus saved effective dimensions and configuration-origin
provenance. The documented JSON example is imported by regression tests.

Native Windows targeted and frozen scientific regressions, complete Windows CI
and portability/collection results are recorded in the PR. No experiment,
stimulus, adaptive implementation, historical fixture, calibration or original
research data is modified. No automatic merge or release.
