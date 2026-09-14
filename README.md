# PsyCoLab — Psychophysics Collaborative Lab

PsyCoLab is a developing Python framework for configuring and running visual
psychophysics experiments. The project is being refactored from a research
codebase into a reusable laboratory tool while preserving the behaviour of
working experiments until their scientific details are deliberately reviewed.

The current repository contains **one reference experiment**: a contrast
sensitivity function (CSF) experiment. The CSF is an example built using the
framework; it is **not** the definition of the framework.

The longer-term design is intended to support experiments with different
stimuli, trial structures, response mappings, adaptive procedures and display
configurations, including lateral probe/flanker and multi-interval
ellipse/annulus paradigms.

## Current status

Public-v1 currently provides:

- repaired independent adaptive staircase state and termination;
- explicit normalised display contrast (`C_disp`) handling;
- an explicit experiment registry rather than treating every Python file as an
  experiment;
- a Textual setup interface;
- a monitor-profile boundary;
- per-run configuration/parameter snapshots in addition to the legacy files;
- a Python 3.11 / Pyglet 1.5.27 reproducible environment definition;
- a Windows one-click launcher.

The legacy Pyglet/OpenGL renderer is intentionally retained. The current CSF
shader mathematics have **not** been changed by this framework phase.

## First launch on Windows

The intended first-run workflow is:

1. Clone or download this repository.
2. Make sure Python **3.11** is installed.
3. Double-click `run_psycolab.bat`.
4. The launcher creates/reuses a local `.venv`.
5. Required packages are installed from `pyproject.toml` when needed.
6. The PsyCoLab Textual setup interface opens.
7. Enter a participant ID.
8. Choose an experiment and validated display profile.
9. Configure the experiment-specific parameters.
10. Review the session.
11. Choose **Run Experiment**.
12. The Textual app exits completely, then the Pyglet experiment launches.

PsyCoLab does not silently install Python itself.

### Command-line equivalents

After the environment has been created:

```powershell
.venv\Scripts\python.exe -m psychophysics_lab
```

or:

```powershell
.venv\Scripts\psycolab.exe
```

Useful non-interactive checks:

```powershell
.venv\Scripts\python.exe -m psychophysics_lab --diagnose
.venv\Scripts\python.exe -m psychophysics_lab --list-experiments
```

## Project names

- Repository: `Psychophysics_Collaborative_Lab`
- Display/project name: **PsyCoLab**
- Python import package: `psychophysics_lab`
- Command: `psycolab`

The Python import name is intentionally descriptive while the shorter PsyCoLab
name is used for the researcher-facing application.

## Data location

For compatibility with the existing project, the default data folder is a
sibling of the repository:

```text
<parent>/
├── Psychophysics_Collaborative_Lab/
└── local_psychophysics_data/
```

A participant ID becomes a folder beneath `local_psychophysics_data`.

PsyCoLab now also creates response-owned snapshots such as:

```text
_experiment.psycolab.json
_experiment.conditions.initial.json
_experiment.parameters.initial.json
_experiment.user_config.initial.json
_experiment.conditions.final.json
_experiment.parameters.final.json
_experiment.user_config.final.json
```

These snapshots make an individual run interpretable later even though the
legacy runtime still uses shared condition/parameter files during execution.

The adaptive session also writes its own `.session.json` completion metadata.

## Participant IDs

The public setup UI asks for an ID such as:

```text
S001
subject_1
pilot-A
```

Avoid putting personally identifying information into participant folder names.

## Session choices

**New session** starts from the experiment's current configured defaults.

**Reuse previous setup (starts a new run)** loads the participant's saved
`experiment_defined.json` as starting values, but it does **not** resume a
partially completed staircase. The old terminal option labelled `OLD` did not
provide true adaptive-state resumption, so the public UI avoids that wording.

## Architecture

The migration is intentionally incremental:

```text
src/psychophysics_lab/
├── adaptive/        future public adaptive-method boundary
├── config/          session/display configuration models
├── core/            experiment orchestration bridge
├── data/            participant/session helpers
├── experiments/     explicit experiment specifications/registry
├── stimuli/         future public stimulus boundary
└── ui/              Textual setup interface
```

The working legacy implementation remains temporarily in:

```text
Events/
Experiments/
Functions/
Interface/
libC.py
```

This is deliberate. Public-v1 places stable boundaries around working research
code before moving or rewriting the graphics implementation.

## Experiment registry

Experiments are explicitly registered in:

```text
src/psychophysics_lab/experiments/registry.py
```

The current CSF specification lives in:

```text
src/psychophysics_lab/experiments/contrast_sensitivity.py
```

An `ExperimentSpec` defines:

- a stable ID and display name;
- the legacy runner module;
- the configuration fields required by that experiment;
- fixed compatibility values that have not yet been scientifically reinterpreted;
- validated monitor profiles;
- experiment-level validation.

The generic TUI reads these fields. It does not contain CSF-specific knowledge.

## Adding an experiment

The intended public-v1 pattern is:

1. Implement or adapt the experiment runner.
2. Create an `ExperimentSpec`.
3. Define the experiment-specific configuration fields.
4. Add validation for those fields.
5. Register the spec explicitly in `registry.py`.
6. Add tests.

A future experiment can therefore request entirely different parameters without
rewriting the generic TUI.

Automatic plugin discovery is intentionally not implemented yet.

## Adding a stimulus

The existing stimuli remain in `Events/stimuliC.py` during this migration.

New/reworked reusable stimuli will later move behind
`src/psychophysics_lab/stimuli/`. Do not modify the generic staircase, data
recorder or TUI simply to add a new visual stimulus.

The later stimulus review will explicitly verify units, visual angle,
calibration and shader mathematics.

## Adaptive methods

The staircase algorithm is parameterised rather than defined by a particular
paper. `n_down`, `n_up`, step sizes, reversal termination and the maximum
response ceiling are experiment/session configuration.

The current CSF defaults are preserved:

- 2-down / 1-up;
- up-step 0.35 legacy log units;
- down-step `0.5488 × 0.35`;
- 10 reversals;
- 30 accepted responses as the safety ceiling.

Changing these values through the setup interface is an explicit user choice,
not a change to the global framework.

## Display profiles

Display profiles live in:

```text
configs/monitors/
```

The initial profile reproduces the physical geometry currently assumed by the
CSF code:

- width: 610 mm;
- height: 350 mm;
- refresh: 60 Hz;
- viewing distance: 1.0 m.

The current CSF is marked compatible only with this profile until the renderer
is explicitly validated against additional laboratory displays. This prevents a
new profile from silently implying that stimulus geometry has been verified.

Photometric calibration and display-command mapping remain experiment/lab
responsibilities and will be expanded later.

## Scientific configuration versus framework configuration

Framework-level concerns include:

- participant/session handling;
- experiment registration;
- display-profile selection;
- data/session ownership;
- setup UI and launching.

Experiment-level concerns include:

- trial timings;
- stimulus conditions;
- response mapping;
- adaptive method and parameters;
- experiment-specific stimulus geometry.

A useful design test is:

> Would this core design still make sense if the only experiment were not CSF?

If not, the behaviour probably belongs in an experiment implementation rather
than the framework core.

## Known limitations / deliberately deferred work

- The CSF shader contrast expression is preserved and still requires a separate
  scientific/rendering review.
- The legacy `31.5` spatial scaling has not been reinterpreted as measured
  pixels-per-degree.
- Additional monitor profiles must be validated before the current CSF can use
  them.
- `packages.zip` is retained until its legacy role has been fully audited.
- The Pyglet/OpenGL implementation has not been modernised.
- Physical rendering, display timing and calibration cannot be established by
  headless unit tests.
- True resume-from-partial-staircase state is not implemented.
- Additional thesis experiments and stimuli have not yet been reintroduced.
- An offline wheel cache is a future deployment improvement.

See `docs/DEFERRED_STIMULUS_REVIEW.md` for stimulus-specific issues that are
intentionally not changed in this phase.

## Development tests

With the development dependencies installed:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

Unit tests are appropriate for configuration, registry, data handling and
adaptive algorithms. Real stimulus rendering/timing must additionally be
validated on the intended laboratory display.
