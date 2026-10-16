# PsyCoLab: build stimuli, then arrange an experiment

**Status:** Incremental public API for ordered *static* phases. New orientation
examples execute through the shared sequence runner. The reference CSF describes
its five phases through the same JSON contract and translates them to its existing
Pyglet/adaptive trial objects; it **does not** yet use the new static presenter.
This protects previously validated CSF timing, contrast, adaptive and data semantics.

## Mental model

```text
Stimulus Python (`render`, parameter declarations)
    + stimulus preset JSON (`configs/stimuli/`)
    ↓
Experiment Python (conditions, response actions, adaptive updates)
    + timeline JSON (`configs/experiments/`)
    ↓
Framework: monitor preflight → display → timed phases → key response
    ↓
One accepted trial in canonical trials.tsv
    + trial_presentations.json (per-phase settings/times/extra observations)
    + procedure_lifecycle.json + immutable parameter snapshots
    ↓
Experiment updates next contrast / orientation / condition and repeats
```

A **stimulus** determines what the screen looks like; an **experiment** determines
what, when, what a response means, and what changes before the next trial. An
**adaptive algorithm** supplies a state update; the experiment decides which
parameter receives that update. The framework saves standard trial outcomes.

## Beginner recipe (Python 3.11)

1. Open **Build Stimuli** from the TUI. Inspect a stimulus's raw Python. Give a
   new lowercase name and select **Build new stimulus**, which safely creates
   `src/psychophysics_lab/stimuli/NAME.py` and `configs/stimuli/NAME.json`.
   Edit scientific geometry, parameter declarations and JSON preset. Register
   the module explicitly in `src/psychophysics_lab/contributions.py`, restart.
2. Open **Build Experiments**. Inspect Orientation Task (procedure) and **Trial
   timeline JSON**. Select **Build new experiment** and enter a lowercase name.
   The template creates `experiments/NAME.py` and `configs/experiments/NAME.json`.
   Register its module in `contributions.py` and restart. Registration remains
   explicit so unreviewed files are never silently executed.
3. In your experiment Python, specify experimental conditions and order; call
   `run.initialise(expected_trials=..., resolution={...})`. Load the timeline
   with `load_timeline(path, timings=run.values, slots=run.stimulus_snapshots)`.
4. Loop through conditions. Compute parameters for that trial using
   `run.stimulus_parameters(slot, **changes)`, then call:

   ```python
   correct = run.play_trial(timeline, target=0, condition="example",
       parameters_by_slot={"target": parameters},
       measurements={"eccentricity_deg": 0.5})
   # Optionally run.update_adaptive(...), updating next trial's parameters.
   ```

   `play_trial` automatically records the accepted response, correctness, key,
   stimulus identity, complete sequence and software/virtual timing. Custom
   scalar observations go into the versioned `trial_presentations.json`, **not**
   undocumented columns in canonical `trials.tsv`. Use names/units described in
   your experiment declaration or `resolution` so the measurements are interpretable.
5. Call `run.complete()` only after all expected accepted trials. Simulate from
   the TUI before hardware work; run `python scripts/validate_run.py RUN_DIR`.
   For a human test, use the appropriate physical verification checks.

## Timeline JSON

Example `configs/experiments/orientation_task.json`:

```json
{
  "schema_version": 1,
  "phases": [
    {"name": "fixation", "kind": "show", "slot": null,
     "duration_ms": {"field": "fixation_ms"}, "instructions": "+"},
    {"name": "target", "kind": "show", "slot": "target",
     "duration_ms": {"field": "stimulus_ms"}},
    {"name": "interval", "kind": "show", "slot": null,
     "duration_ms": {"field": "interval_ms"}},
    {"name": "answer", "kind": "response", "slot": null,
     "duration_ms": {"field": "response_timeout_ms"}}
  ]
}
```

- Phases execute **in the order written**. A timed `show` requires a positive
  integer in milliseconds. An `answer`/`response` phase **must be last**, with
  a positive timeout or `0` to wait indefinitely. Zero-duration keyless phases
  are rejected. Each phase has a unique name.
- A non-null `slot` refers to a declared experiment stimulus slot and its
  validated JSON preset. `null` represents a blank/instruction phase. Multiple
  slots may appear sequentially; simultaneous compositing is not yet part of
  the public static API.
- `{"field": "stimulus_ms"}` uses a validated `ConfigField` accessible in the
  TUI. An integer value in the JSON instead fixes that phase's duration.
- No Python code, conditions or expressions are executed from JSON. Any invalid
  phase, undeclared slot or unknown timing field produces a validation error.
- Response keys and their task meanings are declared with `ResponseParadigm`
  and can be configured in the TUI. Escape aborts. If a positive response
  timeout is exceeded, the procedure fails explicitly instead of silently
  inventing an accepted response.
- A trial's timeline is resolved anew per run; its resolved per-phase details
  and simulation schedule/software flip observations are saved with trial data.

## Existing CSF and scientific correctness

`configs/experiments/contrast_sensitivity.json` lists the **actual current CSF**
trial phases: fixation → new condition (blank) → grating → interval → response.
`Experiments/contrast_sensitivity_function.py` constructs the old scientifically
validated `Trials_read_write_staircase_conditions` objects from these phase
names, while keeping its existing OpenGL, response logger and adaptive state.
An additional leading fixation before the repeated trials is deliberately
retained for compatibility. `resolved_experiment.json` includes the resolved
phase plan. Timing fields `timeFixate`, `timeInterval`, `timeAB`, `timeT` remain
configurable through the TUI and checked by existing CSF validation.

**Do not assume scientific equivalence between a grayscale raster teaching
stimulus and the original contrast-calibrated/phase-sensitive CSF shader.** The
legacy CSF must remain executable without changing its interpretation, and its
photometer and timing checks remain mandatory for qualified human collection.

## Safety and known limitations

- Simulation validates parameter and timeline structure but does **not** wait
  for real durations and is not evidence of actual screen refresh/photon timing.
- New human presentation uses software flip/response event timestamps, not
  measured photon onset, timing certification or keyboard-latency correction.
  The time between frames, OS scheduling and vsync require independent on-site
  verification for scientific claims.
- This first public timeline API handles static grayscale images, blanks,
  sequential stimuli and one response at the end of each trial. Dynamic per-
  frame animation, flicker/SOA with sub-frame precision, simultaneous multi-
  stimulus compositing, early responses, multi-interval choices and complex
  branching still require **separate tested extensions**. Do not attempt to
  reproduce the old ellipse/flicker study with the simplified renderer yet.
- Do not edit private `core/runner.py`, `data/` or monitor calibration to add
  scientific components. Edit only scientific Python modules and JSON, and
  explicitly register new modules in `contributions.py`.

## Implementation plan, priorities and acceptance criteria

**Stage 1 — Included in this PR:** shared validated phase model, JSON examples,
public trial sequencing for the independent orientation example, saved phase
observations, TUI Build/Inspect entrypoints, generated source/JSON blueprint,
and a CSF phase adapter preserving the existing runner. The API accepts separate
scientific modules without changing the core registration engine.

**Stage 2 — After the teaching release:** independently measured/display-
qualified timing interface with frame indices, detected missed frames, timeout
and abort event traces; first-class multi-stimulus compositing; adaptive
condition/parameter update policies; automated checking of measurement units
and schema; automated registration workflow beyond the explicit contribution
allowlist; guided human ellipse/flicker experiment port using hardware tests.

**Stage 3 — After scientific parity tests:** replace CSF's remaining legacy
presentation adapter only if the shared runtime reproduces the old stimulus
geometry, frequencies, contrast mapping, staircases, trial termination and
saved scientific outcomes. Compare both pathways using golden fixtures and
on-site display measurements. Until this proof exists, retain the adapter.

### Review checklist

- [ ] New experiment: scaffold → edit stimulus/timeline JSON → register → TUI
      configure → simulate → run validator, without editing runner internals.
- [ ] Invalid or incomplete timeline fails before recording completed human data.
- [ ] Each completed trial stores stimulus parameters, intended phase durations,
      response and condition, and any declared extra measurements.
- [ ] Adaptive example changes the next trial after the previous response.
- [ ] CSF uses the same phase *description*, but its legacy renderer and
      scientific calibration/termination behaviour remain unchanged.
- [ ] Full Windows and Ubuntu automated tests pass on Python 3.11.
- [ ] Physical presentation, refresh, photometry and response latency are
      independently verified before teaching with human research data.
