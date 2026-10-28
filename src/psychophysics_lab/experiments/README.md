# Researcher experiment files

The [Python-first philosophy](../../../docs/CODE_PHILOSOPHY_AND_CONTRIBUTIONS.md)
governs authoring: the experiment file defines scientific behaviour, the shared
framework executes it and the TUI provides generic configuration and inspection.
All ten active official experiments use flat chronological `trial_events()`
and a once-only SPACE readiness / 1,000 ms settling fixation. Write
`SESSION_START=[]` to disable the opening. Existing external sources are not
rewritten. See the [Stage C evidence](../../../docs/STAGE_C_EVENT_FIRST.md).

## Read every official experiment in this order

1. **PARAMETERS:** declared ConfigFields, response meanings, stimulus identities
   and selected defaults. Settings passed by Configure override these defaults.
2. **SESSION START — ONCE:** edit the key, settling duration or entire list here.
   The session-only ready slot contains fixation, without a task probe.
3. **TRIAL EVENTS — REPEATED:** the flat `trial_events(settings, condition)`
   list gives the actual display order, durations, response and optional cues.
   `prepare_stimuli` maps the current condition and strength to renderer parameters.
4. **SCIENTIFIC RULES — CONDITIONS AND UPDATES:** condition construction,
   randomisation, correctness and the response-dependent next stimulus.
5. **STOPPING AND RESULTS:** completion, safety ceiling, recording, result
   calculations and the procedure. Finite teaching tasks do not acquire a
   scientific threshold merely because an adaptive method is selected.
6. **FRAMEWORK REGISTRATION — MINIMAL AND LAST:** `SPEC` and compatibility
   connection. A new supported experiment requires no TUI source change.

Start with `orientation_task.py` for a finite teaching task,
`contrast_sensitivity.py` for interleaved reversal-completion staircases and
`ellipse_major_axis.py` for two temporal intervals. The two line-position
experiments share a spatial question but retain their distinct geometry.
`ellipse_centre.py` is another two-interval geometry.

`contrast_sensitivity_windowed.py` explicitly declares its circular-windowed
grating and event order. Its named shared CSF functions deliberately reuse
condition selection, adaptation and estimation; its local envelope parameters
and distinct experiment ID remain visible. Follow those named scientific
functions only when studying the shared mathematics.

## One event definition and one execution path

```python
def fixation_events(settings):
    return [Show("fixation", slot="fixation", duration="fixation_ms")]

def trial_events(settings, condition):
    return fixation_events(settings) + [
        Show("target", slot="target", duration="stimulus_ms",
             beep=Beep(550, 35)),
        CollectResponse(actions=("left", "right"), slot="fixation",
                        beep=Beep(750, 35)),
    ]
```

This is an authoring illustration, not a new default cue or protocol. Preserve
each study's actual timing, cue and response meanings. Spatial 2AFC, binary
single-interval judgments and first/second **2IFC** are different designs; two
keys do not imply two stimulus intervals. See
[psychophysical terminology](../../../docs/PSYCHOPHYSICS_METHODS_AND_TERMINOLOGY.md).

Shared-method procedures call
`run_contrast_experiment(trial_events=trial_events, ...)`; direct procedures
pass the list to `run.trial()`. The latest scientific state determines the
effective parameters immediately before each trial. Interpretation and update
occur explicitly inside the recording boundary; leaving it saves once.
Do not perform file access or scientific updates during timed displays.

Acquisition, simulation and Review inspect the same factory. Older
`make_trial=...`/TrialTimeline experiments remain supported. Migrated files
retain `make_trial = legacy_trial_factory(trial_events)` for older callers;
the central adapter wraps the same list.

## Scientific methods, settings and results

All ten official experiments support adaptive and constant-stimuli methods.
`orientation_task`, `probe_above_below` and `example_experiment` also retain
their original mode. Method choice uses the existing public
`psychophysics_lab.methods.contrast` components. Conditions, strength units,
display mapping, correctness and estimator remain experiment-owned.

Digital peak-to-peak grating modulation, probe increment and absolute line
intensity are distinct quantities. None establishes measured optical contrast.
Constant-stimuli schedules save observed performance; a fitted psychometric
threshold requires a separately justified analysis. A safety ceiling does not
turn an incomplete staircase into a valid threshold.

ConfigField declarations should state useful units, bounds and help text.
Run-selected settings must affect presentation and saved scientific metadata.
Library appearance parameters belong in `../stimulus_library.py` or a selected
preset; do not hide duplicate constants later in the procedure. Optional JSON
presets supply values through the same configuration route.

## Retired former published experiment

`new_probe_vertical_line_stimulus` is a retired researcher-created experiment,
not one of the ten official experiments. Its Python source was already absent;
its stale `ready` entry was removed from `authoring/components.json` on
28 October 2026. It must not be discovered, imported, or treated as software
Ready. Retirement removes only the obsolete active publication record; it does
not delete or rewrite archived acquisition records.

The historical `configs/experiments/new_probe_vertical_line_stimulus.json`
remains in place for interpreting older settings. The separately named
`new_probe_vertical_line` stimulus is **not** this retired experiment and is
not retired by this change. If a laboratory wants a similar experiment,
author it as a new, uniquely identified external extension and follow the
normal Test → Ready process; do not silently resurrect the retired ID.

**Deleting or retiring an experiment today:** ordinary unlisted Python
experiment definitions are discovered from their Python source; removing a
definition removes it from fresh discovery. Older published researcher
experiments can also have an explicit entry in
`authoring/components.json`. When deliberately removing one of those sources,
the same reviewed commit must retire its publication entry; otherwise PsyCoLab
will correctly warn that a formerly Ready experiment is missing. That warning
must **not** be silently suppressed: the missing file could also be an accidental
or incomplete installation. Keep historical run records and configuration
files rather than deleting them as part of source retirement.

Independent laboratory extensions use a separate, machine-local readiness
record and an explicitly trusted external folder. Their lifecycle is distinct
from this repository's published inventory. A single researcher-facing
Retire/Remove action, which handles relevant active registration without
deleting acquisition records, is proposed as a future usability improvement;
it is **not** implemented by this retirement.

## Ownership, compatibility and records

Official files are curated reference protocols. Develop new studies as uniquely
identified [laboratory extensions](../../../docs/LABORATORY_EXTENSIONS.md);
promotion is deliberate and reviewed. The
[bundled starters](../../../examples/laboratory_extensions/METHODS.md) demonstrate
composition, cues and the existing Test/Ready workflow.

Only researcher experiment definitions, this README and the required
`__init__.py` belong at the public directory level. `_internal/` holds discovery
and saved-design compatibility, not a second authoring route. Current official
IDs match filenames, including `contrast_sensitivity`. Historical run identity
comes from saved provenance; do not infer a past protocol from today's source.

Canonical response rows and trial journals preserve accepted input and partial
events independently at trial boundaries. Compatible aggregate histories are
written on finalisation; interrupted journal readers report truncation.
`trial_column_overrides` saves the protocol-specific meaning of existing columns
with each run. Existing participant records are never rewritten by authoring.

Cropping, zero-strength catches and off-centre stimuli may be intentional.
Inspect all relevant conditions. Review sampling warnings aid design; physical
presentation and participant acquisition retain their actual display,
calibration and protocol qualification checks. Software tests establish no
physical photometric, temporal or audio qualification.
