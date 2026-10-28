# PsyCoLab experiment authoring standard — version 1

**Design-freeze proposal for maintainer sign-off, Issue #165 / PR #167.**
The current official experiments at main `a5aa56a` remain the accepted scientific
baseline. This PR selects one narrative and qualifies its reference examples;
it does not authorise or perform the official migration. Independent researcher
usability remains NOT VERIFIED until a real researcher completes the exercise.

> A scientist describes the experiment in the order they think about the
> science. PsyCoLab safely executes, validates and records it.

## Decision

Use **one ordinary Python file per experiment**, read in this order:

1. **Part A1 — Experimental choices:** question, meaningful parameters/units,
   factors, alternatives/placement, session opening, chronological trial events,
   and explicitly declared measurements. Everyday editing starts here.
2. **Part A2 — Scientific methods:** condition/track construction, selection and
   balancing, scoring, effective stimulus conversion, response-dependent updates,
   initial scientific state, bounds, stopping, estimators and scientific checks.
   Readable and deliberately editable, with renewed scientific validation.
3. **Part B — Framework integration:** connect those declarations/functions to
   the existing methods, RunContext, recorder and registry. Normally unchanged.

These are sections, not separate files, a new class hierarchy, a DSL or another
execution engine. No generated protocol, hidden queue or condition manager is
required. Small ordinary functions returning flat lists/dictionaries are enough.
Do not create a wrapper merely to fill a section or enforce identical function
names/counts on scientifically different studies.

The executable reference candidate is
[`demolab__csf_two_part.py`](../examples/scientist_first/experiments/demolab__csf_two_part.py).
The contrasting
[`demolab__temporal_order.py`](../examples/scientist_first/experiments/demolab__temporal_order.py)
uses the same narrative for a fixed temporal-order task. These become the
accepted authoring examples only after maintainer sign-off; neither replaces an
official experiment or establishes a new scientifically validated protocol.

## Part A1: what a scientist normally changes

Put the question and controlled quantities first. Name values in scientific
units: `frequency_cpd`, `x_deg`, `stimulus_ms`, or an explicitly named digital
increment. State defaults, accepted bounds and whether a value is a study choice,
derived quantity or invariant. A digital command is not measured luminance,
optical contrast, acoustic onset or photon timing.

Use existing `ConfigField` declarations where generic Configure editing is useful.
Plain Python constants/lists remain valid choices; no mandatory TUI toggle or
second parameter store is introduced. Effective selected values override Python
defaults. Changing a default does not overwrite a previously selected preset.

Declare response alternatives as meanings and physical targets, not unexplained
integers. In the CSF example, `TARGETS` lists left/right names, keys and coordinate
signs; `target_position` maps them to degrees. Declare stimulus identities and
acquisition/calibration requirements visibly. A new scientific variant needs a
new laboratory identity and review; it must not replace official science silently.

Write chronological events explicitly:

```python
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]

def trial_events(settings, condition):
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("grating", duration="grating_ms",
             stimuli=(Stimulus("grating", **target_position(settings, condition)),)),
        CollectResponse(actions=RESPONSES.alternatives, slot="fixation"),
    ]
```

The opening runs once. `SESSION_START=[]` disables it. Readiness consumes no
scientific response, staircase update or observer draw; Escape before Trial 1
leaves zero accepted responses. A pure fixation slot must not accidentally show
a task probe. Audio is an explicit optional event request, not a rendering side
effect or evidence of measured synchronisation.

`trial_events(settings, condition)` is authoritative for Review, simulation and
acquisition. Compose flat lists with ordinary functions/`+` where helpful.
Describe the current trial; never precompute future adaptive strengths.

## Conditions, targets and tracks are different things

| Concept | Gaussian CSF | Two-interval ellipse | Temporal before/after |
|---|---|---|---|
| Scientific condition | Spatial frequency | Position, ratio and ring state (centre task has x=0/ring present) | Signed target-minus-cue SOA |
| Strength | Digital peak-to-peak modulation | Digital probe increment above background | Fixed line appearance; no adaptive strength |
| Target alternative | Left/right location | First/second interval containing probe | Before/after visual cue |
| Staircase track | One independent repeat per frequency | One independent repeat per condition | None |
| Fixed repetition | Presentation within condition/strength cell | Presentation within condition/strength cell | Equal presentations per signed SOA |

The reference's `scientific_conditions(settings)` exposes factor levels in A1.
Its historical `make_conditions(settings)` hook builds independent adaptive
**tracks** in A2. Its docstring says so. `id` identifies a staircase, `repeat`
identifies its independent repetition, and `target` is assigned separately on
each presentation. Increasing staircase repetitions must not multiply the fixed
condition plan. Existing shared probe methods deduplicate tracks by scientific
`value` before fixed scheduling; preserve that behaviour.

Legacy teaching files call scheduled target rows “conditions”; some canonical
`stimulus_condition` values also encode a target-dependent position/angle. The
migration must explain those established encodings, not silently reinterpret
them or rename recorded fields. New factor lists may clarify the concepts while
small compatibility hooks retain existing callers and exact selection order.

No universal balancing policy is imposed. Record the actual seed source and
draw order. CSF/detection tasks use run-seeded active-track selection followed
by independent target draws; teaching tasks may shuffle with the selected
`random_seed`, and their original alternating task remains alternating. Preserve
odd-repeat policy and fixed-level RNG order. “Balanced” must not be claimed for
an adaptive target stream that is independently equiprobable.

## Part A2: scientific methods remain inspectable

Prefer recognisable names such as `make_conditions`, `choose_condition`,
`interpret_response`, `prepare_stimuli`, `change_contrast`, `update_experiment`,
`is_finished`, `primary_rule`, and `results`. Document what a legacy name returns
instead of introducing another object model. The necessary callback signatures
may receive a run/state; a scientist changing A1 does not need to understand that
execution object or recorder internals.

Keep selection policy, counterbalancing, target assignment, renderer-parameter
conversion, digital bounds, initial scientific state, response correctness,
adaptive rule and stopping/estimation decisions here or in explicitly named,
already-tested scientific methods. New numerical logic requires scientific
review and regression evidence, not just an integration test.

For example, the reference shows the log10 exponent and calls the existing
`bounded_log_step`; it does not replace that numerical method. Its median of
last presented reversal contrasts and arithmetic across-track mean are explicit
in `primary_rule`. Line-position studies instead require their established
geometric mean. Finite teaching adaptation is not reversal convergence or a
validated threshold estimator. Fixed levels report accuracy without inventing
an adaptive threshold. Preserve incomplete and boundary-affected result flags.

The temporal example shows its signed SOA calculation and both event orders.
Its cue visibly differs from fixation. It validates non-overlapping durations,
paired signs and its finite schedule, and reports accuracy/fraction “after” per
SOA without claiming a PSE/JND. Reversing displayed order also requires reviewing
condition signs, scoring and saved measurements; changing a heading cannot make
inconsistent science valid.

## Declaring measurements without learning serialization

The scientist declares names, values and units together in A1:

```python
MEASUREMENT_UNITS = {
    "probe_x_deg": "degrees",
    "target_interval": "interval number, 1=first, 2=second",
    "requested_probe_increment": "digital I_probe - I_background",
}

def trial_measurements(settings, condition):
    return {
        "probe_x_deg": condition["x_deg"],
        "target_interval": condition["target"] + 1,
        "requested_probe_increment": condition["contrast"],
    }
```

This ellipse illustration uses its real science; it is not a new implementation
of either official ellipse file. Canonical target codes remain 0/1. The extra
interval measurement explicitly says 1/2, so analysts cannot confuse them.

Custom measurements are finite scalar numbers, strings or booleans. Validate
that every declared key has a value/unit before display; reject absent, nonfinite
or nonscalar values rather than inventing a plausible value. State whether a
quantity is requested, software-observed or physically measured. Pre-response
measurements cannot contain future responses; response/update-dependent results
use the established accepted-response/state records or a named final estimator.

Part B passes these values through the ordinary trial-record argument. Scientists
do not write JSON, add custom recorder columns or perform timed file IO. The
current examples save custom values in the existing per-trial journal and units
in resolved metadata. An optional derived TSV may read them, keyed by trial index,
but must preserve original data and refuse accidental overwrite.

### Automatic versus experiment-declared records

| Field/group | Owner and interpretation |
|---|---|
| Trial index, accepted response, key, correctness and software event time | Existing runner/recorder; scoring is declared in A2 |
| Target alternative | Existing 0-based response code; A1 supplies meanings |
| `stimulus_condition` | Existing experiment-specific encoding; preserve it |
| Staircase ID, trial index, step, reversal/count, completion | Existing adaptive engine/projection; no invented fixed-mode tracks |
| Presented/next contrast or intensity | Existing canonical columns with the experiment's exact scientific units/convention |
| Run status and interruption evidence | Existing lifecycle; partial records are not completed trials |
| Resolved stimulus parameters/placements and event plans | Existing presentation/provenance path from A1/A2 definitions |
| Source hashes, selected settings, monitor profile and qualification status | Existing provenance; source identity changes legitimately during migration |
| `trial_measurements` and `MEASUREMENT_UNITS` | Experiment-owned additional scalars and explicit units |

The canonical table remains exactly 20 columns. Existing journal keys/meanings
also remain readable; a migration may add declared measurements, not silently
rename old observations or rewrite saved records. See the
[complete field map and ten-experiment assessment](EXPERIMENT_MIGRATION_PLAN.md).

## Part B: minimal connection, no hidden science

Use the existing `run_contrast_experiment`/method adapters or direct RunContext
procedure. A direct loop is appropriate for different science. Pass the same
event factory and scientific callbacks; route declared measurements to the same
recorder. Part B may project declared values into canonical fields, connect
configuration bindings, initialise infrastructure and register `SPEC`.

It must not choose target meanings, frequency levels, step sizes, condition
selection, stopping counts, averaging rules or calibration requirements secretly.
Those decisions must be visible in A1/A2 and referenced here. Keep necessary
integration explicit; do not hide it behind a second framework.

Retain `make_trial = legacy_trial_factory(trial_events)` and the small existing
Review planning hooks where required. They point at the same definition, not
another event list. External trust, namespace/collision, source-change and
Test → Ready protections remain intact. Official IDs and one source file per
experiment remain stable.

## Dependencies: no source-hash workaround or circular migration

The refined CSF example is self-contained scientific Python using existing
public events/methods and shared mathematics. It imports no official experiment
module and has no reference-source hash guard. Tests compare its scientific
outputs with current official CSF. Consequently, official migration cannot
create an official → example → official cycle or unexpectedly invalidate the
example because an old official file was reformatted.

Existing official reuse, notably circular CSF's one-way use of Gaussian CSF,
must be reviewed as a pair. Keep that explicit dependency unless a separately
justified/tested scientific extraction is approved. Do not manufacture a shared
condition framework to shorten files. Declare all required source dependencies
through existing provenance mechanisms; never remove source/readiness checks to
make a migration pass.

## Why replace the six-section narrative?

The old layout usefully made chronology visible, but placed everyday choices,
scientific rules and execution/recording work across several sections. A novice
often had to inspect a recording callback to find saved measurements or track
constructor to find factor values. The A1/A2 boundary collects the decisions a
scientist normally edits, while retaining the derivation and consequences nearby
in the same file. A2 makes deliberate scientific modifications reviewable; B
isolates mechanical integration. Event order stays explicit.

This is a comprehension decision, not a line-count target. Removing a source
dependency can make the reference longer, because previously hidden scientific
initialisation is now visible. Do not compress equations, duplicate event lists
or replace readable functions with an opaque abstraction to claim fewer lines.

## Sign-off and migration gates

The [acceptance checklist](AUTHORING_STANDARD_ACCEPTANCE.md) records PASS / FAIL /
NOT VERIFIED. Maintainer sign-off approves **this version-1 narrative, the
Gaussian reference, the measurement boundary and the family-based migration
plan**, with the documented independent-usability limitation. A merge alone is
not a physical apparatus qualification or proof of novice comprehension.

Stop at this design-freeze checkpoint until reviewed and approved. Thereafter,
follow [five independent family waves](EXPERIMENT_MIGRATION_PLAN.md), capturing
each wave's actual current-main baseline before editing. Each requires its own
review, full Windows checks and explicit merge decision. Completion of one wave
does not approve or merge the next. Stage 4 native/independent acceptance and
Stage 5 rollback remain separate milestones.
