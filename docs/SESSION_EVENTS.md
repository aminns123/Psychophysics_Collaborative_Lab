# Python session openings

Stage A added this optional API. Stage B enables SPACE readiness followed by
1,000 ms settling in Gaussian CSF and Ellipse Major Axis only; see the
[source comparison and evidence](STAGE_B_EVENT_FIRST.md). Other experiments and
existing extensions retain their openings. Edit the migrated Python
`SESSION_START` list directly; `SESSION_START=[]` disables it. Their session-only
`ready_fixation` slot is a Gaussian fixation on the selected background.

## Optional Configure fields for a session opening

In an experiment that already registers a `fixation` slot, add these fields to
its existing `FIELDS`. They use the normal Configure editor and saved settings;
there is no second parameter store.

```python
from psychophysics_lab.researcher import (
    ConfigField, WaitForKey, Show, CollectResponse, Beep,
)

OPENING_FIELDS = (
    ConfigField("start_key", "Session start key", "choice", "SPACE",
                choices=("SPACE", "ENTER", "A"), section="Session start",
                help_text="Readiness only; this key is not a scientific answer."),
    ConfigField("initial_fixation_ms", "Initial settling fixation", "int", 500,
                minimum=1, units="ms", section="Session start",
                help_text="Once after readiness; separate from per-trial fixation."),
)

SESSION_START = [
    WaitForKey("ready", key="start_key", slot="fixation",
               instructions="Press the configured start key when ready. Escape cancels."),
    Show("settle", slot="fixation", duration="initial_fixation_ms"),
]
```

Pass `fields=FIELDS + OPENING_FIELDS, session_start=SESSION_START` to the existing
`experiment(...)` declaration. Configure exposes both fields. Review has a
**Session start (once)** group whose key/duration rows open those same editors;
the **Trial** rows still describe the repeated procedure. Selected-row details
retain the existing source/default information. A literal uppercase key such as
`key="SPACE"` also works; an identifier such as `start_key` references a field.
Escape is reserved. Lowercase letters are field names, not literal key aliases.

RunContext.initialise executes the opening once. Do not call an extra runner or
add readiness to the trial loop. `session_start=()` is the default and introduces
no key, delay or sound. Instructions during readiness are independent of the
optional scientific-response guidance checkbox. A fresh keypress is required
after onset; if the same key also answers trials, release it before answering.

## Reusable flat trial events

The existing `TrialTimeline` remains supported. A trial may alternatively be a
flat list or tuple passed to `run.trial(...)` or `run.play_trial(...)`:

```python
def fixation(settings):
    return [Show("fixation", slot="fixation", duration="fixation_ms")]

def trial_events(settings, condition):
    return fixation(settings) + [
        Show("target", slot="target", duration="stimulus_ms"),
        CollectResponse(actions=("left", "right"), slot="fixation"),
    ]
```

Use this only for a task whose actual alternatives are left/right and whose
registered slots are fixation/target. Existing CSF uses a grating slot; the
ellipse task uses first/second intervals and scientific meanings. Do not change
those identities merely to copy this example.

Nested lists, arbitrary event callbacks, repeated names, multiple scientific
response windows, and visual events after a scientific response are rejected.
Changing order requires a scientifically justified protocol change. Call the
event function for each newly selected condition; do not precompute future
adaptive values. Supply current values through the existing
`parameters_by_slot=prepare_stimuli(run, condition, method.state)` path.
`method.accept_response(...)` and the experiment's update rule remain responsible
for the next contrast. They do not run during timed display phases.

To add another stimulus, register/select its class from `stimulus_library.py`
using the existing stimulus-slot/default workflow, then refer to that slot from
Show. A session uses the selected slot's validated **base** parameters. It does
not run trial-specific condition preparation. Review labels that distinction.

## Optional audio requests

`Show(..., beep=Beep(550, 35))` requests a tone at display onset.
`CollectResponse(..., beep=Beep(550, 35))` requests a tone only for an accepted
scientific answer. `WaitForKey(..., beep=Beep(550, 35))` requests a distinct
`accepted_readiness` tone. Leave `beep=None` to preserve silent behavior; no new
official tone is enabled. Use a declared Configure field to choose whether to
construct a Beep while building the sequence outside the timed executor.
Physical audio retains the existing Windows-only, asynchronous request service;
software requests do not measure acoustic onset or certify speaker output.

## Synthetic policy, records and failure boundaries

A synthetic readiness event accepts the resolved key immediately at zero virtual
elapsed time. It generates no keyboard input, scientific Response, observer RNG
draw or sound. Timed session shows advance the session's virtual clock. The
scientific trial observer and its RNG remain unchanged. The same event plan is
used by human runs, presentation tests and synthetic runs.

Opt-in runs add `session_events.json` schema 1, linked and hashed in the existing
manifest. It retains declared/resolved plans, selected base stimuli, event order,
readiness observations, software timestamps and partial error/abort events.
Virtual time and host execution timestamps are separate; neither measures
photons. No trial-schema column, scientific count or staircase history is added
for readiness. Existing data readers and the read-only validator continue to
accept older runs without this optional file.

The first trial flip may finish the last session display's measured software
dwell; finalization retains that observation. Display dwell can extend beyond
the session executor's return during trial preparation. It is distinct from
the planned duration and from the executor's software start/finish interval.

Escape before the first trial produces a zero-response aborted run. Preparation,
output-device and persistence failures terminate through existing recovery and
cleanup. If a device cannot open, a saved error/session trace can be inspected,
but the validator reports missing runtime/resolved evidence; it does not invent
successful display metadata. No-event sessions create no session sidecar.

Stage B reorganizes only Gaussian CSF and Ellipse Major Axis. Their
`trial_events(settings, condition)` lists drive acquisition and generic Review;
older `make_trial()` callers remain supported. Stage C remains a separate migration
of the other eight official experiments and starter templates.
