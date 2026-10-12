# Synthetic experiment and pipeline tests

Synthetic and human acquisition use the **same external PsyCoLab data repository**.
The simulation API reads the selected data root (or the usual
`PSYCOLAB_DATA_DIR` override), and both types use the existing
`participant/experiment/display/conditions/date/run_NNN` hierarchy.

## Experiment-specific scenarios and full pipeline verification

For a named, reproducible acceptance scenario:

```powershell
python -m simulations --list-scenarios
python -m simulations --scenario csf_baseline
python -m simulations --scenario csf_short_censored
python -m simulations --scenario csf_shifted_preference
```

Each scenario runs one or more seeded virtual observers through the actual
configuration, adaptive staircase, canonical trial recorder, data validator
and experiment's own post-hoc analysis. Each run saves its `scenario_report.json` next to canonical `trials.tsv`,
and auto-generated staircase/THC figures inside its own `analysis/` subfolder.
The report contains checks, links to the synthetic runs and the
experiment-specific comparison with known model behaviour.

**Not all experiments need a CSF-style threshold estimator.** Implement
different virtual-observer models and acceptance procedures in
`simulations/<experiment>.py` and `simulations/scenarios/<experiment>.py`.
Start with:

```powershell
python -m simulations --scaffold-simulation orientation_task
```

The two templates are safe and never overwrite existing files. See
[simulations/README.md](../simulations/README.md) for registration, examples,
output paths and scientific interpretation. Software pass/fail concerns
infrastructure and declared scenario conditions; an observed numerical bias
must not be confused with a proven psychometric estimator defect.

Each CSF run can request `staircases_per_condition` (1–24; default 1).
Each copy has its own staircase ID, response streak, contrast sequence,
reversal count and stopping criterion. The total `max_trials` ceiling
applies to the whole run, not to each individual staircase. Both human
and virtual runs get a per-condition staircase PNG at completion; the figure
marks correct/incorrect responses and reversal positions. In the Data page
you can open the run folder and scenario report without hunting through the
external data tree.

Headless runs launched from Simulate display heartbeat dots in the terminal
while Textual is closed, then reopen the TUI with their report path.

## Run a CSF virtual observer

From the repository root, after installing Python 3.11 and PsyCoLab:

```powershell
python -m simulations --seed 123 --max-trials 400
python -m simulations --seeds 1,2,3 --thresholds 0.05,0.1,0.2
python -m simulations --data-root "C:\\path\\to\\local_psychophysics_data" --seed 123
```

Without `--data-root`, the simulator uses the same preferred external data
folder that the human TUI last selected. The earlier `--workspace` flag remains
as an alias for compatibility.

## Shared folder layout

```text
local_psychophysics_data/
├── psycolab_data_config.json    # human TUI's last setup; simulations do not replace it
├── runs_index.csv               # index includes both run kinds
├── H001/                        # human participant
│   └── contrast_sensitivity/.../run_001/
└── synthetic_123/               # virtual observer
    ├── .psycolab_virtual_participant.json
    └── contrast_sensitivity/
        └── legacy_reference_display/.../YYYY-MM-DD/run_001/
            ├── manifest.json   # data_kind: synthetic
            ├── SYNTHETIC_DATA.json
            ├── trial_context.json
            └── trials.tsv
```

The literal `synthetic_` ID prefix is reserved for virtual observers.
Attempted human acquisition with this prefix is rejected, and existing
unmarked `synthetic_...` folders are never silently adopted. Synthetic
participants remain visible in the data browser/index but are hidden from
the participant selector used for human acquisition. This prevents a
simulation from updating human preferences or contaminating existing
human participant folders. It does **not** claim simulated results are
measurements from a human or a calibrated display.

## Reproducibility and scientific interpretation

The CSF virtual observer is an experiment-specific psychometric model, not a
universal model for future experiments. Its frequencies currently refer to
retained **legacy CSF condition values**, not validated cycles per degree.
The observer's midpoint does not guarantee the staircase's reversal
estimator will return the same numerical threshold.

Each run saves random seed, observer parameters, algorithm and simulated
provenance. Synthetic accepted responses share the normal trial schema,
but use a deterministic virtual `recorded_utc` generated from
`2000-01-01T00:00:00+00:00` plus `event_time_s`. Human recordings retain
real wall-clock timestamps. Virtual time is **not** measured reaction time or
display photon timing.

The synthetic run uses the real configuration/event/adaptive/recording pipeline,
generates threshold analysis when there are enough reversals, and is checked
with the ordinary run validator. An unestimable short run must not invent a
threshold: its explanation is saved in that run's `analysis/` directory.

To add a different experiment, supply an experiment-specific observer and
runtime factory in `simulations/` and register a `SimulationSpec` in
`simulations/registry.py`. Validate recovery against ground truth across
multiple seeds and stimulus conditions.

```powershell
python -m pytest tests/test_simulation_pipeline.py
python -m pytest
python scripts/portability_check.py
```

Software checks do not validate Pyglet fullscreen display selection, measured
luminance, visual angle or photon onset; follow the Windows hardware checklist
before collecting scientific participant data.
