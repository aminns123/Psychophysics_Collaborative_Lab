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

## The six-section experiment narrative

The proposed [version-1 A1/A2/B authoring standard](EXPERIMENT_AUTHORING_STANDARD.md)
is at the Issue #165 design-freeze checkpoint. Its external reference examples
are executable; approval and family migration remain separate. The ten current
official sources below remain the accepted implementation until reviewed
migrations are approved. See the [migration plan](EXPERIMENT_MIGRATION_PLAN.md).

All ten official experiments and the bundled extension starters now use:

1. **PARAMETERS:** ConfigField declarations, response alternatives, stimulus slots
   and defaults. Read selected settings from `run.values` or `settings`.
2. **SESSION START — ONCE:** `SESSION_START`, passed to
   `experiment(session_start=SESSION_START)`. An empty list disables it.
3. **TRIAL EVENTS — REPEATED:** `trial_events(settings, condition)` returns an
   ordinary flat event list. Nearby `prepare_stimuli(run, condition, state)`
   resolves the current condition and latest adaptive strength into slot parameters.
4. **SCIENTIFIC RULES — CONDITIONS AND UPDATES:** conditions, seeded selection,
   response interpretation and explicit response-dependent stimulus updates.
5. **STOPPING AND RESULTS:** termination, scientific measurements, estimators
   where applicable and the procedure connecting these rules to RunContext.
6. **FRAMEWORK REGISTRATION — MINIMAL AND LAST:** the final `SPEC` connection.

This is a reading structure, not a requirement to invent empty functions or use
the same scientific loop in every study. See the
[Stage C comparison and evidence](STAGE_C_EVENT_FIRST.md).

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
