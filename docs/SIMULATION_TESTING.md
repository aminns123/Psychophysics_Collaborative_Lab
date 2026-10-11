# Synthetic experiment and pipeline tests

This facility is designed to exercise PsyCoLab's **real configuration,
adaptive procedure, canonical trial log, validation and threshold analysis**
without a human participant, Pyglet fullscreen window or audio device.

## Run the CSF virtual observer

From the project root, with its Python 3.11 environment active:

```powershell
python -m simulations --seed 123 --max-trials 400
python -m simulations --seeds 1,2,3 --thresholds 0.05,0.1,0.2
```

Or use Python:

```python
from simulations.csf import CSFObserver
from simulations.run import simulate

artifacts, analysis = simulate(
    workspace="..\\psycolab_simulations",  # isolated, marked sibling folder
    seed=123,
    observer=CSFObserver(threshold=0.1, preferred_condition=63.0),
)
```

The `workspace` directory **must** be named `psycolab_simulations` and
either not exist or carry the exact synthetic-workspace marker. Never point it
at human/participant data. The regular human run path refuses synthetic roots.

The CSF observer uses **legacy CSF condition values** (such as 63 and 252):
they are *not* validated cycles per degree. The observer has an adjustable
psychometric midpoint, lapse and tuning width. Its midpoint is not guaranteed
to equal the staircase's recovered reversal estimate.

## Reproducibility

The simulation uses its own seeded `random.Random` instance, without changing
global random state. Accepted synthetic responses flow through the existing
legacy staircase/event adapter. Its `event_time_s` is simulated elapsed
time, and its `recorded_utc` starts at a fixed **virtual epoch**
(`2000-01-01T00:00:00+00:00`) plus that event time.

For identical seed, observer and configuration, the canonical `trials.tsv`
is designed to be **byte-for-byte reproducible** across isolated runs.
Real human acquisition continues to use genuine wall-clock UTC timestamps.
Virtual timestamps are labeled as synthetic in the run's
`trial_context.json` and `trial_data_dictionary.tsv`.

The run also stores `SYNTHETIC_DATA.json`, a synthetic `manifest.json`
and simulated `runtime_display.json`. Synthetic output is **not scientific
human-subject evidence**, and no physical display calibration is inferred.

## Add a new experiment-specific observer

Implement an observer and `runtime_factory` in `simulations/`, then register
a separate `SimulationSpec` in `simulations/registry.py`. Do not impose
CSF's particular sigmoid, correctness mapping or frequencies on a different
experimental paradigm.

The observer should define reproducible response probabilities, trial/condition
mapping, and an unambiguous ground truth. Test recovery across seeds and
parameter sweeps, including deliberately short/censored runs with **no
fabricated threshold**.

```powershell
python -m pytest tests/test_simulation_pipeline.py
python -m pytest
python scripts/portability_check.py
```

Headless success does not replace fullscreen, calibration or photodiode testing.
