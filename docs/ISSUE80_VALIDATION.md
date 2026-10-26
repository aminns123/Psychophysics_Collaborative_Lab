# Issue #80 — implementation and validation handoff

## Current acceptance reconciliation — 26 October 2026

Issue #80's external-source implementation is present at the
[accepted baseline](ACCEPTED_SOFTWARE_BASELINE.md). The original package-only
source-resolution blockers are historical, not current defects. Merged PRs
#93–#96 supplied the loader, source navigation, diagnostics and safe starter
onboarding; fingerprint version 2 and platform containment coverage were
subsequently verified in the accepted baseline.

The maintainer's [25 October manual evidence](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/80#issuecomment-6394511355)
and preceding issue comments record Preview/Test/Ready, a **20/20** synthetic
scenario, disabled-extension archive reading (four rows, twenty dictionary
columns, unchanged trial checksum), re-enable/discovery, and source-change
invalidation in a disposable copy. These are observed workstation results,
not newly executed checks in this documentation task.

| Original requirement | Reconciled evidence/status |
|---|---|
| Explicit trust and one independent source root | Implemented in `extensions.configure`/`validate_root`; manually observed opt-in/discovery. Starter creation does not trust or execute code. |
| One local library and experiment Python files; same procedure | Implemented through ordinary registries/development/runner; preview and completed synthetic execution observed. |
| Stable IDs, collisions, containment, import/dependency errors | Regression coverage in `tests/test_laboratory_extensions.py`; Windows junction and POSIX symlink cases run on their respective CI platforms; nested-root checks run on both. |
| Exact-source Draft/Test/Ready | Manual copied-source invalidation passed; fingerprint-v2 dependency invalidation and no silent requalification pass automated acceptance. Current real-study v2 handoff remains below. |
| TUI source navigation and configuration | External Python/preset resolution and Review paths have passing TUI tests; native editor association/path handoff remains below. |
| Portable manifest and source-independent archive reading | Manual scenario/provenance and disabled-extension checksum checks passed; current reader/validator regressions pass. |
| Framework update preserves lab-owned files | External-root separation and byte-preservation/relocation regressions implemented. Deliberate source copying/PR promotion is documented; no automatic study bundler is implied. Full installation/update/rollback rehearsal is Issue #82 stage 5. |
| Windows/Linux focused regressions | Both platforms pass at the accepted commit. This supersedes the historical headless-CI deferral; physical Linux/macOS qualification is not claimed. |
| Human gates remain distinct from software readiness | Import never grants Ready or physical verification. Existing explicit researcher override may waive outstanding calibration/protocol requirements with provenance; essential validity/hardware checks remain. The extension feature adds no independent bypass. |

### Only remaining Issue #80 manual handoff

1. Restart on the accepted revision, confirm the intended external root and
   current fingerprint-v2 readiness. If unchanged source is Draft after the
   v2 update, the researcher deliberately performs normal Preview/Test/Ready
   and a short synthetic check. Do not edit readiness JSON or automatically
   requalify real studies. Earlier pre-v2 Ready evidence does not establish
   the current real study's status.
2. Open that study's Python file and optional preset from the TUI using the
   configured native editor; confirm the intended external paths and their
   association with Review. Record date, commit/source identity and outcome
   without publishing private paths or participant information.

Keep Issue #80 open pending this handoff and maintainer review. Do not repeat
completed trust/archive/invalidation work solely because old checkboxes were
unchecked. Physical apparatus qualification is separate; installation and
rollback acceptance follow the [Issue #82 roadmap](ISSUE82_RELEASE_ROADMAP.md).

## Historical handoff — 24–25 October 2026

The remainder is preserved as the dated record of earlier failures, partial
suites and instructions. Its pending/future-tense statements are superseded
by the reconciliation above and are **not current work orders or baseline
failure claims**. Do not erase those results or relabel them as passes.

**Updated status notice — 25 October 2026:** This report is a dated
handoff and contains historically accurate failures and partial suites;
those failures should **not** be interpreted as the latest Windows baseline.
The maintainer's later complete `main` regression at `98f4119` has
**1505 passed, 0 failed, four warnings (exit 0)**. The separate official
`new_probe_vertical_line_stimulus` subsequently completed `--dev-test`
and `--dev-ready` (software only). Manual acceptance of an independent
**lab-owned extension** on the actual Windows workstation is **still pending**;
see the
[living acceptance checklist](WINDOWS_RELEASE_ACCEPTANCE_AND_STRESS_TEST_PLAN.md).
Issue #80 remains open. No physical display qualification was produced.

**Recorded 24 October 2026.** This report reconstructs the interrupted Work session
from its user-provided execution summary and the reviewed GitHub `main` tree. It
does **not** present console transcripts that are unavailable here, and it does
**not** claim Windows or hardware tests were re-executed during this follow-up.

## Changes already merged

- Baseline before Work's implementation: `c88d43be4bb63a8957ae5546732ce96c825770c2` (Issue #81 PR #92).
- Issue #80 implementation: **[PR #93](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/93)**,
  merged into `main` at `3451ead072915e48e6eda7c99398aa18d8259bad`.
- The new `src/psychophysics_lab/extensions.py` handles explicit source-root trust,
  namespace/containment checks, source hashing, registry registration, and
  machine-local Draft/Test/Ready records.
- Existing `experiments/_internal/contributions.py`, stimulus/experiment registries,
  `development.py`, `core/runner.py`, preflight, TUI and source navigators now
  integrate the *same* experiment and rendering paths as official components.
- `examples/laboratory_extensions/` supplies an external, seven-section left/right
  experiment and one local `LibraryStimulus` class with an example JSON preset.
- `docs/LABORATORY_EXTENSIONS.md` documents the Windows setup and safe update steps.
- `tests/test_laboratory_extensions.py` contains 27 extension-focused parameterized
  test executions as reported by Work, including preview, real simulation,
  provenance, source fingerprint invalidation, source relocation, and TUI selection.
- Optional `laboratory_extensions` run-manifest metadata is additive; the canonical
  **20-column trial-schema-1 acquisition writer remains unchanged**.
- The existing public run reader can open archived run data after disabling or
  deleting the laboratory-owned source; it does not try to import deleted code.

The original Issue #80 PR has no completed scientific/validation handoff in its
PR body. The usage limit interrupted creation of this specific report.

## Reported Windows evidence, and its limits

The interrupted Work log provided to the maintainer reports:

| Scope | Reported result | Interpretation |
| --- | --- | --- |
| External extension-focused suite | **27 passed** | Includes external stimulus preview and simulation, source invalidation, origin hashes, no-extension archival read, Windows junction/path handling |
| Initial combined regression run | **290 passed, 3 failed** | Work attributed three failures to direct construction of `_PlanningContext` in a scientific-audit test |
| Baseline recheck | The same 3 failures reportedly reproduce on unchanged `c88d43b` | Reported baseline behaviour; preserve actual local logs before treating this as independently verified |
| Final TUI/authoring selection | **44 passed** | Software tests, not actual monitor presentation |
| Readiness and researcher override | **60 passed** | Does not grant physical calibration |
| Final compatibility selection | **51 passed**, including extension suite | No recorded failures in that selection |

**These are Work's reported results, not results rerun by this follow-up assistant.**
The local Windows log is the authoritative artifact for confirming the commands,
exact test IDs, exit codes and baseline equivalence. GitHub Actions remains
unreliable, and the user explicitly deferred Ubuntu/Linux/macOS validation.
The reports do **not** establish full-suite green status or physically measured
timing, luminance, output precision, monitor calibration or participant acquisition.

## Inspectable source and acceptance map

| Requirement | Implementation evidence | Remaining validation |
| --- | --- | --- |
| Trust exactly one external root | `extensions.configure`, `validate_root`; TUI `ExtensionsPanel`, CLI `--extensions-enable` | Verify trusted opt-in on user's real Windows machine |
| Namespace and path containment | `extensions.source_at`, `_plain`, `load`; junction/import/collision regression cases | Manual Windows junction/error-message check if local policies differ |
| Single library and one experiment per task | `examples/laboratory_extensions/stimulus_library.py`, `experiments/demolab__left_right.py` | Manually preview real line geometry on intended display |
| Use the normal runner | `extensions.load` registers into ordinary registries; `development.py` and `core/runner.py` reuse existing execution | Run a new representative synthetic experiment from TUI on Windows |
| Source changes invalidate readiness | `fingerprint`, `record_test`, `publish`, `check_run` | Edit a copied local stimulus and confirm retest required |
| Saved run provenance | `core/runner.py` `laboratory_extensions` and source SHA-256 | Inspect actual synthetic `manifest.json` and `trials.tsv` |
| Archived data readable without source | `data/reader.load_run` and extension test | Verify relocated copied run offline |
| TUI source navigation | `ui/setup.py`, `ui/review_files.py`, `ui/editor.py` | Confirm editor resolves machine-local paths |
| Framework update preserves lab-owned work | External folder and separate local config/data roots; byte-preservation tests | Maintain backups and independently test Git updates |
| Windows implementation focus | Local reported Windows tests and `docs/LABORATORY_EXTENSIONS.md` | User-run smoke acceptance before declaring finished |
| Other operating systems | Explicitly **deferred** | Do not describe Linux/macOS as passed |
| Physical hardware qualification | Unchanged hardware requirements | **Not provided** by this feature and must remain separately qualified |

## Maintainer Windows follow-up run — 24 October 2026

After PR #94's review branch was fetched on Windows, the maintainer ran:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  --basetemp="$testRoot\pytest_issue80_followup" `
  -p no:cacheprovider -q `
  tests\test_laboratory_extensions.py `
  tests\test_authoring_actions.py `
  tests\test_review_file_navigation.py `
  tests\test_researcher_override.py `
  tests\test_public_run_reader.py
```

Result: **81 passed, 1 failed, 1 warning** (73.01 seconds). All extension
tests, including the new external authoring preset navigation test, passed.
The sole failing test was
`tests/test_researcher_override.py::test_tui_confirmation_cancel_and_launch[hardware_runtime]`.
It deliberately injected `RuntimeError("Display driver changed")`; the
researcher-override dialog caught that simulated hardware failure, but
`_report_ui_exception` attempted to print to Textual's captured terminal
stderr, which raised `OSError: [WinError 6] The handle is invalid`. A
**separate narrow follow-up** now protects the diagnostic printer so a broken
console handle cannot mask the original failure, while retaining the local
crash log and visible dialog feedback. This was **not evidence of an actual
monitor driver failure**. The single unrelated component warning still concerns
the source-change retest required by `new_probe_vertical_line_stimulus`.

The Windows diagnostic regression and the earlier failing researcher-override
case must be retested before the diagnostic follow-up is merged. Do **not**
reinterpret 81/82 as a fully green run or claim that human display hardware
was physically validated.

## Follow-up corrections in a separate PR

This follow-up addresses only verifiable completion gaps:

1. Restore this missing `ISSUE80_VALIDATION.md` file referenced by the newly
   merged roadmap and extension guide.
2. Update user-facing documentation that still incorrectly calls extensions
   \"planned\" or \"not implemented\".
3. Correct **Build Experiments → Optional JSON preset** for a registered
   laboratory experiment: resolve its declared `default_config` from the
   external source root, not the framework's `configs/experiments` folder.
   Include a focused TUI regression test. Drafts without a registered spec
   remain inspectable through Python source; don't execute drafts merely to
   infer an optional preset file.

This is deliberately **not** another architecture rewrite or software release.
The previous `v0.3.0` pre-release tag predates Issue #80 and is unchanged.

## Windows acceptance before closing Issue #80

Starting from an up-to-date clean `main`, use only disposable test and
development folders:

```powershell
git status
git pull --ff-only origin main

$testRoot = Join-Path $env:LOCALAPPDATA "PsyCoLab_Test_Temp"
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null

.\.venv\Scripts\python.exe -m pytest `
  --basetemp="$testRoot\pytest_issue80" `
  -p no:cacheprovider -q `
  tests\test_laboratory_extensions.py `
  tests\test_authoring_actions.py `
  tests\test_researcher_override.py `
  tests\test_public_run_reader.py
```

Then follow the source-folder example in
[the laboratory extensions guide](LABORATORY_EXTENSIONS.md). Check that
enabling requires explicit trust, the preview and synthetic experiment work,
marking Ready persists across restart, editing science invalidates readiness,
the data dictionary and manifest are correct, and archives remain readable
after disabling the extension. Manually inspect the response keys/geometry
before any human experiment.

### Safe completion decision

Leave [Issue #80](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/80)
**open until the Windows acceptance results and follow-up PR are reviewed**.
Non-Windows CI and physical acceptance can be explicitly deferred rather than
silently treated as successful. Do not merge/retag on the basis of a report alone.
