# Analysing data from a saved PsyCoLab run

Use the **canonical** `trials.tsv` file, not `trials_readable.txt` or historical `legacy_response.txt`. The public helper is in `src/psychophysics_lab/data/reader.py`. It does not run an experiment or modify any acquisition file.

## The one-function approach

Open a Python 3.11 session with PsyCoLab installed in its existing environment (for example, the repository's `.venv`), then copy the following into your own local analysis script:

```python
from psychophysics_lab.data.reader import load_run

# Provide the run_NNN folder, or its trials.tsv file.
run = load_run(r"C:\PsyCoLab_Data\S001\my_experiment\display_1\2026-10-24\run_001")

trials = run["trials"]                         # dict[str, NumPy arrays]
manifest = run["manifest"]                     # original metadata dict
dictionary = run["data_dictionary"]             # per-column units/descriptions

# These two columns describe the CURRENT, actually presented response trial.
contrast = trials["presented_display_contrast"].astype(float)
correct = trials["correct"].astype(int)

print("Experiment:", manifest.get("experiment_id", "Unknown"))
print("Trials:", len(correct))
print("Mean accuracy:", correct.mean() if len(correct) else "No accepted trials")
print("Contrast:", contrast)
```

The helper also accepts `load_run(r"...\run_001\trials.tsv")`. It deliberately leaves every trial column as **text strings**, so missing entries and experiment-specific encodings cannot accidentally be converted to the wrong scientific quantity. Convert the exact columns you know with `.astype(int)` or `.astype(float)` in your analysis script. Conversion of blank/non-numeric cells may raise an error, correctly prompting you to inspect them.

### Explore unknown experiment-specific measurements

```python
run = load_run(r"C:\PsyCoLab_Data\S001\...\run_001")
for name, values in run["trials"].items():
    units = run["data_dictionary"].get(name, {}).get("units_or_encoding", "not documented")
    print(f"{name}: {units} (N={len(values)})")
```

`run["trials"]` contains **exactly the columns that were recorded**. A future experiment may add optional columns: those appear under their original names, in addition to the earlier columns. If an older run lacks such a column, it is simply absent; the loader does **not** fabricate a value. Check for optional fields with `if "my_measurement" in run["trials"]:`.

## Read-only compatibility contract

- PsyCoLab currently writes **trial schema 1** with 20 canonical columns. The run reader accepts those columns plus any additive, experiment-specific columns and uses the saved names, **not positional indices**. This does not yet change the fixed-column acquisition writer.
- Older runs with the supported trial schema can be read unchanged. A historical TSV lacking a manifest can be loaded as **unversioned data**, but its provenance and physical validity are **not established** by that fact.
- Unknown future schema versions are **rejected** until reviewed. Extra fields are fine only when the underlying established column meanings remain unchanged; a changed scientific meaning requires a new documented schema and reader support.
- Saved column names, contents and available per-run `trial_data_dictionary.tsv` are preserved; the reader does not fill missing fields with a contemporary default.
- The reader never rewrites `trials.tsv`, `manifest.json`, calibration data or existing derived analyses, and performs no participant-display operations.
- **This is a data-access tool, not a scientific validation tool.** For strict integrity/provenance checks, run `python scripts/validate_run.py PATH_TO_RUN` separately. The strict validator intentionally checks the current acquisition schema more closely than the general-purpose reader.

## Interpret correctly

- `presented_display_contrast`: contrast **presented** on this accepted response.
- `next_display_contrast`: contrast computed **after** the response for the next use of the staircase.
- `correct`: encoded 0 or 1, provided by the experiment's own response mapping.
- `stimulus_condition`: experiment-specific; inspect `trial_data_dictionary.tsv` and `resolved_experiment.json` before assuming cycles/degree or any other units.
- All recorded display contrast and intensity values are **digital quantities** unless a particular run contains actual verified photometric calibration. Do not label them measured luminance by default.

For raw data layout, see [DATA_LAYOUT.md](DATA_LAYOUT.md). For definitions see [TRIAL_DATA_DICTIONARY.md](TRIAL_DATA_DICTIONARY.md). For rules about old saved formats and migrations, see [SCHEMA_COMPATIBILITY.md](SCHEMA_COMPATIBILITY.md). For derived threshold estimates, see [the threshold analysis guide](ANALYSIS_AND_THRESHOLDS.md) where available, or inspect `src/psychophysics_lab/analysis/thresholds.py`.

## How this supports independent scientific analysis

You can import the NumPy arrays into an entirely separate research notebook or Python script. Keep that analysis code and any generated figures outside the original acquisition directory, or write appropriately versioned derived results in its dedicated `analysis/` area. Never edit the canonical observations to make a plot or to 'upgrade' an earlier run.
