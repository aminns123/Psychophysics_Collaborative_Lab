# Authoring-standard design-freeze acceptance

Proposal: [version 1](EXPERIMENT_AUTHORING_STANDARD.md), Issue #165 / PR #167.
Scientific baseline: current official main `a5aa56a`. **No official migration has
been performed or approved by this work.**

## Objective checklist

This table records the local design-freeze checkpoint. The exact final local
Windows result and hosted CI head/base are recorded on PR #167 after completion;
do not infer CI acceptance from an earlier head or from these focused tests.

| Criterion | Outcome | Evidence / limit |
|---|---|---|
| One settled narrative, ordinary Python, one file per experiment | PASS | A1 choices → A2 scientific methods → B integration; no new engine/DSL/condition manager |
| Everyday values, factors, alternatives/placement, events and measurements visible in A1 | PASS | Both executable candidates and source-edit exercise |
| Scoring, selection, updates, stopping and estimators inspectable before B | PASS | A2 placement checks; no reducer/count/target policy hidden in B |
| Condition versus target versus independent track clarified | PASS | Explicit CSF factor list, unchanged track order, fixed repetitions independent of track count |
| Gaussian scientific equivalence | PASS | Adaptive/fixed, opening on/off, teaching/psychometric observers, deterministic trial bytes, per-response state/history, reversals/results and ceiling case |
| Temporal protocol consistency | PASS | Paired signed-SOA schedule, both event orders, mapping, recorded counters/results and invalid cases; not a validated PSE/JND |
| Two-interval ellipse applicability | PASS | A/F measurement attachment preserves canonical bytes, event/action plans, adaptive histories and primary results; official source unchanged |
| Measurements, units, canonical schema and Read compatibility | PASS | Exact declared finite scalar keys, saved units, 20 columns, existing reader/validator and non-destructive derived export |
| Generic Review and selected-setting priority | PASS | Same edited `trial_events`; remapped response keys; retained existing ConfigField/preset semantics |
| Source-change invalidation and Test → Ready | PASS | Real external-source edits revoke readiness; new Test → Ready required; invalid source cannot be approved automatically |
| No official CSF import/hash pin or migration cycle in the reference | PASS | Import inspection and successful execution with old official callbacks deliberately disabled |
| All ten current official sources/contracts and shared scientific implementation protected | PASS | Frozen main source/field/response/stimulus/calibration hashes; unchanged Stage C evidence |
| Real software phase player, once-only opening and zero-response Escape | PASS | Established injected-display harness; not native UI/hardware evidence |
| Focused reference/standard selection | PASS | 66 tests before full qualification; commands below |
| Complete Windows regression / portability for final candidate | NOT VERIFIED in this pre-CI snapshot | Mandatory final outcome is reported on PR #167 for its exact head |
| Final hosted Windows CI for proposed integration | NOT VERIFIED in this pre-CI snapshot | Mandatory final outcome is the final PR check, including reviewed main base |
| Independent scientist understands and edits without framework help | NOT VERIFIED | No independent human exercise has been conducted |
| Native Windows TUI interaction by a first-time researcher | NOT VERIFIED | Console is not exposed to supported control; no headless result is substituted |
| Maintainer acceptance of this standard/reference and permission to migrate | NOT VERIFIED | This is the explicit sign-off request, not an approval inferred by the agent |
| Ten official migrated implementations / final repository-wide migration report | NOT VERIFIED | Intentionally deferred until approval and five independently reviewed waves |

Focused command:

```powershell
python -m pytest tests/test_authoring_standard.py tests/test_scientist_first_examples.py -q
```

On the isolated Windows 11 / CPython 3.11.15 exact-profile environment, the first
complete final selection passed **66 tests in 79.82 seconds**. A source-edit
stress check first reproduced five invalid-factor cases that incorrectly passed
validation; the candidate now validates the authoritative factor function and
all five are rejected. No official source or mathematical method changed. The existing
all-ten frozen scientific matrix, source/contracts, legacy extensions, readers,
Review and installation regressions remain in the full Windows suite. No
dependency or installation change is part of this PR.

## Independent scientist exercise (human gate)

Use a new disposable extension root and synthetic records. Give the scientist
the [short guide](../examples/scientist_first/README.md), reference source and
corresponding stimulus class, with no framework source navigation requirement.
Record actual commands, errors, assistance and the scientist's explanations.

| Task | Pass evidence to record | Current human outcome |
|---|---|---|
| Explain condition/target/track | Distinguishes frequency, side and independent repetition, then predicts fixed trial count correctly | NOT VERIFIED |
| Change factor levels | Adds a frequency in A1, identifies effective override/default, predicts and checks schedule/data | NOT VERIFIED |
| Change alternatives/placement | Creates a uniquely identified spatial variant; names/keys/coordinates and scoring agree | NOT VERIFIED |
| Change chronology/timing | Edits readiness or timed trial event; predicts before/after consequences and checks Review | NOT VERIFIED |
| Add a measurement with units | Edits `MEASUREMENT_UNITS` and `trial_measurements`, finds the exact saved values without writing serialization code | NOT VERIFIED |
| Explain/update stopping/results | Distinguishes reversal completion from a safety ceiling and identifies the declared estimator; deliberately validates a changed goal | NOT VERIFIED |
| Restart, Test → Ready, execute and recover | Source edit invalidates Ready; retest succeeds; cancellation/invalid input is understandable | NOT VERIFIED |
| Find/read results | Opens current and older saved synthetic records, explains automatic versus added data, exports a separate table safely | NOT VERIFIED |

Software tests actually edit a disposable CSF source to add a frequency, change
left/right to above/below, change grating duration and add a labelled measurement,
then run Test → Ready and inspect real saved synthetic outputs. This demonstrates
capability of the code boundary; it is **not** a novice comprehension benchmark.

A human pass requires a scientifically correct explanation and correct saved
behaviour without maintainer changes to core/TUI or unexplained framework
assistance. Record completion time and every assistance point; do not invent a
universal speed threshold or call an AI walkthrough an independent acceptance.
If a task fails, record the smallest reproduced obstacle and its scientific
effect. Do not automatically reopen the architecture or rewrite all experiments.

## Sign-off requested

Approve or reject these concrete decisions:

1. A1/A2/B is the version-1 authoring standard for the planned migration, with
   scientific choices/methods visible and B restricted to existing integration.
2. The refined, independent Gaussian example is the executable reference for
   that standard; the temporal example and ellipse assessment establish the
   intended breadth without claiming additional scientific qualification.
3. Preserve the canonical 20 columns and old journal keys; custom measurements
   use the existing boundary and explicit saved units.
4. Approve the [five-wave plan](EXPERIMENT_MIGRATION_PLAN.md), requiring a fresh
   baseline and separate review/merge decision for every wave. No blanket merge
   or automatic next-wave implementation is granted by a prior green result.

The recommendation is **approve version 1 as the design freeze after the final
Windows checks and maintainer review**. Independent usability remains an honest
Stage 4 gate. It does not require another architectural generation. This PR
itself does not replace any official source; wait for explicit approval before
implementing the first migration wave.

Native console automation is not claimed. The available control surface does
not expose the console and does not support terminal-app automation. This is
an acceptance-tool limitation, not a reproduced PsyCoLab defect. A human may
still perform the separate exercise.

Software validation does not certify display luminance/contrast, photon timing,
geometry, acoustic onset, input latency or an experimental protocol. Existing
calibration/provenance safeguards remain intact. Laboratory-specific physical
qualification and Stage 5 rollback remain separate from this design decision.
