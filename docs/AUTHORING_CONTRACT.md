# PsyCoLab authoring contract

The [code philosophy](CODE_PHILOSOPHY_AND_CONTRIBUTIONS.md) defines long-term
architectural goals and contribution policy. The experiment Python file owns
scientific behaviour. The framework executes it, and the TUI discovers, configures
and inspects the registered definition.

## Where scientific code belongs

Official experiments are curated reference implementations in
`src/psychophysics_lab/experiments/<id>.py`. Their IDs match their filenames.
New paradigms and variations normally begin as uniquely named
[laboratory extensions](LABORATORY_EXTENSIONS.md). Promotion into the official
catalogue requires a reviewed PR; a local contribution must not replace an
official experiment or stimulus.

Official visual definitions are `LibraryStimulus` classes in
`src/psychophysics_lab/stimulus_library.py`, with `PARAMETERS`, `render()`
and `SPEC`. External laboratory stimulus classes use the documented extension
layout and the same public interfaces. Renderers receive calibrated coordinate
arrays in degrees and return intensity arrays. Scientific equations, masks,
geometry and contrast conventions belong in the stimulus class or named
scientific methods, with units stated explicitly.

## Recommended A1/A2/B experiment narrative

Use the approved [version-1 authoring standard](EXPERIMENT_AUTHORING_STANDARD.md)
for every new experiment. Begin with the [researcher walkthrough](LEARN_PSYCOLAB.md)
and three [progressive left/right lessons](../examples/laboratory_extensions/LESSONS.md).

1. **A1 — Experimental choices:** scientific question, parameters/units/bounds,
   conditions, target alternatives/placement, keys, session/trial events and
   declared measurements. This is the normal starting point for study edits.
2. **A2 — Scientific methods:** condition/track construction and selection,
   randomisation, scoring, effective strength conversion, response updates,
   stopping and estimators. Changes here require deliberate scientific validation.
3. **B — Framework integration:** connect the declarations to existing execution,
   recorder, Review hooks and SPEC. Normally leave this unchanged.

These are sections of one ordinary Python file. Do not invent wrappers, a new
condition manager or empty functions merely to fill a heading. Keep consequential
science in A1/A2 and pass the same event factory to Review and execution.

The approved family migrations use this narrative. Remaining official families
retain their accepted implementation until their separate PRs are approved;
those sources and older extension APIs remain supported. Historical [Stage C evidence](STAGE_C_EVENT_FIRST.md) is retained, not
the primary new-author tutorial. See the [migration plan](EXPERIMENT_MIGRATION_PLAN.md).

## Chronological events and scientific updates

```python
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation",
               instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]

def fixation_events(settings):
    return [Show("fixation", slot="fixation", duration="fixation_ms")]

def trial_events(settings, condition):
    return fixation_events(settings) + [
        Show("target", slot="target", duration="stimulus_ms"),
        CollectResponse(actions=("left", "right"), slot="fixation"),
    ]
```

Register the named slots and import the events from
`psychophysics_lab.researcher`. A ready slot must contain fixation only, without
the task's probe or other stimulus. Readiness waits indefinitely for a fresh
keypress, runs once before Trial 1, and is never a scientific response, adaptive
update or observer draw. Escape aborts with zero accepted responses.

A trial contains one response stage. Events describe displays, response collection,
optional cues and observation markers. Keep scientific updates outside timed
displays, inside the existing `run.trial()` recording boundary. A shared-method
experiment passes `trial_events=trial_events` to `run_contrast_experiment`;
a direct procedure passes the flat list to `run.trial()`. Resolve each new trial's
strength from the current state, rather than precomputing future adaptive values.
Small functions may compose lists with ordinary `+`; no nested runner is needed.

The experiment declares optional `Beep(frequency_hz, duration_ms)` on Show or
CollectResponse; drawing classes do not own sound. Adding a new experiment with
existing public components requires no change to `ui/setup.py`.

## Configuration and compatibility

ConfigField editing remains available through generic Configure/Review. Exposing
the ready key or settling duration as fields is optional: researchers can edit
their Python literals directly. Selected overrides remain authoritative; neither
Review nor a second parameter store defines a competing experiment.

Older `make_trial(settings, condition)`/TrialTimeline definitions and supported
legacy actions remain compatible. Migrated files retain
`make_trial = legacy_trial_factory(trial_events)` at registration for existing
callers. This small central adapter wraps the same list; it does not maintain
another event definition. Acquisition, simulation and Review share the public
event factory. Existing extensions are not rewritten or automatically trusted.

### Read-only selected-method inspection

An experiment can reuse its existing fixed-method factory in Review:

```python
method_reviewer={"constant_stimuli": constant_contrast_method}
```

The factory returns its existing `ConstantContrastMethod`. Review inspects the
real schedule, preflight bounds, resolution and pure record projection using a
context that forbids saving, input and trial execution. It never advances the
method or accepts a response. Older callable `method_reviewer` callbacks retain
their adaptive-only `(conditions, selected_condition, state)` contract; fixed
experiments without a declared factory retain the existing planner fallback.

Optional ordinary Python `MEASUREMENT_UNITS` maps journal field names to explicit
units. Review obtains the actual fields and representative values from the
existing pure `trial_record` or selected fixed record function. These are journal
measurements, not additional canonical TSV columns. `REVIEW_INACTIVE_FIELDS`
can map a method name to retained settings that do not control that method's
trials or estimator. Such settings remain subject to established validation;
the declaration does not change defaults, validation, recording or execution.
Keep `max_trials` active when the fixed planner enforces its safety ceiling.

Use existing `stimulus_parameter_controls` to link an effective renderer input
to its controlling ConfigField. These links affect inspection/edit navigation;
they do not bind different acquisition values or infer a control from coincident
numeric values. None of these optional declarations changes source fingerprinting:
the complete actual experiment source is still recorded and invalidates readiness
when changed.

## Recording and validation

RunContext and the canonical recorder allocate external run folders and save the
existing 20-column TSV, scientific state, event records and source provenance.
Do not add file writing to renderers or timed callbacks. Trial journal records
preserve accepted input and partial events on interruption; readers report
incomplete writes. Historical runs retain their saved identities and metadata:
interpret them from their own manifests, without rewriting participant files.

Preview/Test/Ready source fingerprints, hardware calibration and acquisition
qualification remain separate checks. Software tests do not establish physical
luminance, photon timing, audio onset or response latency. Preserve the existing
preflight and protocol qualification requirements.

Start with [the learning guide](LEARN_PSYCOLAB.md), the
[experiment file guide](../src/psychophysics_lab/experiments/README.md) and the
[bundled extension walkthrough](../examples/laboratory_extensions/METHODS.md).
