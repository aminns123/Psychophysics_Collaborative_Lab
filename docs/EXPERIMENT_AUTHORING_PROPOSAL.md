# Proposed contributor workflow after pipeline acceptance

Historical proposal: the implemented beginner API and exercises are documented in
[TEACHING_GUIDE.md](TEACHING_GUIDE.md). This page is retained as design history.

This is a proposal, not a new builder implementation. Resolve the audit's physical contrast, feedback/timing and laboratory-qualification decisions first.

1. Start from the existing scaffold; keep one stimulus module and one procedure module. Use `StimulusSpec` for identity/source and extend it in a future reviewed change with unit declarations, parameter validation and optional pure preview hooks.
2. Select a registered stimulus or define an experiment-owned one. Separate digital command parameters from physical luminance evidence. Declare editable units and allowable ranges explicitly.
3. Use `ExperimentSpec/ConfigField` to define condition count/list, units, timing and monitor requirements. Keep resolved physical values in the run snapshot, not duplicated TUI geometry fields.
4. Declare a response paradigm independently of the adaptive algorithm. Select a registered algorithm in the specification and expose only that experiment's allowed controls. An algorithm needing different observations should supply its own adapter/model; do not force CSF correctness into it.
5. Compose a `procedure(RunContext)` that owns presentation, accepted responses and completion. Strengthen this bridge later with explicit lifecycle/error/renderer hooks rather than requiring authors to learn four historical file paths.
6. Supply pure geometry previews and an optional real GPU preview; label which transformations are computed and which are physically measured. A preview is not calibration.
7. Add a separate observer/model and evaluator under simulations plus reproducible seed scenarios. Run the shared configure/record/analyse path; require expected failures and short/censored-run checks.
8. Review display readiness and snapshot/hash. Allow software simulation before qualification. Permit controlled human launch only after the experiment's lab-defined requirements and timing/contrast decisions are met.
9. Save source/stimulus versions, resolved units, observer parameters and derivation provenance with each new run. Keep independent reanalysis versions; never rewrite historical raw trials.

User journey: Create task → choose/define stimulus → define conditions → responses/adaptation → timing/display requirements → preview → virtual checks → scientific review/qualification → controlled acquisition → canonical data/analysis. The builder should edit these public declarations and explicit `contributions.py` registration; framework internals remain behind tested adapters. Existing VS Code source inspection remains the editable escape hatch.

Acceptance for a later builder PR: at least two materially different paradigms, experiment-specific observers and analyses, small-screen tests, no hidden scientific defaults, preserved legacy import/call contracts, and a versioned publication/review process. No generic observer or generic threshold estimator should be assumed to fit every experiment.
