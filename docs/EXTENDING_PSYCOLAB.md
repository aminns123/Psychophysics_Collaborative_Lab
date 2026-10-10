# Extending PsyCoLab: experiments and stimuli

PsyCoLab should grow through explicit, reviewable modules rather than automatic
plugin discovery. Keep the four responsibilities separate.

## 1. Reusable stimulus

A stimulus defines **what is presented**. Put reusable, display-independent
parameter calculations under:

```text
src/psychophysics_lab/stimuli/
```

Prefer pure geometry/mathematics functions that can be tested without opening a
window. Keep the actual Pyglet/OpenGL drawing adapter as thin as possible.

Minimal pattern:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MyStimulus:
    size_deg: float
    contrast: float


def resolve_geometry(stimulus: MyStimulus, display_profile, resolution_px):
    # Pure calculation only.
    ...
```

Tests should cover parameter validation, conversions and deterministic geometry.
A headless test does **not** prove that the physical stimulus on a monitor is
correct; laboratory measurement/inspection is still required.

## 2. Experiment procedure

An experiment defines **how stimuli, timing, conditions and responses are
combined**. Add its configuration/specification under:

```text
src/psychophysics_lab/experiments/
```

and register it explicitly in:

```text
src/psychophysics_lab/experiments/registry.py
```

Use `ExperimentSpec` / `ConfigField` rather than adding experiment-specific
fields directly to the TUI. The hub reads the registry and builds configuration
forms from the specification.

Before registration, decide explicitly:

- experiment ID and human name;
- compatible monitor profiles;
- configurable values and defaults;
- validation rules;
- fixed run-level grouping variables;
- response encoding and trial-dictionary overrides;
- runtime implementation entry point.

## 3. Adaptive method

Adaptive methods define **how parameters change after accepted responses**.
They should not own stimulus drawing, monitor calibration, participant folder
layout or generic UI behaviour.

The working CSF staircase remains partly in the compatibility layer. Do not move
or rewrite it merely for tidiness; migration should be behaviour-preserving and
covered by equivalence tests.

## 4. Framework infrastructure

The framework owns configuration, monitor profiles, lifecycle, provenance and
canonical recording. Avoid putting CSF-specific assumptions into these layers.

## Required review for scientific changes

Discuss and approve changes to any of the following before implementation:

- stimulus mathematics;
- timings;
- contrast definitions;
- staircase rules / threshold estimator used as an acquisition rule;
- response mappings;
- monitor/calibration semantics;
- geometry assumptions;
- the retained legacy `31.5` scaling;
- canonical schemas or acquisition hierarchy.

Derived analysis may introduce alternative estimators without modifying raw
acquisition, but the analysis convention must be saved alongside its output.

## Suggested contribution sequence

1. Add pure stimulus/config calculations.
2. Add headless unit tests.
3. Add the experiment procedure/spec and registry entry.
4. Add TUI configuration handoff tests.
5. Run full headless CI.
6. Perform monitor/fullscreen/timing/calibration laboratory checks.
7. Only then collect scientific data.

## Inspectable sources and separate configuration adapters

Register stimulus metadata with `StimulusSpec` / `register_stimulus` in
`psychophysics_lab.stimuli.registry`. Give each stimulus a unique ID, human name,
description and repository-relative Python `source_path`. The inspector lists
registered components, rather than every Python file in the stimulus folder.

An `ExperimentSpec` can now declare `source_paths`, `configure_module`,
`configure_function` and `monitor_validator`. The default configuration adapter
remains `Interface.config.run_configure_experiment` for backwards compatibility.
A new experiment should provide its own configuration adapter instead of using
CSF's conditions/parameter generator. It receives
`(participant_id, data_root, resolved_setup, run_directory=...)`, writes only
inside the newly allocated run and returns conditions, parameters and response
paths. It also writes `state/user_experiment_config.json`. Its runtime keeps the
current `(conditions, parameters, response, state_directory)` call signature.

`examples/minimal_experiment.py` is an executable, hardware-free adapter example.
It is deliberately not registered in the participant-facing application. To
exercise it locally without changing the shared registry:

```python
from pathlib import Path
from examples.minimal_experiment import SPEC
from psychophysics_lab.experiments.registry import register_experiment
from psychophysics_lab.config.models import SetupRequest
from psychophysics_lab.core.runner import run_request

register_experiment(SPEC)
run_request(
    SetupRequest("synthetic_example", "new", SPEC.id,
                 "legacy_reference_display", {"example_level": 0.5}),
    repo_root=Path.cwd(),
    data_root=Path.cwd().parent / "synthetic_pipeline_data",
)
```

Run this from the repository root using its Python environment. It creates new
synthetic records; it does not present stimuli or produce participant evidence.
Register a scientific extension explicitly in the project registry once reviewed.
Duplicate IDs are rejected. Add field units/ranges/help and pure validation;
use `monitor_validator` for profile-dependent constraints. `editable=False`
marks read-only fields, while `fixed_setup` holds protected built-in constants.
Custom displays must list experiments in `qualified_experiments` only after
the laboratory has qualified that combination. Merely copying a reference
profile does not establish equivalence.

Automatic plugin discovery and a new universal trial/procedure API are outside
this change. The explicit adapter boundary lets contributors add modules while
the tested legacy CSF renderer, staircase rules and condition scaling remain in
place. Add an end-to-end hardware-free adapter test before a physical trial.
