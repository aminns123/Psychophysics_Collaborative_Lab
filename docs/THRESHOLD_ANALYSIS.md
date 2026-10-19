# Staircase quick-look and threshold analysis

PsyCoLab stores participant and synthetic responses as canonical, append-only
`trials.tsv` files. Derived analysis never changes the recorded trials,
the original staircase states, or the configuration used for acquisition.

## Automatic figures after a run

For a completed, partially completed, aborted or errored **adaptive** run with
accepted trials, finalisation calls `analysis.previews.create_run_figures`.
Eligibility is determined by the saved staircase columns, not a special
experiment ID or whether the run came from a human or virtual observer.

Figures and status are stored in the **same run** under `run_NNN/analysis/`:

- `staircases.png`: overall multi-condition diagnostic.
- `staircases_condition_<condition>.png`: all independently labelled
  staircases for one observed condition, with correct/incorrect and
  reversal markers.
- `staircase_preview.json`: provenance, canonical TSV hash and plot counts.
- `primary_thresholds.json`: derived primary estimator result, if an
  experiment declares a primary rule.
- `threshold_vs_condition.png` and `sensitivity_vs_condition.png`:
  produced only when at least one condition has a justified primary estimate.
- `analysis_status.json`: why results are missing or partial, and any
  plotting failure. Plotting problems do not invalidate acquisition.

These are QC plots. Software flip times, display contrast and screen intensity
are **not** measured photon timing or calibrated optical contrast.

## Primary versus exploratory estimators

Each experiment declares its **own primary estimator** in
`resolved_experiment.json`. For example, some procedures use the median of
the last N *presented* reversal contrasts per staircase, whereas another
may use their geometric mean. Eligible completed staircases then contribute
to the explicitly selected across-staircase aggregation. Incomplete or
censored staircases must not generate fabricated thresholds.

The primary estimator is used consistently online and by
`analysis.primary`. Sensitivity is `1 / threshold` only for positive, valid
estimates; scientific interpretation of that unit belongs to the experiment.

The TUI can also request exploratory threshold calculations with final-N or
retained-fraction reversal selection and a choice of presented/next-step
strength. Those outputs are **derived alternatives**, not replacements for
the primary estimator, and are stored under versioned
`run_NNN/analysis/thresholds/<timestamp>/` directories.

An incomplete run with no eligible threshold should still retain its
observed staircase plots and an explicit unavailable-threshold explanation.

## Recompute from raw data

Load `trials.tsv` and group rows by `stimulus_condition` and `staircase_id`.
The `reversal` column marks eligible turnaround observations. Read
`trial_data_dictionary.tsv`, `resolved_experiment.json` and the saved
configuration before deciding whether to use `presented_display_contrast`,
`presented_screen_intensity` or another declared strength.

Always keep original files read-only. Run
`python scripts/validate_run.py <run_directory>` to check internal
consistency; this is not an optical or scientific validation.
