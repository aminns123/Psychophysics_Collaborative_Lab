# Public procedure contract

New `researcher.experiment(...)` procedures must declare `calibration_requirements`
using `geometry`, `luminance`, and/or `timing`. A nonvisual task may instead give
a nonempty scientific explanation in `calibration_not_applicable`. Also declare
`monitor_capabilities=("display_binding", "resolution")`, or explicitly `()`
when neither is applicable. Omitting these declarations is an authoring error.
Simulation validates the declarations but does not require physical verification.
The reference CSF path and its existing calibration policy are unchanged.

The procedure receives `RunContext`. Call, in order:

1. `run.initialise(expected_trials=N, resolution={...}, runtime_display={...})`.
   Supply resolved stimulus/task information. A human renderer supplies actual
   display information; simulation automatically records that no display was used.
2. Present each trial and collect a response. `run.synthetic` selects the
   experiment's seeded virtual response path; `run.seed` supplies its seed.
3. `run.record(stimulus_condition=..., target_alternative=...,
   participant_response=..., response_key=..., correct=...)` for each accepted
   response. Other canonical columns are optional; indices are assigned centrally.
4. `run.complete()` after exactly the planned number of responses. Returning
   early, recording outside the lifecycle, or completing an empty procedure fails.

Use `run.abort(reason)` for participant cancellation and `run.fail(reason)` for
failure. Both stop execution and preserve available records. Unexpected exceptions
also preserve diagnostics and are re-raised. Abort produces `aborted_by_user`;
failure produces `error`. Neither is successful scientific completion.

The runner writes `procedure_lifecycle.json`, canonical trials, immutable configuration
and source metadata, display/resolution information, and final status. Validate with
`python scripts/validate_run.py PATH_TO_RUN`. PASS describes internal consistency,
including a consistently recorded abort; inspect the manifest status for completion.
Physical laboratory qualification remains separate.
