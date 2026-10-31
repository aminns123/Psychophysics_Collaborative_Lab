# Wave 3: Contrast sensitivity source migration

## Accepted reference and boundaries

Both files (contrast_sensitivity, contrast_sensitivity_windowed) are reorganised from merged develop
`8f493fa0a54cbe57109943120b5e410e77c0541a` (tree identical to reviewed
`fdb61410f62daffa08af7a424445d6eb1c28277c`). This does not assert that the
separately investigated post-merge develop CI is green. No merge is authorised.
Waves 1/2 are retained. Other families, shared methods, runner, rendering,
recording, calibration, extension trust and saved-run readers are unchanged.

The exact pre-migration source and representative settings are frozen in
`tests/fixtures/issue165_wave3/`. `baseline.json` pins old and new LF-normalised
SHA-256 identities. Historical Stage A/C and authoring fixtures remain unchanged.
Guards exempt only explicitly manifest-pinned migrated identities; all remaining
official sources retain their historical source and scientific checks.

## Before and after: reading the science

Before: parameters, opening and events appeared early, but stimulus preparation,
measurement dictionaries, response instructions, scientific metadata and framework
record projection were interspersed. After:

| Researcher task | Location |
|---|---|
| Change conditions/defaults/units/bounds | A1 `FIELDS`; inspect A2 `make_conditions` for enumeration |
| Find target alternatives/keys and placement/time | A1 `RESPONSES`, slots and `trial_events`; effective renderer inputs in A2 `prepare_stimuli` |
| Change opening | A1 `SESSION_START`; `[]` disables it |
| Inspect saved journal values | A1 `trial_measurements` (and CSF fixed measurements); canonical meanings remain declared |
| Inspect selection, counters, next strength, headroom | A2 named scientific functions; no new manager |
| Inspect stopping and estimator | A2 `is_finished`, `primary_rule`, `finish_experiment` |
| Connect execution/recording/Review | B existing procedure, record projection and public registration |

This is one Python file per public ID. Scientific decisions remain inspectable;
moving them into a shorter integration wrapper was not the goal. Circular CSF
retains explicit one-way Gaussian scientific reuse, never a prototype dependency.
For ellipses, fixation → first interval → ISI → second interval → response remains
one ordinary flat A1 list, with the original optional cues on both onsets.

## Executed equivalence contract

`test_issue165_wave3.py` executes frozen/current/current with identical seeds
and TeachingObserver responses through the canonical runner. Both opening enabled
and `SESSION_START=[]` are covered. It checks exact 20-column trial bytes,
trial presentations and prepared parameters, chronological events, trial actions,
every adaptive state/history, reversal/termination output, primary thresholds,
resolved scientific metadata and repeated determinism. Each output is independently
validated by the saved-run validator and opened by the established reader.

Cases include both methods/seeds 0 and 19, completed adaptive tracks, a safety
ceiling/incomplete adaptive result, complete fixed schedules, rejected undersized
fixed ceilings, ESC-equivalent abort before Trial 1 (zero accepted answers) and
third-response interruption (two accepted answers). Default/bounds/keys/slots/
calibration/column metadata and effective Review plans are compared.
The existing injected-display presentation tests run in the complete suite;
software tests do not establish physical photon, input or audio timing.

Intentional differences: source order, documentation and source identity only;
measurement dictionaries are named functions with unchanged values. No scientific
observations or canonical bytes are added, removed or normalised away. Session
wall-clock start/finish fields are checked for ordering then excluded from exact
comparison; all scientific session/trial content remains compared.

## Acceptance and limits

Targeted equivalence: 40 cases. Final Windows/portability/CI evidence is recorded
in the PR after execution. Test → Ready, source invalidation, external APIs,
historical readers, geometry/intensity constraints and generic Configure/Review
remain covered by the existing complete suite.

Independent researcher readability and real laboratory apparatus: NOT VERIFIED.
This is source/software qualification, not human or physical acceptance.

### Existing circular fixed-mode Review defect (retained, not concealed)

Both frozen and migrated circular CSF register the inherited Gaussian fixed-mode
Review factory. It requests absent `grating_sigma_deg` and raises `KeyError`.
The test pins this precise pre-existing failure before and after; it does not
pretend Review passed or silently replace the experiment's method. Circular
fixed acquisition/simulation and saved results pass exact equivalence. A separate
reviewed correction should bind the circular `fixed_contrast_method` reviewer;
until then accurate circular fixed-mode Review is a known acceptance limitation.
