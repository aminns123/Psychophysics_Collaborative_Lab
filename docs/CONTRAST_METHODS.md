# Contrast selection methods — universal researcher API

**Goal:** every official and laboratory-owned experiment can select either
an adaptive strategy or the method of constant stimuli without copying
staircase algorithms or duplicating trial acquisition and saved-data logic.

This describes the shared API. PR #135 integrated CSF, draft PR #137 adds
line-position/flanker/ellipse studies, and draft PR #138 adds the four
orientation/teaching studies. The last two PRs are **not merged or scientifically
accepted until their CI and Windows TUI/simulation checks pass**.
A new local experiment can use the same public strategies after declaring its
actual digital strength units, valid ranges and trial interpretation.

## Researcher-facing architecture

1. **Experiment file:** parameter fields, scientific conditions and their units,
   stimulus slots/parameters, timeline, response interpretation, strength
   convention, eligible range and expected primary analysis.
2. **Method factory:** choose an available policy by TUI `contrast_method`.
   `AdaptiveContrastMethod` delegates to the experiment's existing tested
   staircase functions. `ConstantContrastMethod` owns seeded fixed-level
   scheduling, progress, and simple descriptive accuracy.
3. **Shared runner:** `run_contrast_experiment()` executes one trial loop,
   presenting the experiment-defined timeline and recording accepted responses
   through `RunContext.trial()`.
4. **Renderer:** uses the strength in the experiment's own digital-command
   equation. No universal equation converts grating modulation, an increment
   above background, and absolute line intensity.
5. **Data:** `trials.tsv` retains its **20-column schema v1** for both methods.
   Constant-stimuli runs have no staircase reversals/thresholds. The selected
   method, fixed levels, seed, full schedule and observed accuracy belong in
   resolved run metadata. Adaptive primary estimates remain method-specific.

## Public API

`from psychophysics_lab.methods.contrast import (`
`    run_contrast_experiment, AdaptiveContrastMethod,`
`    ConstantContrastMethod, fixed_level_schedule, parse_fixed_strengths,`
`)`

An official or local study declares small strategy factories and then one
procedure; its normal scientific callbacks remain next to their equations:

```python
def adaptive_method(run):
    return AdaptiveContrastMethod(
        run,
        make_conditions=make_conditions,
        initialise=initialise_experiment,
        select=choose_condition,
        record=trial_record,
        update=update_experiment,
        finished=is_finished,
        finish=finish_experiment,
    )

def fixed_method(run):
    # First define UNIQUE scientific conditions, not staircase replicas.
    # The method does not determine what a condition (position/ratio/etc.) means.
    conditions = [{"value": 2.0, "frequency_cpd": 2.0},
                  {"value": 4.0, "frequency_cpd": 4.0}]
    background = run.values["background_intensity"]
    maximum = 2 * min(background, 1 - background)  # CSF ONLY
    levels = parse_fixed_strengths(run.values["fixed_contrasts"],
                                   minimum=0, maximum=maximum)
    schedule = fixed_level_schedule(
        conditions, levels, run.values["fixed_repetitions"], seed=run.seed,
        condition_field="frequency_cpd", strength_field="contrast",
    )
    # Researcher validates count, geometry, intensity headroom, and every
    # condition/target pair before constructing the method or acquiring data.
    if len(schedule) > run.values["max_trials"]:
        raise ValueError("Increase the explicit trial ceiling or reduce levels.")
    return ConstantContrastMethod(
        run, schedule=schedule, resolution={
            "trial_selection_method": "constant_stimuli",
            "planned_trials": len(schedule),  # also save seed, full plan, units
        },
        record=fixed_trial_record,
    )

def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )
```

Above is a *wiring example*, not a complete executable new experiment;
`contrast_sensitivity.py` is the actual complete reference. The public
`ContrastMethod` protocol is intentionally small: `is_finished`,
`next_trial()`, `trial_record(selection)`,
`accept_response(selection, response, trial)`, and `complete()`.

### Why the method is not just `contrast = function(...)`

The selection must remember state. Adaptive procedures need independent
staircase identities, response streaks, reversals and completion. Constant
stimuli must remember a deterministic schedule, target balance, accepted
responses and planned completion. This state belongs to the selected method,
not to duplicate experiment code.

### What every experiment must declare

- The scientifically controlled *quantity* (e.g. digital peak-to-peak grating
  modulation, digital probe increment above background, absolute pixel
  intensity); units, bounds and associated display conversion.
- Unique conditions **before** method selection. For adaptive methods,
  independent staircase replicas can then be created from those conditions.
  For fixed methods, each condition × strength level × repetition produces
  scheduled trials with seeded target balancing.
- A condition's correct alternative and the original trial timeline. For
  multi-interval or orientation studies, retain their real trial structure.
- A robust visible-pixel/headroom check that is applied to the chosen method
  and **all** prospective conditions/strengths, rather than only a random
  preview trial.
- Method-appropriate analysis and provenance. A fixed-level psychometric
  threshold requires a separately validated fit, not a staircase estimator.

## Inventory of registered official studies

| Study | Current behaviour | Required controlled quantity for dual-method adoption |
| --- | --- | --- |
| `contrast_sensitivity` | Both methods, first shared-API adopter | Digital peak-to-peak modulation (not measured optical contrast) |
| `line_position_baseline`, `line_position_flanker` | Adaptive only | Probe digital increment above local background, including overlap headroom |
| `ellipse_centre`, `ellipse_major_axis` | Adaptive only | Probe digital increment; preserve interval/ring geometry and local overlap limits |
| `orientation_adaptive` | Adaptive teaching procedure | Teaching-Gabor digital modulation; preserve its finite-trial update rule |
| `orientation_task` | Fixed-trial teaching procedure | Teaching-Gabor digital modulation; needs scientifically declared adaptive rule |
| `probe_above_below` | Fixed-trial teaching procedure | Vertical-line intensity relative to its 0.5 digital background |
| `example_experiment` | Fixed-trial teaching procedure | Line digital intensity relative to its 0.5 digital background |

Note: `line_position_flanker` differs from baseline in scene composition.
Do not use a global `1-background` cap as a replacement for its local
probe-overlap validation. Similarly, an absolute brightness is *not*
automatically the same quantity as a digital increment.

## The reusable family adapters

- **Grating CSF:** `contrast_sensitivity.py` is the first full reference.
  Its selected value is digital peak-to-peak grating modulation.
- **DetectionScene probes:** import `probe_contrast_fields()`,
  `probe_constant_method()`, `make_probe_fixed_schedule()` and
  `validate_probe_fixed_settings()` from `methods.probe`.
  Conditions and target positions remain in the experiment. The probe
  *increment* must pass the real pixel-composition headroom test for both
  targets. See `line_position_baseline.py` and `ellipse_major_axis.py`.
- **Gabor and bright-line teaching:** import
  `teaching_method_fields()`, `constant_teaching_method()`,
  `OriginalTeachingMethod` and `TeachingAdaptiveMethod` from
  `methods.teaching`. Gabor modulation and bright-line increments have
  different digital ranges. The original fixed-count teaching code stays
  selectable as **Original experiment** (the unchanged default).
  The optional teaching adaptive mode stops after the selected accepted
  responses and claims no threshold; a genuine threshold protocol must
  be separately declared and validated.

For every study, the common experiment procedure should be small:

```python
def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_method(run),
            "constant_stimuli": lambda: fixed_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )
```

Some teaching examples include an additional `original` factory to preserve
their exact old finite-trial protocol. Experiments with target-dependent
geometry may supply `prepare_selection` to the runner: it enriches the
selected trial object **in place** with physical positions while preserving
method identity and condition scheduling.

**Local experiment template principle:** import these public helpers; do not
copy the staircase algorithm, fixed-level schedule, data-writer or main run
loop. Keep scientific condition creation, physical display mapping, response
interpretation, timing and calibration restrictions readable in your own
experiment file. Prefer a small declared `method_planner` (and optional
`method_reviewer`) on the `ExperimentSpec` so the generic TUI/Review can
show active method settings without hardcoded experiment IDs.

### Canonical local data is unchanged

Both methods use the same local external data root, experiment folders,
manifest and **existing schema-v1 20-column `trials.tsv`**. With fixed
strengths, write actual `presented_display_contrast` in the scientifically
declared digital units. `staircase_id`, reversal fields,
`next_display_contrast`, etc. remain present as **empty/not applicable**
columns. Do **not** delete columns or invent a staircase estimate. Record
the method, full seeded trial plan, displayed/intensity convention and
per-level counts and accuracy in `resolved_experiment.json`.

## Compatibility and acceptance

- New fields and method selection must be **opt in**, preserving every
  experiment's existing default, records and deterministic adaptive output.
- Do not create or requalify lab-specific extension experiments automatically.
- Before claiming **universal support**, connect each study above and verify
  configuration → Review → simulation → native Try → saved data, across
  both methods and method switching. Keep the original scientific
  calculation for each existing protocol.
- `methods/contrast.py` deliberately does not depend on CSF, experiments
  registry, Textual, pyglet/OpenGL or a particular monitor.
