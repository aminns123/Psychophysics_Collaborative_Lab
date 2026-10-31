# Established compatibility examples

New learners: use the [three progressive lessons](LESSONS.md) first.
The two older worked examples below are retained unchanged for existing labs;
they are supplementary, not a competing authoring standard.

# Two established executable examples

## Begin with the simple left/right experiment

`experiments/demolab__left_right.py` and `experiments/demolab__line_strength.py`
use the approved [A1/A2/B standard](../../docs/EXPERIMENT_AUTHORING_STANDARD.md):
**A1 experimental choices**, **A2 scientific methods**, then **B framework
integration**. A1 is the normal starting point; changes to scientific methods
in A2 need deliberate validation. B connects existing execution and recording.
There is one Python file per study and no generator or new framework.

The basic example's `FIELDS` supplies declared defaults to generic Review
editing (and universal run controls in Configure); the unchanged companion
`presets/left_right.json` supplies its initial selected values. The target slot
selects `demolab__line` from this folder's `stimulus_library.py`.

Read `SESSION_START`: SPACE readiness on a pure fixation cross, followed by
1,000 ms settling, once before Trial 1. In A1 edit those literals directly or use
`SESSION_START=[]`. Configure fields are optional. Escape aborts safely; the
ready key is never an answer.

`fixation_events(settings)` returns an ordinary one-element list.
`trial_events(settings, condition)` composes it with `+`: fixation → observation
marker → line → blank → left/right response → observation marker. Edit the
duration field names or event order in this file. To request an onset cue,
replace `beep=None` on Show with `beep=Beep(550, 35)`; on CollectResponse use
`beep=Beep(750, 35)` for an accepted scientific answer. Both are silent by default.
These are software cue requests, not measured acoustic onset guarantees.

A1 declares `trial_measurements(settings, condition)` and units beside it: requested
`line_offset_deg` (degrees) is saved in the existing journal; the canonical 20
columns and correct-answer state observations retain their meanings.

The response alternatives and F/J keys are in `RESPONSES`; `interpret_response`
checks target/response equality. `choose_condition` places the line left/right.
`update_from_response` increments the correct-answer count once.
`is_finished` stops at the configured accepted-trial count, and
`finish_experiment` completes canonical recording. There is no hidden adaptation
or threshold estimator in this basic example.

## Add an explicit strength method

`experiments/demolab__line_strength.py` is a complete opt-in example using the
installed `LinePatch`, `TeachingAdaptiveMethod`, `ConstantContrastMethod`,
`fixed_level_schedule`, timeline and canonical runner. It vendors no engine.
Its conditions are 1° and 2° eccentricity. Strength is a **digital increment**
above grey 0.5, with line intensity `0.5 + strength`, bounded to [0, 0.5].
This is a short discrimination demonstration, not a luminance threshold study.

Copy this folder to a separate laboratory source location and explicitly enable
that trusted folder in PsyCoLab. Existing folders are never overwritten. Select
`demolab__line_strength`, Test it, then mark the tested revision Ready. Choose
Adaptive for the finite n-down/n-up demonstration, or Constant stimuli for
preselected levels. The default fixed plan has two eccentricities × three levels
× five presentations = 30 responses. Targets are binary left/right, balanced
within each condition/level to within one for odd repetitions. A different
response paradigm needs its own planner. Zero increment is an intentional catch.

A1 in the strength example declares fixed-mode journal observations
`fixed_repeat` (presentation within an eccentricity/increment cell) and
`presented_display_contrast` (digital increment, not optical contrast).
`trial_measurements` forwards exactly those existing measurements. Adaptive
mode keeps the installed method's state/history, not fictitious fixed repeats.
No trial column or scientific result is renamed or invented.

Review shows the selected method, one representative stimulus, timings, strength
mapping and planned count. Full schedule, seed, actual strengths and conditions
are saved through existing resolved metadata and the unchanged 20-column TSV.
Fixed runs leave staircase-only values blank and report observed accuracy;
psychometric fitting is a separate scientific decision.

Tested/Ready fingerprints include the imported framework methods, adaptive
engine, renderer and recording path. Updating those scientific dependencies
returns an unchanged local experiment to Draft and requires retesting; it does
not edit the laboratory source or historical runs. Saved run source inventories
and extension fingerprints retain provenance. These APIs are available on this
development baseline; pin its commit pending a separately approved versioned
release. Earlier tags may not export these APIs. Do not copy engines to work
around an older installation: use a compatible pinned framework.

Headless synthetic checks validate this example. Actual display geometry,
photometry and timing require the laboratory's separate physical evidence.

The strength example's `trial_events` shows fixation → line → left/right answer.
`choose_condition` supplies the current strength; `prepare_stimuli` maps it to
`0.5 + strength`. The imported `TeachingAdaptiveMethod` applies the selected
n-down/n-up counters and multiplicative down/up factors to produce the **next**
strength after each accepted answer. The finite adaptive run stops at
`trial_count`, while the constant-stimuli run exhausts its condition/level/
repetition schedule. Sharing this named method avoids copying a second engine.

## Run and validate a trusted local copy

From the framework checkout on Windows, enable your reviewed copy explicitly:

```powershell
.\.venv\Scripts\python.exe -m psychophysics_lab --extensions-enable "C:\your-lab\my-experiments" --trust-extension-code
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-preview demolab__line
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready stimulus demolab__line
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-test demolab__left_right
.\.venv\Scripts\python.exe -m psychophysics_lab --dev-ready experiment demolab__left_right
```

The custom stimulus and experiment each need their own software Ready evidence.
Test uses the real simulation/validator path and reports its disposable synthetic
run folder. To recheck a saved run without modifying it:

```powershell
.\.venv\Scripts\python.exe scripts\validate_run.py "C:\path\to\reported\run_folder"
```

Select the Ready experiment through the normal TUI, Configure, Review and
Simulate responses, or use Try the experiment for the existing physical-test
path. Testing `demolab__line_strength` uses the same `--dev-test` and
`--dev-ready experiment` commands with its ID; its LinePatch is built in.
Changing source/dependencies returns affected components to Draft under the
existing fingerprint rules. Existing installed folders are never overwritten,
and no template update automatically enables trust, publishes an extension or
changes participant records. Give a new study a unique namespace and ID before
developing its scientific variation; no TUI source edit is required.

## Safe editing map

| Task | Edit / inspect | Validate afterward |
|---|---|---|
| Change conditions | A1 eccentricity field; A2 schedule/selection | Values, order, fixed count and seeded schedule |
| Change alternatives or placement | A1 response mapping/events; A2 signed offset | Both target meanings, correctness and rendered geometry |
| Change timings/audio | A1 fields and flat event list | Event order, actual software presentation and cancellation |
| Change saved measurements | A1 names/units/function; existing B projection | Finite values, journal, canonical reader and Review |
| Change adaptive/stopping rule | A2 named shared method and selected fields | Accepted-response traces, bounds and incomplete runs |

For your own study, change the namespace in `psycolab_extension.json`, each SPEC
ID, matching experiment filename and source_paths, custom stimulus ID/default,
and preset experiment/stimulus IDs together. Never reuse an official identity.
Existing laboratory folders are not upgraded or overwritten by this example PR.
Custom stimuli remain ordinary classes in local `stimulus_library.py` using the
same public interface; no core TUI or registry edits are necessary.
