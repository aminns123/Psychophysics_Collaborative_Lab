# Scientific stress audit — 27 October 2026

## Decision and scope

**Recommendation: Ready for manual laboratory acceptance testing after this PR's
final Windows and Ubuntu checks pass and the maintainer accepts the repairs.**
This is not a software release candidate sign-off or physical apparatus
qualification. The merged intake `main` is red; do not treat its failing checks
as an accepted baseline. No PR was merged and no release or tag was created.

The audit tested software behavior using synthetic responses and scripted
researcher actions. It did not collect human observations, measure optical
contrast or photon timing, alter real calibration, or establish participant-level
equivalence. Real participant archives and local calibration directories were
not used as test fixtures.

## Exact source and environment

- Authoritative Windows checkout inspected first: maintainer's existing
  `Physics/PhD/GitHub/Psychophysics_Collaborative_Lab`; clean `main` at
  **`c81b1db74d995c867c0b846e9aced35dfaafadcc`**, equal to fetched `origin/main`.
  No open PR was returned at intake. Both registered CSF experiments were present.
- Repairs and tests used separate Windows worktrees of that same repository;
  the authoritative checkout was not reset, edited or reinstalled. This was not
  substituted with a cloud execution environment.
- Review repair commit: `4d4d4424204672d0bb6af432aa5e1004f73486c5`.
- Scientific stress tests and stale-contract corrections:
  `dbbd9e113140ce3f99c3ed0ac8259ec593fee5a5`.
- Sidebar draft/guidance repair: `088a3ca4e90a7ef74f925947308d3f050c667ea5`.
  Scientific help metadata: `6c1557034bc71595b917a3bdfb412cb6bdf6696b`.
  Explicit defaults adoption: `266af367f94a9f3d74386d213267251dc41e9f31`.
  The PR head identifies the complete integration
  target; GitHub check evidence must be tied to that exact head, not just an
  earlier code commit.
- Windows AMD64, Python 3.11.15, existing laboratory virtual environment.
  Each pytest case redirects `PSYCOLAB_CONFIG_DIR` to a disposable directory.
  Synthetic runs use disposable data roots outside the Git worktrees and the
  normal canonical recorder. Native entry-point checks also used isolated
  configuration, with no participant acquisition.
- Existing `v0.3.0` tag was observed unchanged at
  `60588ddff67bd2a892da1dc1daa70eab1c0ee474`.

## Commands and observed outcomes

Commands below ran from the corresponding Windows worktree with that existing
Python interpreter. Paths shown are relative, reproducible evidence destinations;
they are not proposed changes to the laboratory's data layout.

| Check | Command / evidence | Outcome |
|---|---|---|
| Frozen intake main | `python -m pytest -q --basetemp=../stress-main-baseline-temp --junitxml=../stress-main-baseline.xml` | **1,769 passed, 4 failed, 1 skipped**, 4 warnings; 1,021.30 s |
| Intake GitHub CI | [main workflow 40410787522](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40410787522) | Windows and Ubuntu red; Windows log matches the same four failures |
| Review/source/navigation before sidebar repair | Review authority, file navigation, fullscreen and extension selection | 26 passed; two small-screen mouse-driver assertions required waiting for scheduled scrolling, not a production timing change |
| Corrected Review + scientific contracts | `python -m pytest -q tests/test_review_parameter_authority.py tests/test_experiment_reading_pattern.py tests/test_csf_windowed_variant.py` | **45 passed**, 1 warning; 55.03 s |
| Independent stress before four extra boundary/catalogue assertions | `python -m pytest -q tests/test_independent_scientific_stress.py tests/test_experiment_reading_pattern.py tests/test_csf_windowed_variant.py` | **131 stress cases passed**; combined run had 167 passes and one stale alias-instrumentation failure, subsequently corrected |
| Post-Review full suite at `dbbd9e1` | `python -m pytest -q --basetemp=../stress-final-full-temp --junitxml=../stress-final-full.xml` | **1,917 passed, 1 skipped**, 4 warnings; 1,253.24 s. Subsequent navigation/default-adoption repairs are covered by targeted checks and final-head full GitHub CI. |
| Final sidebar/guidance + geometry/fullscreen regression | `python -m pytest -q tests/test_review_parameter_authority.py tests/test_console_geometry.py tests/test_review_fullscreen_and_source_jump.py` | **22 passed**, 1 warning; 102.08 s |
| Portability | `python scripts/portability_check.py` | Passed; no tracked local environment/cache or hard-coded home paths |
| Scientific field-help regression | Review authority + official method baseline + reading-pattern contracts | **58 passed**, 1 warning; 149.91 s |
| Defaults/Review/refresh regression | Review authority + file navigation + expanded table + F5 tests | **41 passed**, 1 warning; 114.78 s; final default-selector refinement separately **2 passed** |
| First complete candidate `b37b0c9`, GitHub run 40419988881 | Full Windows/Ubuntu suites | Ubuntu: **1,921 passed, 3 skipped**, portability passed. Windows: **1,922 passed, 1 failed, 1 skipped**; the 60-column geometry test observed a zero-width table. The immediate local rerun passed all four sizes, consistent with sampling before initial layout. The test now waits boundedly for real bounds before retaining every original geometry/data assertion; no production layout or science was changed for this correction. Final-head CI is required again. |
| Same-process TUI walkthrough | Actual Textual application at 120×40, all ten experiments, adaptive → constant stimuli → adaptive | **30 configuration/Review transitions passed**; JSON summary retained locally |
| Actual Windows entry point | `python -m psychophysics_lab`, direct keyboard input at 80 columns | Setup → circular CSF → Configure → Review → expanded table → Edit; native navigation defect reproduced, documented below |

The full suite includes the newly added Gaussian oracle, full-registry coverage,
strict constraint cases, external extension test, existing viewport/sampling,
calibration, source refresh, data, override, presentation-mode and isolation
regressions. The final GitHub Windows/Ubuntu jobs independently rerun the complete
suite and portability check on the final PR target. The PR's evidence comment
records their head SHA, run URL and completed results; pending CI is not green CI.

Exploratory failures were kept distinct from implementation defects: an initial
stress fixture deliberately hit an undersized 12-trial ceiling for a 32-trial
ellipse schedule; valid cases now select a sufficient ceiling and separate tests
retain deliberate rejection. A standalone TUI harness initially read a table
before mount completion; it was rerun with the existing mount-aware driver.
Neither result justified weakening acquisition validation.

## Complete experiment-by-method coverage

Every cell below uses three seeds (`0`, `19`, `9007199254740993`), the real
prepare/trial/response/method/recorder pipeline and the independent canonical
validator. Scientific studies also vary background between 0.2, 0.5 and 0.9;
teaching tasks retain their declared 0.5 background. Numeric equality is not
used to infer that different scientific quantities mean the same thing.

| Official experiment | Controlled quantity | Adaptive | Constant stimuli | Historical/default teaching path |
|---|---|---|---|---|
| `contrast_sensitivity` | Digital peak-to-peak grating modulation | 3 | 3 | Not offered |
| `contrast_sensitivity_windowed` | Same modulation, separate circular envelope | 3 | 3 | Not offered |
| `line_position_baseline` | Probe increment above selected background | 3 | 3 | Not offered |
| `line_position_flanker` | Probe increment with declared local flanker scene | 3 | 3 | Not offered |
| `ellipse_centre` | Probe increment in two-interval scene | 3 | 3 | Not offered |
| `ellipse_major_axis` | Probe increment with ring/position conditions | 3 | 3 | Not offered |
| `orientation_adaptive` | Declared teaching Gabor strength | 3 | 3 | Already adaptive |
| `orientation_task` | Declared teaching Gabor strength | 3 | 3 | 3 original-path runs |
| `probe_above_below` | Teaching line command relative to actual background | 3 | 3 | 3 original-path runs |
| `example_experiment` | Teaching line command relative to actual background | 3 | 3 | 3 original-path runs |

These are 69 matrix runs, plus 20 exact same-seed replay comparisons (two runs
each), two actual Gaussian/circular sequence comparisons, interruption/recovery,
tampering and repeated-run cases. Scientific conditions include two frequencies,
two positions, two aspect ratios and ellipse ring combinations where applicable.
Adaptive runs deliberately use short response ceilings; they do not establish
threshold convergence or perceptual validity. Fixed repetitions are per level
per scientific condition, not a global response count.

All tested fixed runs retained the canonical **20 columns**, actual declared
strength values and empty staircase identity/index/reversal cells. They produced
no invented adaptive threshold. Every completed matrix run passed the validator.
Same-seed canonical trial rows, including virtual timestamps, replayed exactly.
Run directories remained distinct. Large integer seeds retained their exact value
in provenance. Nonfinite starting strengths/backgrounds were rejected.

## Scientific grating inspection

The independent circular oracle starts from the **real Review planning and
`prepare_stimuli` output**, not an unrelated hand-built renderer dictionary.
For diameter 1°, fade 0.1°, frequency 2 cycles/degree, background 0.37 and selected
peak-to-peak modulation 0.2, sample points with the same carrier phase give:

| Radius | Envelope gain | Digital command at positive carrier peak |
|---|---|---|
| 0.125°, 0.3°, 0.4° | 1 | 0.47 |
| 0.45° | 0.5 | 0.42 |
| 0.5°, 0.6° | 0 exactly | 0.37 exactly |

The outer annulus is a raised cosine. Hard-edge/zero-fade behavior, invalid fade
greater than radius, background headroom and exact background outside the circle
remain independently checked. A hard edge introduces spatial frequencies beyond
the carrier; the existing carrier sampling check does not certify that edge's
full spectrum. Native display sampling and optical output remain acceptance work.

The Gaussian oracle uses the selected **sigma 0.5°, cutoff 3 sigma**, unchanged
digital modulation scaling and original Gaussian through radius 1°. The final
one-sigma raised-cosine multiplier is half at radius 1.25°, reaches zero at 1.5°,
and commands exact background beyond it. Raster extent is not Gaussian support.
The configurable stimulus class default sigma and the experiment's selected
sigma are explicitly distinguished in Review.

AST comparisons against pre-circular main
`c57b9d3ad424a9468d863b82a49bc14e749a9b9b` found the complete
`ContrastSensitivityGrating`, `GaborPatch` and `TeachingGabor` classes unchanged.
This PR does not modify `stimulus_library.py`, contrast/teaching/probe method
mathematics, adaptive engines, trial timelines, canonical recorder,
calibration implementations, default JSON or participant storage paths.
Scientific `help_text` was added for 30 previously unexplained field names in
their declarations, including shared teaching fields. An AST comparison after
removing only `ConfigField.help_text` verified those edits change no scientific
code, field defaults, choices or bounds. Every official experiment field now
supplies help text; custom extension fields use the author's own explanation.

Actual Gaussian and circular runs with equal settings/virtual responses produced
equal canonical trial, target, response and adaptation sequences for both methods.
Their experiment IDs/directories and envelope metadata remain distinct; circular
resolution contains no sigma attribution. Equal software sequences do not imply
equal human thresholds for different envelopes.

Existing viewport tests verify cropping to visible pixel centres without
rescaling the scientific aperture, bounded raster allocation, rejection of
wholly invisible required support and finite/positive geometry. They are part
of the full-suite evidence, not evidence of a measured laboratory display.

## Confirmed findings and repairs

| ID / severity | Reproduction and actual versus expected | Root cause / affected function | Repair |
|---|---|---|---|
| R1 / P1 | Circular aperture 1° with renderer default or preset width different: Review previously suggested editing Python for the resolved width. Expected one identified controlling experiment input. | Missing review control links; `settings_review.review_rows`, `review_files.targets_for_rows`, `ReviewScreen` | Explicit review-only slot/parameter → experiment-field links; derived status, real edit route, base/default/source details; no acquisition binding change |
| R2 / P1 | Review → Edit → alter frequency → sidebar Review. Previous Review returned with old values, including after entering `2,nan`. Expected current draft validation and preserved invalid input. | `LaboratoryNavigation.on_button_pressed` preferred an existing Review below the current configuration | Sidebar delegates to current Configure's normal Review validation; valid edits apply, invalid edits remain editable |
| R3 / P2 | Uncheck response guidance → edit a value → return to Review. Request silently reverted to true. | New `SetupRequest` used default flag in `ExperimentConfigScreen.on_button_pressed` | Retain the Review request's explicit guidance choice; regression checks false through both routes |
| R4 / P1 verification blocker, stale tests | Run intake suite: four failures listed below, although valid execution is supported. Expected tests to reflect declared shared behavior. | New variant not reflected by source-shape/callback fixtures; invalid fade normalized outside exception assertion | Correct contracts; retain strict validator, real trial callbacks and actual saved-run validation |
| R5 / P2 | After F5 retains an old defaults snapshot, reselecting its already-selected defaults option need not trigger a change event. Expected an explicit repeatable adoption action. | `StimulusParametersPanel` relied on a selection-change event; class defaults were also absent when default JSON existed | Add Adopt current class defaults, available for every stimulus; it replaces the selected base without changing experiment-controlled inputs |
| R6 / P2 test reliability | First candidate Windows CI sampled table width 0 at 60 columns; Ubuntu and immediate local four-size rerun passed. Expected geometry checks to observe a completed compositor layout. | `test_review_scrollbar_and_run_plan` treated mounted state as completed layout | Bounded wait for positive rendered table/frame/workspace bounds, followed by every original rail/value assertion; permanent collapse still fails |

The four stale intake tests are
`test_geometry_and_invalid_fade_are_defined_in_degrees`,
`test_every_researcher_file_has_the_same_actual_reading_order[contrast_sensitivity_windowed]`,
`test_scientific_interfaces_are_readable_without_identical_main_loops`, and
`test_actual_condition_stimulus_response_contract_for_every_experiment[contrast_sensitivity_windowed]`.
The replacement tests check imported CSF aliases, the distinct renderer,
required callback arguments with only optional keyword additions, declared
fields, and the shared module where the actual update callback is resolved.
No duplicate staircase loop or fictitious teaching field was added.

No P0 data corruption or scientific invariant violation was reproduced in this
audit. That is bounded evidence from these cases, not proof that none exists.
Remaining P2/P3 findings have exact examples in the companion
[First-Time Researcher Usability Report](FIRST_TIME_RESEARCHER_AUDIT_20261027.md).

## Failure, cleanup and independent validation

Four injected interruption modes stop after two accepted responses: explicit
abort, presentation setup exception, response key/alternative mismatch and
negative reaction time. They preserve that accepted prefix, mark aborted/error
status accurately, produce validator-consistent archives and permit a fresh run.
These are controlled software injections, not power-loss or fatal-driver tests.

Independent tamper cases change the accepted count, response alternative, schema
header or experiment metadata. Output hashes are deliberately recalculated after
the corruption; semantic validation still rejects each copy. This distinguishes
scientific/structural checking from a checksum-only test. Valid originals remain
unchanged. Eight repeated adaptive launches do not accumulate open matplotlib
figures. Process memory was not certified against a long-duration bound; no
claim of exhaustive native handle/VRAM leak testing is made.

## Laboratory extension

The audit creates a disposable external laboratory folder from the documented
shared-method example, then adds a real adjustable line-length field and a
review-only link to its actual `prepare_stimuli` renderer input. It imports
`LinePatch`, `TeachingAdaptiveMethod`, `ConstantContrastMethod`, the fixed
scheduler and `RunContext` integration from the package. It copies no engine or
recorder. This is source installed through the existing editable package/Python
environment; it is not a fresh independently built wheel acceptance test.

The extension is tested and explicitly marked software Ready in disposable
configuration. Universal Setup/Configure/Review exposes its parameter, Edit
focuses the local field and the effective length updates. Both methods execute,
save through the canonical recorder and validate. Changing the external source
invalidates Ready. Existing copied-framework tests also invalidate Ready when
shared contrast/probe/teaching dependencies change, without editing real sources.
Native external editor association/version-to-version installation remains
tracked by Issues #80, #82 and #142.

## Windows walkthrough and remaining release gates

The actual Windows command entry point opened at 80 columns. Keyboard selection
reached circular CSF, Configure, Review, expanded table and Edit. Shift-Tab could
reach the expanded controls; full-screen Review displayed status and routing
with horizontal scrolling reserved for the advanced source column. The invalid
frequency/sidebar behavior above was discovered here, not inferred from a unit
test. The entry-point sessions exited normally with Ctrl+Q.

The direct keyboard walkthrough and mount-aware Textual driver are separate
evidence. Desktop computer-use automation was not used on terminal applications
because that skill prohibits it. There was no completed physical fullscreen CSF
run: the isolated profile was an **UNBOUND DRAFT** and native preflight correctly
instructed detection/selection/saving of the actual display binding. No binding
or calibration evidence was fabricated to continue. After the sidebar repair,
the actual Windows keyboard route rejected `2,nan` and remained in Configure with
an explicit finite-frequency/range error. F5 also restarted successfully while
retaining the selected circular CSF settings and loading the new scientific help.
An en dash in that native error appeared as mojibake (`0.5â€“32`); this readability
finding is retained for the Windows diagnostics/interface follow-up in #140.
Full launcher installation,
independent workstation deployment, native crash `0xC000041D`, physical timing,
photometry and update/rollback qualification remain open in #123/#82.

### Practical manual laboratory acceptance checklist

- [ ] Maintainer reviews this PR's complete diff and final-head green Windows and
  Ubuntu checks, then makes the merge decision. Do not merge the red intake main
  simply because an earlier branch was green.
- [ ] On the intended Windows laboratory computer, record installed/source
  identity, start through the actual batch launcher, and verify the selected
  external data workspace and independent lab extension root.
- [ ] Bind the real monitor and verify geometry/distance/resolution. Do not reuse
  the audit's draft profile as a qualified display.
- [ ] In both CSFs, choose background, conditions and method; edit sigma/cutoff
  or circular diameter/fade through Review. Check actual effective geometry after
  return, JSON reload and F5. Confirm invalid settings retain the draft.
- [ ] In all ten experiments and the lab extension, switch adaptive/fixed/back;
  inspect condition counts, strength units, repetition meaning and response keys.
  Try known invalid input, cancel confirmations and ensure no run starts.
- [ ] Run bounded **Try the experiment** on qualified safe hardware, including
  Escape and retry; verify isolated test records. Inspect actual clipping,
  fixation, response guidance, timing/audio behavior and cleanup.
- [ ] Independently qualify optical transfer, output-depth claims and physical
  timing/input/audio where scientifically required. Software Ready and a
  researcher override do not establish measured calibration.
- [ ] Inspect a saved synthetic/test run in Data, its analysis, dictionary,
  canonical columns and source provenance; confirm fixed mode claims no
  staircase threshold. Preserve archives during any update/rollback rehearsal.
- [ ] Obtain collaborator-machine evidence for #123, complete deployment and
  rollback gates and licensing/ownership review under #82, then separately
  approve any release/version decision.
