# Issue #165 — Wave 2 orientation migration

Frozen reference: develop `649b7058cc6692e476cac4121ab847cb4ebf1759`, whose
source tree matches accepted main `179d32f`. Only `orientation_task.py` and
`orientation_adaptive.py` are migrated. Wave 1 is already complete; Waves 3–5
are not started. The onboarding and visual passes are separate PRs.

## Scientist-facing reading map

| Scientific task | Before | A1/A2/B location |
|---|---|---|
| Identify negative/positive targets and their keys | Parameters, selection and record callback | A1 response declaration and signed-angle explanation; A2 `choose_condition` |
| Change appearance/tilt magnitude | Selected TeachingGabor parameters, then prepare/choose callbacks | A1 explains selected absolute orientation; generic Review edits stimulus values; A2 retains conversion |
| Change timing/order/readiness | Parameters, session and trial-event sections | A1 fields, SESSION_START and the same authoritative `trial_events` |
| Understand saved values | Record callback and runner | A1 `trial_state`, explicit state units and canonical/fixed-record explanation; B forwards the same state |
| Inspect adaptation, starting contrast and stopping | Scientific rules, initialization, stopping and registration | A1 mode differences; A2 methods, original initialization, bounds and finite stopping |
| Connect execution and recording | Procedure mixed with stopping | B existing initialization/record projection, unchanged shared runner and SPEC |

These are sections of one ordinary Python file. No new condition framework,
execution engine, wrapper class, configuration system or shared mathematical
extraction is introduced. The files are not shortened at the expense of science.
Original scientific function bodies remain directly inspectable; initialization
metadata/state and participant prompts move ahead of mechanical integration.

Target alternatives are not scientific factors or independent tracks. Both files
balance scheduled negative/positive rows (one extra target 0 for odd counts),
then shuffle with `random_seed`. Historical canonical condition encodings remain
signed angles in original/adaptive modes and the existing `tilt_sign` cell label
in fixed mode. Fixed repetitions are per cell, not per response alternative.

`orientation_task` retains original/adaptive/fixed modes. Original uses selected
stimulus contrast; its optional shared teaching adaptation uses starting_strength.
`orientation_adaptive` retains adaptive/fixed modes and its own established
adaptive starting contrast from the selected stimulus. Its multiplication,
zero/up-step handling, representable-number floor and saturation at 1 are
unchanged. Neither finite procedure becomes a reversal-converged threshold study.

## Data and compatibility boundary

No custom measurements, canonical columns, journal observations or resolved
scientific metadata are added or renamed. A1's state function only projects the
existing contrast/factor observations; STATE_UNITS documents these in Python
without inventing physical measurements or adding a serialization contract.
The existing canonical data dictionary and fixed-mode records retain their exact
meanings. Source hashes/line positions legitimately change; saved runs retain
the actual new provenance rather than pretending that old source was executed.

Defaults/bounds, IDs, response meanings, events, cues (none), placement,
random draws, stopping, calibration requirements, readiness, historical readers
and generic Configure/Review remain unchanged. One Python source remains per ID.
The existing make_trial compatibility adapter points to the same trial_events.

## Equivalence evidence and acceptance

`tests/fixtures/issue165_wave2` preserves both complete pre-change sources and
their hashes. The exact current-source guard now pins these two migrated files
and verifies their immutable historical references, while retaining guards for
the other eight sources and shared scientific code. No scientific fixture is
rewritten, skipped or weakened to accommodate the migration.

The dedicated comparison executes frozen/current/repeated-current definitions
through the same canonical runner: all five supported experiment/method pairs,
seeds 0/19/137, observer accuracies 0/.65/1 and empty/standard openings. Canonical
trial bytes, complete actions/journals, adaptive histories/session, resolved
metadata and primary-result presence/contents match. Readiness abort, third-trial
abort and timeout preserve identical incomplete-run observations. Separate tests
compare seeded conditions/fixed schedules, event plans, invalid bounds, Review's
scientific plan and zero/subnormal/upper-bound next contrasts. Source line
locations are deliberately excluded only from the read-only Review plan
comparison; full recorded scientific documents remain compared.

Targeted Windows checks: **104 passed** after final readable formatting. Complete
Windows/portability results and exact-head CI links accompany the PR. The full
suite retains frozen Stage C output comparisons and real injected-display phase
player, readiness-abort, source invalidation and legacy extension regressions.

Software equivalence is PASS only after those final checks pass. Independent
researcher comprehension/native acceptance and physical display/input/audio
qualification remain **NOT VERIFIED** by these tests. A scientist making a new
factor design or changing stopping still needs to inspect the named A2 callback
interfaces; this migration does not claim to remove that programming requirement.

No working installation, environment qualification, external laboratory source,
configuration, calibration or participant data is edited. Maintainer review and
explicit merge approval remain required; this wave does not approve the next.
