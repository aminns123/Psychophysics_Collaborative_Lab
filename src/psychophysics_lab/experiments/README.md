# Researcher experiment files

Edit one experiment here and its stimulus class in `../stimulus_library.py`.
Experiments share section order, units and response conventions. They may use
different scientifically justified loops. Purpose and `PARADIGM` identify the participant's two alternatives:
spatial/property 2AFC, or first/second interval (two-interval forced choice,
also called 2AFTC here).

## Read every file in this order

1. **Settings and stimuli:** `FIELDS`, `RESPONSES`, stimulus slots/defaults and
   `PARADIGM`. All *researcher-adjustable experiment parameters* should be
   declared here as `ConfigField` values with meaningful names, units, bounds
   where physically or numerically necessary, and `help_text` for ambiguity.
   The TUI supplies the selected values; this section gives defaults. The
   selected values must be read from `run.values` (or `settings` inside
   `make_trial` / `make_conditions`), not from frozen defaults further down.
   Geometric relationships defining the task (e.g. a probe at its ellipse
   centre or a target sign corresponding to the response alternatives) may
   remain equations/invariants; explain them near the setting declarations.
2. **Conditions and order:** `make_conditions(settings)` returns named condition
   dictionaries; `choose_condition(run, conditions, state)` selects one and sets
   its `target` (correct alternative index) and `value` (condition saved in data).
3. **Prepare stimuli:** `prepare_stimuli(run, condition, state)` always returns
   a dictionary of validated stimulus parameters by slot, never a bare coordinate
   or Scene object. Conditions carry scientifically named coordinates/quantities.
4. **One trial:** `make_trial(settings, condition)` returns the chronological
   displays, interval gaps, optional sounds and response collection. Observation
   markers may appear here; scientific updates may not. Both intervals remain
   explicit in a temporal task.
5. **Responses and adaptation:** `interpret_response(condition, response)` states
   correctness; `update_experiment(run, condition, state, response, trial)` performs
   the scientific update once and returns state. `trial_record()` declares named
   measurements and canonical data fields. No file-writing code belongs here.
6. **Run and finish:** setup, a Boolean stopping rule, the point estimator where
   applicable, and a procedure that follows the scientific design.
7. **Framework connection:** validation and `SPEC = definition()` connect these
   scientific functions to the TUI and shared machinery.

`condition` describes this trial. `state` holds quantities that persist across
trials, including adaptive counters/engines. The open `trial` exposes an immutable
accepted response and trial state, and applies declared nonvisual updates.

```python
def procedure(run):
    conditions = make_conditions(run.values)
    state = initialise_experiment(run, conditions)
    while not is_finished(run, conditions, state):
        condition = choose_condition(run, conditions, state)
        stimuli = prepare_stimuli(run, condition, state)
        with run.trial(
            make_trial(run.values, condition),
            target=condition["target"], condition=condition["value"],
            parameters_by_slot=stimuli, **trial_record(run, condition, state),
        ) as trial:
            response = interpret_response(condition, trial.response)
            state = update_experiment(run, condition, state, response, trial)
    finish_experiment(run, conditions, state)
```

Entering `run.trial()` presents the trial using the existing renderer and collects
one response. Interpretation and update are explicit calls inside the boundary;
leaving it saves once. An exception preserves accepted input, partial events and
state, and marks the run interrupted/failed. A failed adaptive update remains
incomplete rather than being invented to make counts agree. Do not perform file
access in an update callback. The compatibility `play_trial()` API still exists
for internal/older action plans. The example above is an adaptive pattern; a
fixed-trial procedure can use a for loop and omit an adaptive update.

Start with `orientation_task.py` for fixed trials, `contrast_sensitivity.py`
for interleaved staircases, and `ellipse_major_axis.py` for two explicit temporal
intervals. `line_position_baseline.py` and `line_position_flanker.py` show the
matched spatial task; `ellipse_centre.py` shows a different temporal geometry.
The scientific specification and declared primary estimator state what a result
means. A safety ceiling does not make incomplete staircases adequate.
Historical reconstructions live under `_internal/historical/`, preserve their
quirks for explicit replay and are absent from normal menus.
The edited custom probe retains its existing Draft/Test/Ready gate.

`_internal/` holds discovery, declaration validation, source-name compatibility and
historical design loading. Researchers do not edit it to add experiments.
`__init__.py` is the required package entry point and contains no experiment science.

## Editing scientific parameters consistently

- **Experiment choices** such as condition positions, CSF grating eccentricity
  and envelope width, ellipse ring radius/vertical centre, trial durations,
  staircase settings and sound cues belong in the experiment's leading
  `FIELDS` section. They must be reflected by the rendered timeline,
  canonical trial measurements and scientific run summary.
- **Stimulus appearance** such as the line's drawn width, grating phase or
  Gabor diameter belongs in that stimulus's `PARAMETERS` in
  `stimulus_library.py`; edit the stimulus class/preset, not a duplicate
  experimental constant. The experiment can use a named field to vary an
  appearance choice specifically for that study.
- **Shared algorithms and coordinate conventions** belong in the shared
  engine. For example, above/below uses the sign of a positive displacement;
  a probe at the centre of an ellipse tracks that ellipse's centre. Do not
  expose literal alternative indices or zero coordinate origins as misleading
  "scientific settings".
- Some examples use an authoritative `default_config` JSON that supplies
  initial `values`. Keep declared Python fields, JSON keys, their defaults
  and units coherent. Other JSON designs in `configs/experiment_designs/`
  may be *historical compatibility inputs*, not the active Python protocol.
- Regression tests should vary each editable field and test the *chosen*
  value, not freeze a specific default (except a compatibility/default
  round-trip test). Qualifying physical geometry, luminance and timing remains
  a separate laboratory task.

## Contrast sensitivity naming

The public file and menu name are Contrast Sensitivity. Its established saved-run
ID `csf_thesis` is retained internally: the older ID `contrast_sensitivity` already
means a scientifically different historical shader protocol. The internal
`source_names.py` migration map prevents either kind of saved run from being
silently reinterpreted. New experiment files still match their own IDs normally.


Required study choices remain blank in setup until selected. Adaptive n-up/down,
step sizes, reversal counts and retention come from TUI values, never hidden
historical constants. Shared staircase state, primary analysis and display
services have documented reasons in `docs/SCIENTIFIC_REDESIGN.md`. Scientific
stimuli preserve floating commands through texture upload; output precision and
optical timing still require physical qualification before acquisition.


The shared run context handles physical-test versus participant-acquisition policy
at initialisation. Do not add a blanket non-synthetic guard: physical testing uses
the real display and is intentionally distinct from participant acquisition.
Shared recording helpers shorten repeated projections; the scientific strength,
steps, gamut and measurements remain explicit at the experiment's call site.
See `docs/RESEARCHER_TEST_WORKFLOW.md` for these narrowly shared responsibilities.

## Reading and recording without more framework code

To understand a task quickly, start with `make_trial()` and `prepare_stimuli()`,
then its response/update functions and finish rule. Settings and framework
declarations can stay folded in your editor until you need them. Keep equations,
conditions, optional cues and the primary estimate in this file. A fixed-trial
task needs no dummy adaptation function. The NumPy grids supplied to a stimulus
renderer support named masks and equations; see the short learning guide.

`trial_column_overrides` documents protocol-specific meanings in the existing
saved-data dictionary. For example, `digital_probe_increment` and
`digital_peak_to_peak` must not inherit the historical C_disp definition. New
runs save the declarations with the run, so later source edits cannot silently
change their data definitions. Existing data files are never rewritten.

At each trial boundary, canonical responses and `trial_events.jsonl` are saved
independently. Each journal line contains the actual trial, response/partial
events, presentation record and adaptive updates. Compatible aggregate JSON
histories are produced once during finalisation, including ordinary aborts and
errors. This avoids repeatedly rewriting all earlier trials. If the process is
killed, the durable journal remains even when aggregate files are absent. The
reader `data.session.read_json_records` yields complete lines and explicitly
reports an incomplete final line; it does not conceal a truncated write.

Cropping, blank/control trials and off-centre stimuli are intentional design
choices, not automatically corrected or prohibited. Inspect all relevant
conditions. Display sampling limitations are shown at Review without blocking
design or simulation; physical presentation still checks the actual display.
