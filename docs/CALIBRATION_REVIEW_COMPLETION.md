# Calibration Review and completion

Calibration setup, physical verification and experiment qualification are separate actions. A green setup page means saved observations/configuration; it does not certify emitted light, photon timing or human acquisition.

## Page 6 — Review

Review summarizes the selected saved display, including saved/incomplete observations, the number of luminance pairs, manually declared verification, outstanding actions and explicit experiment qualifications.

- **Finish calibration setup → Return to Experiment** stays visible above the scrolling Review summary, including at 80×24. It reloads the selected saved profile, reports missing observations/verification, preserves that display selection and returns to Experiment. It does not change measurements, qualification or profile revision. Missing observations or a missing photometer do not trap the researcher. A missing/unreadable selected profile is reported; another profile is never substituted.
- **Review physical verification** opens a focused screen for geometry, physical photometry and photon timing declarations. Saved ruler evidence is needed to declare geometry verified. Actual saved photometer pairs and the instrument/method are needed to declare photometry verified. Changed Verified declarations require explicit independent laboratory-review acknowledgment. Photon timing is manually declared from independently retained instrument evidence, never inferred from software flips. Optional notes/date remain optional for entering measurements and finishing setup.
- **Check / qualify experiment** uses the registered experiment names. It shows passed/blocked hardware requirements and, when a matching experiment draft exists, validates that draft through the existing configuration validator. Explicit qualification requires all declared requirements and a separate researcher-review acknowledgment. Without a parameter draft, qualification covers the registered display requirements; final configuration and acquisition checks still apply. No arbitrary experiment IDs are needed in this normal workflow.
- **Advanced monitor profile editor** remains available for detailed edits. Back cancels without saving. Unchanged Save reports **No changes to save** and creates no revision. Changed values are explicitly saved, with existing revision history retained.

After saving focused verification or qualification, the researcher returns to updated Review. Previous/Next and the six page buttons remain available. Finish does not open a confirmation dialog.

## Qualification and safety

Experiments declare their physical requirements in `ExperimentSpec.calibration_requirements`. The CSF experiment declares geometry, photometry and timing. `qualification_checks` is shared by the qualification screen and local-display human preflight: a saved local binding/resolution, required manual geometry/declarations, an explicitly verified photometer mapping and timing declarations must hold. Configuration/contrast/spatial-sampling checks remain authoritative. A qualification list entry alone no longer bypasses these local-display requirements.

Simulations and configuration review remain available without physical qualification. The existing historical unbound reference compatibility path is retained for backward compatibility; it is not newly certified or available for local laboratory qualification. Method strings marked fake/demo/simulated/synthetic cannot supply a trusted photometry mapping or CSF human qualification, even if an old file has a Verified flag. Those pairs may remain saved as clearly unverified test data for setup/development.

Verified flags are **manual declarations**. PsyCoLab does not independently check that the researcher used a ruler, calibrated photometer or photodiode, and no universal acceptance tolerance is invented. The lab must retain instrument evidence and apply its experiment-specific criteria.

## Persistence and old readings

Local profiles continue to use append-only history and one active selected profile ID. `save_profile` checks the expected revision before comparing values. Actual changed saves create a revision; normalized identical saves return the current revision and perform no profile/preference write. Stale writers still fail, including stale no-op requests. Navigation/refresh/Finish create no profile revision.

The PR #21 luminance-reuse policy remains: older JSON can be reused only when stored intervening physical configurations and profile identity prove compatibility. Optional omitted metadata no longer erases existing saved provenance. An unchanged mapping/method/date preserves its existing review and qualification; genuinely changed data require review. No old revision or participant snapshot is deleted or rewritten. Physical setup changes still invalidate the relevant declarations and experiment qualifications.

## Implementation report

The old loop had two causes: Review completion depended on `qualified_experiments`, and its primary action opened the unrestricted profile editor. Saving unchanged profiles also allocated revisions. Review now derives setup completion from the first five stages and exposes deliberate review/qualification separately; Finish is available even when setup is incomplete.

Source changes are limited to calibration Review/navigation, focused screens, shared qualification checks, the CSF requirement declaration, no-op persistence and compatible reimports. The six-page appearance, stimulus definitions, adaptive rule/defaults and historical participant records are preserved.

Baseline: latest main `e1f59b6` (merged PRs #20/#21), clean working tree, no open calibration PRs when inspected. Implementation branch: `feature/calibration-review-completion`.

| Verification | Actual result |
|---|---|
| Baseline Windows/Python 3.11 | 595 passed, 167.12 seconds |
| Final complete Windows/Python 3.11 suite | **606 passed, 0 failed, 0 skipped**, 167.82 seconds |
| Focused Review workflow cases | 11 passed, 8.38 seconds |
| Syntax | 113 package/test files passed |
| Dependency and portability checks | Passed |
| Diff whitespace | Passed |
| Windows/Linux CI | Run and inspected on the PR; see its current verification results |

The full final suite emitted no unexpected warning summary. The added workflows include actual Textual clicks at 80×24, incomplete and complete Finish, no-op Save, explicit verification, blocked/accepted qualification, restart, compatible older-file reimport, fake photometry rejection, stale writes, physical-change invalidation and unrelated-field preservation.

Existing assertions were retained except where the requested semantics changed: Review no longer becomes complete merely because qualification exists; the concurrency test now races **actual edits**, since unchanged saves intentionally do not write; the human range-guard fixture explicitly supplies required verification/mapping declarations. None of these changes skips the checks or weakens the concurrent stale-writer/range assertions.

Reproduce on Python 3.11 from the checkout:

```powershell
$psycolabReviewTemp = Join-Path $env:TEMP ("PsyCoLab-review-" + [guid]::NewGuid())
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=$psycolabReviewTemp
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\portability_check.py
git diff --check main...feature/calibration-review-completion
```

Tests use isolated local configuration, fixture observations and Textual. Fresh hardware measurements and human acquisition were not performed. CI results are recorded on the review PR; passing automated tests do not certify actual hardware.

## Laboratory acceptance

1. On the intended display, save measured dimensions/binding, ruler observations, spatial/software timing diagnostics and actual luminance data. Confirm Review accurately distinguishes saved records from verification.
2. Finish with unverified photometry/no qualification. Confirm Experiment opens with the selected display and human preflight still blocks missing requirements; simulation/configuration remain available.
3. Review independent ruler/photometer/photodiode evidence under lab criteria; deliberately save the relevant declarations. Confirm fake/test methods cannot be verified or qualified.
4. Select the registered experiment name, inspect its requirements, and qualify only after laboratory protocol review. Check actual framebuffer/DPI, digital/physical contrast and timing on the intended hardware.
5. Restart, make a no-op Save, and confirm no revision is added. Change a physical setting and confirm old qualifications/evidence become invalid as appropriate. Keep original participant snapshots unchanged.

Review the PR and merge manually only after approval. No automatic merge is performed.
