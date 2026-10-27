# Event-first researcher interface: architecture and Stage A

**Stage B:** Gaussian CSF and Ellipse Major Axis now use the six-section
Python-first narrative, `trial_events()` and the approved SPACE/1,000 ms opening.
See the [before/after comparison and equivalence report](STAGE_B_EVENT_FIRST.md).
The Stage A evidence below remains a record of its original revision.

Inventory and API decision, 27 October 2026. Starting checkout:
`C:/Users/AlexanderMinns/Physics/PhD/GitHub/Psychophysics_Collaborative_Lab`,
clean `main`, HEAD/origin/main `2374f535ed4ff96bc39e5d09044184dae02cbbf8`,
origin `https://github.com/aminns123/Psychophysics_Collaborative_Lab.git`.
Implementation uses the explicitly named `event-first-stage-a-20261027` worktree
and `feat/session-events-stage-a-20261027` branch. No acquisition environment is
reinstalled. Real participant data, extension sources and calibration are not edited.

## Inventory before implementation

The active official registry contains ten experiments: contrast_sensitivity,
contrast_sensitivity_windowed, ellipse_centre, ellipse_major_axis,
line_position_baseline, line_position_flanker, orientation_adaptive,
orientation_task, probe_above_below and example_experiment. All expose a public
procedure and use the same RunContext/canonical recorder. Historical definitions
are excluded from automatic migration; external registrations retain their
existing trust/Ready checks. No open PRs were returned at intake; #151 and #152
have been merged. Read the dated accepted-software baseline together with the
more recent scientific stress and Review-authority reports; they are software
evidence, not apparatus qualification.

| Existing owner | Responsibility retained |
| --- | --- |
| core/timeline.py | Phase declarations, validation, resolution and serialization |
| core/trial_execution.py | One ordered traversal for human and virtual backends |
| core/presentation.py | Pre-rendering, key/hold filtering, Escape, software timing, cleanup |
| researcher.RunContext | Run lifecycle, accepted responses and canonical recording |
| methods/contrast.py | Shared adaptive/fixed trial loop; scientific strategies unchanged |
| core/runner.py | Preflight, external workspace, manifests, hashes, recovery/finalization |
| ui/settings_review.py | Execution-free description using actual experiment planning code |

The original PhD checkout was read, never imported/executed:
`C:/Users/AlexanderMinns/Physics/PhD/GitHub/psychophysics_experiments_git`,
clean HEAD `da377eb784197aff7207428fdb57789c037b1272`. Its
`Experiments/Contrast_sensitivity_function/contrast_sensitivity_function_exp.py`
(opening queue at lines 765–774) and
`Experiments/Flanker_Experiment/Ellipse2D_experiment.py` (opening queue at
981–982, interval events at 1027 onward) support chronological composition.
Their monolithic helpers, positional bundles and file-mediated state are not
copied. Current Gaussian CSF is the first planned migration; ellipse_major_axis
is the representative two-interval case. The circular CSF remains a separate
scientific identity using shared CSF policy.

## Proposed public API and implementation boundary

`Show`, `CollectResponse`, `Stimulus` and existing `TrialTimeline` retain their
semantics. `WaitForKey(name, key=..., slot=..., instructions=...)` declares a
readiness event, not an answer. `SessionTimeline` validates only timed Show and
WaitForKey phases, including an empty sequence. Both containers use the SAME
Phase representation, preparation service and executor. `run.trial()` and
`play_trial()` also accept flat lists/tuples through a small validated adapter;
lists can be composed using `+`. Nested sequences/callbacks are rejected.

`experiment(session_start=SESSION_START)` registers an optional flat sequence.
RunContext.initialise dispatches it once after normal preflight and before any
trial can start. This is a lifecycle concern; neither contrast strategy receives
a second opening loop. Session stimuli use the selected registered slot's base
parameters; trial preparation still supplies the current condition/state values.
Session events cannot update scientific state. No session declaration means the
old path, without a new delay, key, sound or event file.

Uppercase supported key names such as SPACE are literals; an identifier such as
start_key resolves from a declared ConfigField. Escape remains reserved. Session
instructions are independent of optional scientific-response guidance. Synthetic
readiness accepts the declared key at zero virtual elapsed time, without drawing
an observer response or consuming random numbers. Timed shows advance only the
virtual schedule. Audio records requests; synthetic runs generate no sound.

## Compatibility risks and mitigations

| Risk | Required boundary/test |
| --- | --- |
| Readiness becomes first answer | Separate key-wait result; never construct a scientific Response; held-key release filtering retained |
| RNG/state changes | 40 pre-change runs: all ten studies, both methods, seeds 0/19; compare complete canonical rows, action traces, adaptation history |
| Invalid declaration reaches display | Validate phase kinds, flatness, names, fields and slots before opening output devices |
| Pre-first-trial abort/error disappears | Dedicated optional session_events.json with partial events; runner retains zero-response abort/error lifecycle and closes output |
| Old readers/provenance break | Unchanged trial schema and existing sidecars; additive versioned session sidecar, optional manifest link and independent validation |
| Timed callbacks/renderer fork | No callbacks in session declarations; use existing prepare/play_phase/execute_timeline |
| Extension silently changes | No opt-in means no behavior change; existing registration/fingerprints unchanged |

The frozen baseline is also held in `event-first-baseline-20261027`; its full
Windows regression run is separate from implementation. Deterministic fixture
`tests/fixtures/event_first_baseline_20261027.json` was captured before production
edits. Hashes encode complete canonical rows/action traces rather than selected
endpoints. Software timestamps for session execution are not photon timings.

## Staged review gates

Stage A adds the API and representative regression tests only. Official protocol
defaults and files remain unchanged. Stage B must demonstrate CSF and ellipse
trial-order, geometry, response, full staircase and estimator equivalence before
any remaining official files are reorganized. Stage C then updates all active
files, extension starters, Configure/Review guidance and documentation, with
full Windows/Ubuntu regression evidence. No legacy compatibility removal,
automatic merge, release or tag is authorized by these stages.

## Executed Stage A evidence

- Frozen intake Windows suite: **1,925 passed, 1 skipped**, four retained
  registry warnings, 1,263.02 s. The first invocation could not use the shared
  Windows pytest temporary folder and failed during fixture setup; the complete
  retry used a new disposable project-local folder. No scientific failure was
  inferred from that filesystem problem.
- All **40** pre-change seeded runs match complete canonical trial rows, trial
  action traces (including resolved stimuli and response mappings), and adaptive
  histories after the additive API. Their defaults, event order and durations
  are unchanged.
- Combined session/input/audio, scientific baseline, shared method, calibration
  preflight and extension compatibility selection: **172 passed, 1 skipped**,
  111.79 s. Final focused session/presentation/audio selection after preserving
  the last session display's measured dwell: **60 passed**, 20.91 s.
- Representative Gaussian CSF and ellipse_major_axis comparisons cover both
  adaptive and fixed methods; complete reversal termination, initial one-down,
  last-trial status and primary threshold files also match with an opt-in opening.
- Escape, preparation/device failure and invalid readiness preserve zero accepted
  scientific responses. Re-sealed session-key, response, duplicate-event and
  timestamp tampering is rejected. A software window test confirms that a held
  readiness key cannot become the first trial answer.
- The Configure/Review test edits a session key through the existing editor and
  confirms the effective sequence and timing route. This is Textual test-driver
  evidence, not a claim of a new native acquisition/hardware session.
- Portability check passed. Full final-head cross-platform CI is recorded in
  the Stage A PR; no physical qualification is inferred from it.

The finalization test also preserves the first trial flip that finishes the last
session display's actual software dwell. That dwell can extend beyond the session
executor's return while the next trial is being prepared; planned duration,
software function interval and observed display dwell are distinct quantities.
Official experiment modules, scientific methods, adaptive algorithms, renderers,
configuration JSON, calibration and trial-column definitions are not changed in
Stage A. Stage B/C source conversions and starter-template migration remain
separate review stages, not completed acceptance claims in this PR.

The maintainer subsequently made **Windows the sole acceptance target**. The
existing CI matrix is retained, but Ubuntu is not a completion gate. The final
session/presentation/frozen-baseline/timeline group passed **104 tests** in
64.85 s, including both methods through the actual bounded presentation-test
workflow using an injected software display. A compatibility case retains the
old resolution behavior for laboratory TrialTimeline subclasses with required
constructor arguments. Final-head Windows CI is linked from the PR evidence.
