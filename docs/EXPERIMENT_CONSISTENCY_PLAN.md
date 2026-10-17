# Experiment consistency: plan and acceptance contract

## File order

Purpose and forced-choice category, followed by seven sections: settings and
stimuli; conditions and order; stimulus preparation; one trial; responses and
updates; run and finish; framework connection. All scientifically meaningful
decisions remain in the experiment and selected stimulus class. TUI values are
authoritative for a run. Shared recording and execution stay internal.

## Identical function responsibilities

| Function | Input | Output / responsibility |
|---|---|---|
| `make_conditions(settings)` | Validated TUI settings | List of named condition dictionaries |
| `choose_condition(run, conditions, state)` | Run and experiment state | One condition dictionary with `target` and `value`; may add scientific fields |
| `prepare_stimuli(run, condition, state)` | Chosen condition and current state | Dictionary of validated stimulus parameters by registered slot |
| `make_trial(settings, condition)` | Settings and chosen condition | Chronological TrialTimeline: displays, response and observation markers; no scientific update actions |
| `interpret_response(condition, response)` | Condition and accepted response | Named response dictionary with explicit correctness |
| `update_experiment(run, condition, state, response, trial)` | Explicit interpretation and active trial | Apply scientific updates once; return current experiment state |
| `is_finished(run, conditions, state)` | Updated state | Boolean scientific stopping decision |
| `initialise_experiment(run, conditions)` | Conditions and run | Declare resolution, create adaptive engine and initial state |
| `trial_record(run, condition, state)` | Scientific trial values | Named measurements, initial trial state and canonical-column projections |
| `finish_experiment(run, conditions, state)` | Final state | Estimator, adaptive snapshots and correct completion status |

Each procedure has the same six visible steps. `run.trial(...)` presents using
the existing shared executor, then yields its accepted response. The experiment
calls interpretation and update explicitly inside that trial context. On exit,
the shared recorder flushes the canonical row, events and state exactly once.
Exceptions preserve accepted input and partial state. Post-response actions
retain the existing event format and order. No second renderer or response loop.

## Forced-choice categories

Spatial/property 2AFC: target identifies left/right, above/below or tilt sign.
Two-interval forced choice (the requested 2AFTC category): target identifies
first/second interval; both displays and their interval gap stay visible in
`make_trial`. Both categories use the same condition and response contracts.
Different scientific geometry, schedules and stopping rules remain explicit.

## CSF name and compatibility

Rename `contrast_sensitivity.py` to `contrast_sensitivity.py`, with display name
Contrast Sensitivity. Remove thesis-specific wording from normal run controls;
retain source attribution in documentation. Preserve its established `csf_thesis`
saved-run ID internally: the older `contrast_sensitivity` ID already identifies
a scientifically different historical shader protocol. Reassigning that ID
would silently reinterpret old data. An internal source-name map handles this
single migration; new experiments still match filename and ID normally.

## Verification and acceptance

Apply to all nine experiment files, including the managed custom probe. Keep
its readiness gate rather than publishing changed source automatically. Compare
frozen legacy canonical rows, phase/action traces and adaptive states; exercise
TUI-selected parameters and both response meanings. Add contract tests for
condition/parameter return types, callback-free visible trials, identical
function signatures and main-loop ordering. Test staged recording on success,
abort and update failure, with no writes during display execution. Run the full
suite and inspect representative spatial and temporal files side by side.
Human readability remains a separate acceptance exercise; tests verify the code
contract and scientific preservation, not researcher comprehension.


## Implementation and verification completed

- Applied the identical executable procedure and all helper contracts to all nine
  experiment files; the public CSF source is `contrast_sensitivity.py`.
- The contract tests compare actual procedure syntax trees, inspect exact function
  signatures, reject hidden updates in trial builders, and validate runtime slot
  parameters, response interpretation and update order for every experiment.
- Existing frozen historical phase/action traces, canonical rows and adaptive
  states still match. Spatial CSF timing, threshold estimation, both response
  meanings, TUI overrides and temporal interval ordering pass their checks.
- Staged execution retains the same renderer and recorder. Success, abort,
  invalid update and adaptive-update failure preserve accepted-input provenance;
  no recorder writes occur while the scientific trial boundary is open.
- Full suite: 986 passed. Final focused suite: 62 passed. Compilation, dependency
  consistency and patch formatting checks pass.
- The warnings report the edited custom probe's existing readiness fingerprint
  gate. It was exercised in isolation by tests without automatically publishing
  changed source. Physical acquisition blocks and readiness gates remain intact.
- No human readability study or physical display qualification is claimed.
