# Ordered scientific redesign

Requested order: historical separation (2), scientific specifications (3), flexible
readability (6), presentation precision/timing (1), recovery validation (5), primary
analysis alignment (4). Physical qualification remains a measured hardware task.

## Git-history findings

- `9ad1304` already quantised the shared raster to uint8. The low-contrast issue
  predates the recent consistency changes; it was not a precision feature removed
  by those changes.
- `f9ff6fd` introduced durable partial scientific-action events. Retain that
  behaviour and its exception tests.
- `7472ee2` rejected late responses; `c6daec1` fixed probe layering/response
  attribution. Keep these corrections.
- The reference shader avoids early CPU quantisation, but `_reference_csf/libC.py`
  still requests an RGBA8 intermediate framebuffer. Its nominal historical 10-bit
  story is not evidence of measured end-to-end precision. Do not blindly restore it.
- The gamma/calibration acceptance history deliberately separates setup acceptance
  from measured physical verification. Preserve that distinction.

## Stage 2: historical separation

The reconstructed base/flanker/ellipse modules are archived under
`experiments/_internal/historical/`. Their old IDs still resolve for replay and
saved-data interpretation. Normal catalogue/UI listing excludes historical specs;
`include_historical=True` is explicit compatibility mode. Historical source/frozen
tests remain unchanged scientifically. New scientific protocols receive new IDs.


## Stage 3: scientific protocols

Normal experiments persist a versioned scientific specification: discrimination,
quantity/units, condition schedule, adaptive semantics, stopping, exclusions and
estimator. New line-position baseline/flanker protocols and separate ellipse
major-axis/centre protocols use degrees and the methods in thesis Chapter 4.
Unspecified probe vertical separation, observer-specific flanker frequency and
ring digital increment are required study inputs, not inherited pixel defaults.
Line-position estimates use geometric means of retained presented reversals;
CSF/ellipse estimates use medians. Optical contrast remains unqualified.

## Stage 6: appropriate consistency

The exact-main-loop syntax-equality test is removed. Fixed-trial tasks may use a
for loop and omit a meaningless adaptive update. Common names, readable sections,
presentation-only trial builders and explicit scientific response meanings stay.

## Stage 1: presentation and contrast precision

The scientific raster stays floating point through a float32 OpenGL texture.
The explicit uint8 raster is retained for teaching stimuli and exported PNG
previews. Requested CSF strengths .001 and .0001 now differ before display
encoding; the PNG preview still cannot represent that difference. Missing
ARB_texture_float support is an error, never an automatic 8-bit fallback.

This removes one known loss of precision. It does **not** establish framebuffer,
operating-system LUT, GPU output or panel precision. The older shader's RGBA8
intermediate texture is not an appropriate measured reference. New protocols
remain blocked for human acquisition. A monotonic measured luminance-transfer
utility refuses extrapolation and clipping; it is not silently applied to digital
stimuli or treated as an optical contrast calibration.

Timed visual stages now count refresh frames at the selected profile rate and
record requested/quantised durations, every software flip, delayed intervals and
the next visual flip. Transition intervals are included. A function-return time
is not the physical stimulus offset. Instruction labels and rasters are prepared
before the timed loop. Software flip records do not measure photons or audio
onset. Audio cues remain software-triggered and need physical measurement.

Hardware acceptance still requires measured luminance linearisation, effective
low-contrast precision across the intended stimulus range, actual monitor refresh
and photon timing (including fixation, stimulus, ISI and audio conditions). Failure
to distinguish requested contrasts, clipping, timing failures and missing evidence
must remain explicit. Do not lift acquisition blocks merely because tests pass.

Primary references: [OpenGL floating textures](https://registry.khronos.org/OpenGL/extensions/ARB/ARB_texture_float.txt),
[PsychoPy luminance correction](https://devdocs.psychopy.org/general/gamma.html),
[PsychoPy frame diagnostics](https://psychopy.org/general/timing/detectingFrameDrops.html).

## Stage 5: recovery diagnostics

New detection protocols use a stimulus-dependent logistic observer with declared
chance, lapse, slope, threshold and threshold probability. Constant-accuracy
observers remain pipeline smoke tests. Saved metadata distinguishes the two.
Conditions and observer outcomes use separate seeded random streams. Human
procedures receive fresh saved seeds; historical replay retains its original seed
and random-number conventions.

`python -m simulations.recovery` runs repeated known-threshold diagnostics using
the acquisition contrast update, shared staircase engine and primary estimator.
The operating-point calculation supports fixed n-down/one-up steps only. Arbitrary
TUI n-up/down values are still collected and executed, but this benchmark does not
claim their threshold interpretation is validated.

The benchmark reports successes, boundary exits, incomplete runs, conditional
bias and repeated-estimate spread. It starts at the known threshold, a favourable
diagnostic assumption. Its spread is not a human confidence interval. Results in
`docs/audit_evidence/scientific_recovery.json` include severe boundary censoring
at high strengths/lapses. Bias among successful runs is not evidence that censored
runs recovered a threshold. These are limits to study before choosing acquisition
parameters, not a reason to silently tune a participant's TUI settings.

## Stage 4: declared primary analysis

Each scientific experiment declares presented (pre-update) reversal strengths,
retained count from TUI, within-staircase statistic and arithmetic averaging across
independent repeats. CSF/ellipse use a median; line-position uses a geometric mean.
A condition receives an official result only when all its configured repeats are
complete with enough reversals. Completed conditions may survive a global safety
ceiling, but incomplete conditions receive no threshold. Error/aborted runs receive
no primary threshold. Canonical condition/staircase ownership is validated.

Acquisition writes `primary_thresholds.json`; post-hoc default analysis recomputes
the same result from `trials.tsv`. Alternative retention/column conventions require
explicit exploratory mode and are labelled accordingly. The TUI's editable derived
figure page requests exploratory mode. Raw records are never edited by analysis.

## Researcher-facing contract and exceptions

Open one public experiment and its stimulus class. The experiment declares task,
conditions/order, stimulus parameters, interval sequence, response scoring,
adaptation, stopping and primary estimator. The stimulus class declares image
formation, units, layer order and gamut. TUI controls remain authoritative for
study settings, including n-up/down, step sizes and reversal counts.

Scientific decisions outside those two files have narrow justifications:

| Shared location | Reason and researcher-facing declaration |
| --- | --- |
| `adaptive/staircase.py` | Tested counter/reversal state machine; each experiment selects its rule, controls and explicit contrast update. Historical rules use a separate adapter. |
| `analysis/primary.py` | One implementation prevents online/offline estimator drift; the complete estimator specification remains in the experiment's finish function and saved result. |
| `core/presentation.py` | Hardware encoding, frame accounting and input boundary need one auditable implementation; scientific timing/placement remains in each trial builder. |
| `stimuli/geometry.py`, spatial calibration | Shared unit conversion; physical monitor evidence is saved per run. |
| `simulations/psychometric.py` | Explicit validation model, saved with parameters; not a hidden acquisition decision. |

Old IDs `base_flanker`, `indirect_flanker`, `ellipse_2d` and `contrast_sensitivity`
retain historical meaning. The public `contrast_sensitivity.py` implements the
modern spatial CSF with saved ID `csf_thesis`; reusing the older ID would silently
change the meaning of existing data. Its source filename is universal. Explicit
historical catalog mode is available to replay and test old protocols.

No participant data or calibration evidence was removed. The archived source and
frozen full-trace tests retain historical interpretation. Earlier durable-event,
late-response and layering fixes remain in place. The managed custom probe still
requires its ordinary Draft/Test/Ready retest after source changes; it was not
silently republished.


## Verification record

- Full regression run: **1,010 passed**, with four warnings reporting the managed
  custom probe's existing readiness gate. No frozen fixture was changed.
- After the final result-status and readability refinements: **81 focused checks
  passed**, including 23 scientific-redesign cases. These cover all new protocols,
  normal and explicit historical setup, threshold estimator agreement, incomplete
  runs, finalisation failure, raster precision, frame accounting and recovery.
- Lifecycle/action preservation was additionally checked with **61 passing tests**.
  These focused counts overlap with the full suite; they are not additive totals.
- Patch whitespace checks pass. Changes remain uncommitted on
  `refactor/scientific-protocol-redesign`; no remote branch was updated.

The standalone `python -m simulations` CLI and `simulate()` default retain the old
CSF model as compatibility entry points. Their legacy tuning/condition flags must
not be interpreted as the modern spatial CSF. Use the normal TUI or explicit
`simulate(experiment_id="csf_thesis", ...)` for the current protocol. This retention
avoids silently changing established scripts; normal TUI catalogs exclude it.

No hardware or researcher-comprehension validation is claimed by these checks.
The full default modern CSF simulation (seed 123, two frequencies, four independent staircases per frequency) also completed: 488 responses, all eight staircases complete, two primary condition results. This is an additional pipeline check, not a recovery or hardware qualification.
