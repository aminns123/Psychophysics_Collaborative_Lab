# PsyCoLab architecture baseline — 26 October 2026

Software implementation and focused regression evidence, prepared for the
27 October Windows laboratory checks. This is not a release, merge approval,
hardware qualification or retrospective approval of participant observations.

## Checkout and exact revisions

- Verified live checkout: `C:\Users\AlexanderMinns\Physics\PhD\GitHub\Psychophysics_Collaborative_Lab`.
  Its origin is the requested `aminns123/Psychophysics_Collaborative_Lab` repository.
  It was clean on `main`; no live source edits were made.
- Isolated implementation checkout:
  `C:\Users\AlexanderMinns\.codex\.chatgpt-projects\g-p-6ac9f587c3948191a038a071aaa95b01\architecture-repair-20261026`.
  The project mirror's `sources/` was not changed.
- Baseline, independently checked with remote `ls-remote`:
  `02b02a34daeb7964049e39d3fb1ebf96474812d1`.
- Final implementation commit:
  `b0a292beee1461bfcb0f0ecd3b8c1b49d0ad1c69`.
  Subsequent report-only commits record test/CI evidence; the PR head identifies
  the exact delivered documentation revision.
- Historical `v0.3.0` remote ref: `60588ddff67bd2a892da1dc1daa70eab1c0ee474`.
  The tag was not moved, replaced or republished.

## What already worked and was retained

All nine official experiments already connected the shared contrast strategy
interface. `RunContext`, trial timelines, canonical response recording, external
data directories, parameter snapshots, manifests and source inventories already
provided one acquisition pipeline. CSF and probe constant schedules already
separated scientific conditions from independent adaptive staircase replicas,
used seeded binary target balancing, and reported descriptive accuracy.

The CSF Gaussian-plus-cosine-tail equation, probe overlap/headroom checks,
viewport intersection, calibration gates and historical adaptive arithmetic
were retained. Experiment files continue to own scientific conditions, stimulus
mapping, interval structure, correct alternatives and analysis declarations.
The original fixed teaching procedures remain the default explicit `original`
option where previously provided.

## Confirmed defects and their repairs

1. **Gabor declaration ownership.** `sine_grating` declared two unused envelope
   fields while `gabor_patch` omitted fields its validator required. Move the
   declarations to Gabor and restore the original five-field sinusoidal contract.
   Old Gabor JSON fills only the two explicitly declared legacy defaults. Flat
   and fading square apertures remain opt-in; legacy Gaussian remains default.
   Review help marks inactive sigma and explains the hard-edge sampling limit.
2. **Orientation safety ceiling.** The actual orientation initializer still
   used `trial_count` for the adaptive session ceiling after PR #145 repaired a
   different teaching initializer. Use configured `max_trials` there, retain
   finite `trial_count` stopping and original multiplication updates, and reject
   an unreachable response goal before execution.
   Correct the introductory comment: the numeric underflow guard is not a .001
   scientific contrast floor.
3. **Authoring fixture coupling.** An unfinished starter copied the newly
   extended example JSON despite declaring no method fields. Give the test-only
   starter its own complete settings; unknown production keys remain errors.
4. **Finite teaching lifecycle.** New optional teaching adaptations saved a
   running adaptive session after completing their scientific response count.
   Add an optional engine `response_goal`; unchanged reversal-based engines omit
   it. The canonical validator requires agreement with configured `trial_count`,
   resolved goal, lifecycle and accepted count, and disallows a fabricated
   threshold. Staircase reversal completion remains truthful and separate.
5. **Preset versus active ceiling.** Preserving a reference JSON with
   `max_trials=1000` is legitimate when the active run selects 4. The validator
   previously treated both as active. Validate source-preset provenance and
   distinguish only its two precise source-value locations; all active ceilings
   must still agree. Tamper tests reject both active-state mismatch and invalid
   preset provenance. Final method summaries now retain the initial source
   preset, rather than discarding it when saving observed accuracy.
6. **Older complete working JSON.** Only fields explicitly declared with
   `allow_legacy_default` may be omitted. Original omissions and misspellings
   still fail; default filling uses declared historic defaults, not an edited
   current preset. An unchanged reference JSON keeps its actual source identity.
7. **Shared method readiness.** Extension fingerprints omitted `methods/`.
   They now include its scientific source; dependency contract version 3 returns
   affected studies to Draft and requires a fresh Test/Ready cycle. Source is
   never copied into or rewritten inside the laboratory folder.
8. **Configuration/Review contract.** Retain immediate field bounds and errors;
   derived probe intensity/step explanations remain in Review. Update the
   obsolete assertion about their location. Remove two unreachable legacy
   helpers and the unreachable selector handler, with background-selection,
   navigation and broader TUI regression coverage.
9. **Checkbox clarity.** Preserve Textual keyboard/mouse behavior while adding
   literal `[ ] Not selected` / `[X] Selected — not yet saved` text. Review's
   response guidance explicitly applies to the current run. Persisted
   calibration evidence and saved feedback remain separate from selection.

The structural tests already accepted delegated method callbacks on this
baseline. No duplicate `update_experiment()` functions were restored.

## Review order

1. [PR #146](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/146),
   `c5f23033435fc8dc2c98b9ed0f8392324f8db456`: confirmed Gabor/orientation/fixture repairs.
2. [PR #147](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/147),
   `76f8fa465e37442e54b8645752f822871bbb62b1`: finite teaching lifecycle, explicit
   JSON compatibility, shared-method fingerprints and local example; based on #146.
3. [PR #148](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/148),
   on `fix/readiness-ui-baseline-20261026`: source-preset
   preservation/validation, checkbox states, dead UI cleanup and full support
   matrix. Review the combined head before accepting the stack. No automatic merge.

## Actual architecture and readability audit

`stimulus_library.py` owns self-contained stimulus declarations and rendering
equations. `methods/contrast.py` owns strategy selection, fixed schedule/progress,
accuracy bookkeeping and one shared trial loop. `methods/probe.py` owns reusable
increment scheduling/record projection; `methods/teaching.py` owns short teaching
policies. The existing adaptive package owns streaks, steps and reversals.

Experiments retain condition creation, target geometry, strength-to-command
equations, timelines, response meaning and estimator choices. The remaining
similar-looking CSF/probe callbacks express different scientific schedules,
headroom and estimators; no further extraction was justified for this repair.
Explicit method imports preserve readability without a new runner or registry.

Configuration groups declared fields generically; Review resolves the selected
method and stimulus, units, scientific help, source navigation, trial-controlled
values, geometry/clipping and presentation count. Fixed schedules are summarized
there; complete schedules, seed and observed accuracy remain in resolved metadata.
Sampling failures remain recoverable preflight feedback. Carrier Nyquist checks
do not qualify the extra spatial frequencies introduced by a hard aperture.

Both methods retain schema-v1 **20-column `trials.tsv`**, experiment/run identity
and sequential trial indices. Fixed trials leave staircase fields blank. Strength
is CSF digital peak-to-peak modulation, probe increment above local background,
Gabor modulation, or the teaching line's declared increment/absolute command;
none establishes physical luminance contrast. Psychometric fitting is separate.

## Nine-experiment verification matrix

“Pass” below means automated Windows Configuration → Review → synthetic
execution → canonical saved-run validation, for both selected methods, using
small explicit scientific test conditions. It is not a physical presentation
or exhaustive stress qualification. The fixed matrix includes zero catch levels.

| Experiment | Original default | Adaptive | Constant | Configuration/Review | Simulation/data |
|---|---|---|---|---|---|
| `contrast_sensitivity` | Adaptive | Pass | Pass | Pass both | Pass both |
| `line_position_baseline` | Adaptive | Pass | Pass | Pass both | Pass both |
| `line_position_flanker` | Adaptive | Pass | Pass | Pass both | Pass both |
| `ellipse_centre` | Adaptive | Pass | Pass | Pass both | Pass both |
| `ellipse_major_axis` | Adaptive | Pass | Pass | Pass both | Pass both |
| `orientation_adaptive` | Original finite adaptive rule | Pass | Pass | Pass both | Pass both |
| `orientation_task` | Explicit `original` | Pass | Pass | Pass both | Pass both |
| `probe_above_below` | Explicit `original` | Pass | Pass | Pass both | Pass both |
| `example_experiment` | Explicit `original` | Pass | Pass | Pass both | Pass both |

The three explicit `original` paths also execute in the teaching regressions.
The full local [line-strength example](../examples/laboratory_extensions/experiments/demolab__line_strength.py)
passes both methods, Review and saved validation. Its two eccentricities are
scientific conditions; line intensity is `0.5 + increment`, with increment
bounded to [0, 0.5]. It imports installed stimulus/method/timeline APIs and no
engine implementation. Binary target scheduling is not a claim of support for
arbitrary future multi-alternative response designs.

## Executed evidence

- Remote main workflow
  [40343136366](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40343136366)
  completed red on both platforms. Windows: **12 failed, 1691 passed, 1 skipped**.
  Inspected PR #143/#144/#145 completed jobs confirm 6/11/5 failures respectively;
  these overlap and are not independent defect counts.
- Initial focused local reproduction: **9 failed, 67 passed**.
- Minimal repair regression set: **98 passed**. New carrier/ceiling checks:
  **40 passed**. These overlap; do not add their counts.
- Methods, explicit compatibility, extension and staircase checks:
  **103 passed, 1 platform skip**.
- Checkbox/calibration/override/probe UI set: **73 passed**. The emitted crash
  report in an intentional failure-recovery test is expected test evidence.
- Final matrix plus finite-goal checks: **23 passed**, including all 18 official
  method combinations. Independent preset preservation/corruption checks:
  **2 passed**.
- Portability check passed; `pip check` found no broken requirements.
- Direct comparison with pre-aperture commit
  `f78e83a5f25445bc887f2547a5ae59b072cd03d8`: both Gabor classes, sinusoidal
  grating and CSF each preserve all **49,152 floating and encoded default raster
  pixels** on a 256×192 angular grid. Carrier/phase/orientation opt-in tests and
  independent viewport crop tests supplement this identity check.
- AST comparison confirms **50 scientific function bodies** across the nine
  experiments are unchanged against that same pre-aperture revision. This is
  source evidence, not a substitute for full historical run-byte fixtures.
- Final scientific help/comment corrections: **18 passed** (Gabor and generic
  Review). These text-only amendments followed the start of the full-suite run;
  executable equations, stopping logic and recording code were unchanged.
- Full local Windows suite: **1,755 passed, 1 skipped, 4 warnings, zero failures**
  in **990.86 seconds (16:30)**. The skip is the POSIX-only symlink case;
  warnings concern the isolated missing authored source. Local log and JUnit:
  `../architecture-full.log`, `../architecture-full-results.xml` in the working
  project (not participant data and not committed to Git).
- Final PR #148 hosted Windows/Ubuntu CI is **pending** at delivery; do not infer
  a hosted pass from the local result. Inspected earlier #146/#147 CI still
  fails only the obsolete Configuration-versus-Review assertion corrected in
  #148. The inspected #147 Windows run had 1 failure / 1,732 passes / 1 skip.
  Review the combined head before accepting the stack.

Environment actually used: Windows x64, Python 3.11.15 (conda-forge build),
NumPy 1.26.4, pyglet 1.5.27, Textual 1.0.0, matplotlib 3.11.2, pytest 8.4.2,
pip 26.2.1, setuptools 84.0.0, wheel 0.48.0; package metadata 0.3.0. Tests used
the existing environment without reinstalling it; pytest selected the isolated
checkout source. Tests isolate local configuration and create synthetic data
inside this project workspace. No real calibration or participant records changed.

## Remaining uncertainty and 27 October manual Windows checklist

- [ ] Review/approve the final PR stack and inspect final Windows/Ubuntu CI.
- [ ] At native terminal sizes 80×24 and 160×55, configure all nine studies;
  switch adaptive → constant → adaptive, Back/Review/Edit, presets, source-file
  navigation, response guidance, Try and simulation. Verify invalid settings can
  be corrected without losing another experiment's draft.
- [ ] Load an old Gabor JSON, confirm unchanged legacy appearance, then compare
  explicit 1° square hard aperture and degree-based fade at the monitor edges.
  Check phase/orientation/frequency, full/partial visibility and invisible-target
  rejection. Hard edges add high spatial frequencies; qualify their actual sampling.
- [ ] Check CSF sigma, support diameter, taper start, raster and clipping in Review;
  do not substitute a hard aperture for its historic smooth envelope.
- [ ] Click and use Space/Enter on calibration/qualification, trust, readiness,
  override and response-guidance controls. Check cancel, failed save, saved/reopen
  and profile/evidence identity. Checking alone is not physical verification.
- [ ] Copy the local example to a separate configured laboratory folder, Test and
  Ready both methods, then update a copied shared method and confirm Draft/retest
  behavior. Preserve existing local source, presets and external root pointers.
- [ ] On disposable synthetic runs, repeat seeds, abort/retry and exercise recovery;
  validate retained runs and exports. Compare all available historical adaptive
  fixtures; broad all-study historical byte equivalence is not claimed here.
- [ ] Independently qualify geometry, display binding, actual photometry/output
  depth, photon timing, input and audio for the apparatus/protocol being claimed.

The missing `new_probe_vertical_line_stimulus.py` authoring warning remains
isolated and visible; no evidence establishes it as the collaborator's native
crash cause. Do not delete history or restore/approve unknown source to silence it.
The earlier native 0xC000041D and historical large-terminal layout report remain
unresolved pending reproduction. Automated checks are not native hardware evidence.

## Release recommendation

Preserve `v0.3.0`. Recommend **v0.4.0rc1** as a future *software* candidate because
this baseline adds opt-in method APIs and aperture controls. Do not change the
source version or create the tag until owner approval and the software gates pass.

The existing launcher already checks isolated editable source/package identity
and diagnoses/reinstalls mismatched metadata; that part of Issue #82's stage 2
is implemented, despite stale roadmap wording. It validates Python 3.11 and
preserves incompatible environments. Remaining gates are an approved exact x64
Python distribution/patch and runtime/transitive/bootstrap/build/dev constraints
with artifact identities, two reproducible clean installations through the real
batch launcher, failure/recovery diagnostics, and a copied-fixture update/rollback
rehearsal that preserves external roots and newer observations. Current loose
dependency ranges and successful `pip check` are not reproducibility evidence.

Owner/institution licensing and third-party attribution decisions remain open;
no root software licence was found and none was invented. Documentation and
release notes must specify software compatibility, downgrade limits and the
physical qualification scope explicitly. Keep Issues #82, #125–#128, #136 and
#139–#142 open while their CI/native/physical acceptance remains outstanding.
