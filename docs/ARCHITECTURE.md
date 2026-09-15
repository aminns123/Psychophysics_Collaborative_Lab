# PsyCoLab architecture

PsyCoLab is a general psychophysics framework. Contrast sensitivity (CSF) is
the first reference experiment, not the definition of the framework.

```text
PsyCoLab
|-- configuration / TUI
|-- experiment registry / specifications
|-- monitor profiles
|-- experiment runner / lifecycle
|-- canonical data recording
|-- adaptive methods (partly legacy)
|-- stimuli / rendering (partly legacy)
`-- legacy compatibility layer
```

## Current package boundaries

| Under `src/psychophysics_lab/` | Responsibility |
|---|---|
| `__main__.py`, `app.py` | CLI, diagnostics, setup-to-acquisition handoff and final run summary. `python -m psychophysics_lab` and `psycolab` use this entry point. |
| `config/` | Setup requests, monitor models, profile loading and validation of encoded luminance mappings. Profiles are stored in `configs/monitors/`. |
| `ui/` | Textual participant, workspace, experiment and display selection; experiment-owned fields and review. The TUI closes before the renderer launches. |
| `experiments/` | Explicit registry, `ExperimentSpec`/`ConfigField`, validation, grouping folders and trial dictionary overrides. CSF supplies its own defaults and legacy module. No automatic experiment discovery. |
| `core/` | Runner owns run creation, configuration snapshots, provenance, finalization and index updates. Lifecycle helpers save an experiment-supplied termination reason and close its window; they do not define scientific completion criteria. |
| `data/` | Portable identifiers, participant listing, workspace state, run allocation, atomic JSON snapshots, run index, append-only trial records, dictionary and readable exports. |
| `adaptive/` | Intentional future boundary for reusable adaptive methods. Current working staircase mechanics still live in `Events/staircase.py`. |
| `stimuli/` | Intentional future boundary for reusable stimulus APIs. Current renderer remains in the compatibility layer. |
| `paths.py`, `diagnostics.py` | Checkout/external workspace resolution and local crash/fatal-fault diagnostics. |

These boundaries describe the current incremental migration, not a new API design.

## Compatibility layer

`Events/`, `Experiments/`, `Functions/`, `Interface/` and `libC.py` remain
temporary compatibility code during incremental migration:

- `Interface/config.py` translates setup into the established runtime files.
- `Experiments/contrast_sensitivity_function.py` composes the reference experiment,
  its phase queue, display, stimuli and response handling.
- `Events/staircase.py` provides display-independent response streaks, staircase
  state and completion; `adaptiveMethods.py` and `adaptive_session.py` adapt the
  legacy events/files to these rules and the canonical recorder.
- `Events/display_contrast.py` provides the existing digital contrast conversions.
- `Events/stimuliC.py` and `libC.py` own the existing Pyglet/OpenGL stimuli and engine.
- `Functions/functionsForUse.py` supplies legacy file and geometry helpers.

The runner temporarily establishes the checkout working directory/import path
for this layer. `packages.zip` remains a runtime dependency archive pending a
separate contents, dependency and licensing audit. A source checkout is still
needed for acquisition; the package installation alone does not replace it.

## Acquisition and lifecycle

An explicit experiment specification and selected monitor profile produce setup
and fixed grouping components. The runner creates:

```text
participant / experiment / display / fixed conditions / YYYY-MM-DD / run_NNN
```

Data live outside the checkout. Each run owns its configuration, initial/final
state snapshots and manifest. Workspace preferences and `runs_index.csv` are
convenience records; the run folder is authoritative. Reusing setup starts a new
run, not a resumed staircase.

`trials.tsv` (schema 1) records accepted responses only, with distinct `presented_*`
and `next_*` values. Its dictionary defines the saved columns; `trials_readable.txt`
is a derived fixed-width view. The six-column legacy response remains compatible.

Scientific completion, the response ceiling, Escape and errors remain distinct.
The adapter saves each accepted response before automatic termination. Escape
saves `aborted_by_user` without inventing a response. See
[lifecycle](EXPERIMENT_LIFECYCLE.md), [data layout](DATA_LAYOUT.md) and
[trial dictionary](TRIAL_DATA_DICTIONARY.md).

## Runtime provenance

The manifest keeps SHA256 fingerprints with sorted repository-relative POSIX
paths. The acquisition-source inventory recursively includes all Python files
under `src/psychophysics_lab/`, `Events/`, `Experiments/`, `Functions/` and
`Interface/`, plus `libC.py` and `packages.zip`. New runtime helpers in these
boundaries are therefore included automatically without import tracing or Git.

Tests (`test_*.py`, `*_test.py`, `conftest.py`, test directories), hidden/local
directories, caches, temporary/data directories and symlinks are excluded.
Only Python sources and the named dependency archive are fingerprinted: no
participant data, editor settings, bytecode or absolute machine paths.
The selected monitor profile and resolved configuration are saved separately
as run artifacts. Adding a runtime source boundary outside these roots requires
deliberately extending the inventory.

## Read-only validation

```text
python scripts/validate_run.py <run_directory>
```

The validator prints individual checks and PASS/FAIL, with exit code 0/1.
It reads files only, compares supplied output hashes, checks trial schema/counts,
adaptive status/state, interleaved staircase continuity, response ceilings,
portable JSON metadata and agreement of dictionary/readable/configuration files.
For CSF it also checks legacy post-response quantities and state snapshots.
Numeric comparisons use relative and absolute tolerance `1e-12`.

Use it after finalization. A consistent abort can pass; incomplete/crashed runs
may fail for missing artifacts. Missing hashes are explicitly reported as
unverified. PASS is internal consistency, not proof of untampered data, scientific
validity, display calibration or stimulus timing. Dictionary checks use the
current registered experiment definitions, so historical schema/definition
versions may need their corresponding checkout. No repair is attempted.

## Scientific changes remain a separate review

Shader and staircase mathematics, phase timing, response mappings, contrast
definitions, calibration semantics, geometry and the retained `31.5` scaling are
unchanged. See [deferred stimulus review](DEFERRED_STIMULUS_REVIEW.md).
