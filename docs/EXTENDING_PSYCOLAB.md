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
