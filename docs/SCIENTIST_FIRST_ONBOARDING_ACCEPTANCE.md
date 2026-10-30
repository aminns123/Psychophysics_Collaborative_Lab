# Scientist-first onboarding acceptance

Baseline: develop `649b705` / source-identical main `179d32f`. The separate
PR #181 startup/environment proposal is not included or changed.

## Recommended learning path

1. Learn / Help → short walkthrough: first operate Configure/Review, then author.
2. Build Experiments → A1/A2/B: basic discrimination; inspect the official
   teaching counterpart or the independent local `demolab__left_right.py`.
3. Build Experiments → A1/A2/B: adaptive / fixed → `demolab__line_strength.py`.
4. Local laboratory starters → create a separate folder, read source, explicitly
   trust it, Preview/Test → Ready, then Review and simulate the local definition.
5. Read the detailed approved standard and Gaussian/temporal references when
   developing new science. The older six-section sources remain supported
   scientific references, not the primary new-author teaching path.

The two official Wave 1 teaching sources were already migrated and are not
rewritten. The other eight official Python sources, shared mathematical methods,
runner, stimulus library and recorder are unchanged by this PR.

## Before and after: executable local examples

| Task | Before | After |
|---|---|---|
| Locate everyday study choices | Parameters/events and saved measurements separated across six sections | A1 holds question, fields/units, targets, session/trial chronology and measurement declaration |
| Understand selection and scientific updates | Scientific rules and stopping in separate sections | A2 holds selection, scoring, counters/methods, bounds and stopping/results |
| Find the mechanical connection | Procedure mixed with stopping/results | B connects existing RunContext or run_contrast_experiment, records and SPEC |
| Learn adaptive vs fixed science | Follow imported method plus registration | A1/A2 comments and field map distinguish conditions, alternatives, one finite teaching track and cell repetitions |
| Find examples from the TUI | Older layout taught; local shared-method example not directly linked | Direct basic, adaptive/fixed and local-starter source links; generic UI unchanged |

No empty wrapper sections or new condition manager are introduced. The basic
example still alternates left/right and saves the same offset/correct-count
observations. The strength example still uses the installed teaching adaptive
method and fixed schedule; the named fixed measurement declaration forwards the
same existing repeat and digital increment. Fixed Review now calls the actual
fixed factory, exposing its existing scientific mapping and measurement units.
That is inspection of the execution definition, not an alternate schedule.

A scientist editing A1 need not understand RunContext/JSON serialization to
change timings, keys or declared measurements. Changing conditions, placement,
strength convention, scoring or stopping requires deliberate A2 validation.
Adding a different method still requires understanding its existing public
callback interface; this is not claimed to remove all programming knowledge.

## Scientific and extension evidence

`tests/fixtures/onboarding_develop_649b705` preserves both exact LF-normalized
pre-change starter sources and their hashes. The new comparison runs frozen,
current and repeat-current definitions through the same real canonical runner:
three applicable experiment/method pairs × seeds 0/19/137 with observer accuracy
0/.65/1 × empty/standard opening. It compares canonical TSV bytes, complete
trial actions/journals, resolved metadata and adaptive histories/session without
dropping scientific fields. Session plans, readiness, virtual timing and resolved
stimuli also match; only validated wall-clock recording times differ.

The existing independent annulus-before/after-cue laboratory fixture is reused,
not imported from or renamed from an official experiment. Its own custom
stimulus, cue-gap conditions, B/A responses and journal measurements are tested
in fresh processes in both layouts: project-file discovery and a separate
explicitly trusted `PsyCoLab_Extensions/experiments/` folder. Both adaptive and
fixed methods use the canonical runner/20-column recorder. No core TUI or
registry edit is needed. The fixture's temporal science is an acceptance example,
not a newly qualified protocol.

| Acceptance item | Outcome / evidence |
|---|---|
| A1/A2/B reachable through Build/Learn | Automated real-widget source-link test |
| Two executable teaching examples | Frozen/current/repeated-run scientific comparison |
| Generic Configure and Review, official and external | Existing separation and independent-authoring route tests |
| Custom stimulus, declared conditions/responses/timing/measurements | Independent annulus fixture Review and saved-journal tests |
| Generic editing, missing/invalid drafts, presets and F5 | Independent route suite retains corrections and selected values |
| Actual external source and stimulus navigation | Existing decoy-file test verifies the external target |
| Trust, Test → Ready, source-change invalidation | Real extension/development controller and fingerprint tests |
| Canonical data and historical/legacy compatibility | Canonical byte comparisons, validator, reader and archived pre-Stage-C extension test |
| Independent human comprehension / native researcher exercise | NOT VERIFIED by automated tests |
| Physical display/audio/input qualification | NOT VERIFIED by software tests |

Exact final Windows/portability results and CI links accompany the PR. Existing
laboratory folders are never overwritten or silently upgraded to these starter
sources. No working environment, calibration, participant record or qualification
evidence is changed. Adoption of the learning narrative does not approve the
remaining official migration waves.
