# Synthetic experiment and pipeline tests

Synthetic and human acquisition use the **same external PsyCoLab data repository**.
The simulation API reads the selected data root (or the usual
`PSYCOLAB_DATA_DIR` override), and both types use the existing
`participant/experiment/display/conditions/date/run_NNN` hierarchy.

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
