> Historical workflow notes. For new stimuli, procedures, JSON presets and blueprints,
> use the authoritative [Teaching guide](TEACHING_GUIDE.md). The old placeholder
> scaffold and record-only public procedure description below are superseded.

## Choose what you are running

On **Experiment**, choose the intended run before configuring its conditions:

| Choice | What happens |
| --- | --- |
| **Test experiment presentation** (default) | Real fullscreen stimulus and keyboard test, separate test data; no photometer or human-qualification declaration required. Physical monitor binding, framebuffer and digital contrast safety still checked before display. |
| **Human experiment** | Pseudonymous participant ID required; full physical calibration, experiment qualification and strict final preflight remain mandatory. |
| **Simulation** | Virtual observer only, with no physical display or photometer required; uses the registered simulation scenario. |

The next **Review** page defaults to that choice and shows **only its relevant readiness panel**, rather than displaying a list of human blockers while testing the software. You can change your choice on Review. Test runs use a synthetic-only ID, never a real participant identity, and still ask for a short explicit TEST DATA confirmation before fullscreen launch.

# Researcher quickstart: creating a PsyCoLab experiment

The aim is to keep research contributors focused on two files: a **stimulus**
(what is presented) and an **experiment** (the protocol, responses and timing).
Monitor management, data directories, validated configuration, provenance and
trial-log formatting belong to the framework.

## Create the two contributor files

From the PsyCoLab checkout, with its Python 3.11 environment installed:

```powershell
python -m psychophysics_lab --scaffold orientation_task
```

The command creates **new files only**, without overwriting existing work:

- `src/psychophysics_lab/stimuli/orientation_task.py`: stimulus parameters
  and its `StimulusSpec`.
- `src/psychophysics_lab/experiments/orientation_task.py`: experiment
  `procedure(run)`, its `ExperimentSpec`, and TUI-exposed `ConfigField`s.

The scaffold deliberately raises `NotImplementedError` until you implement
and validate the actual procedure. Its example does **not** draw stimuli or
produce meaningful scientific measurements by itself.

## Register the modules

Edit **one** explicit registration file:

`src/psychophysics_lab/contributions.py`

```python
EXPERIMENT_MODULES = ("psychophysics_lab.experiments.orientation_task",)
STIMULUS_MODULES = ("psychophysics_lab.stimuli.orientation_task",)
```

Preserve any existing entries. Restart the application to load the new modules.
No framework-internal runner or TUI file should need editing to register a new
experiment. View/edit source through the TUI's Experiments, Stimuli and
Developer pages or open the actual files in VS Code.

## Implement the study

- Define stimulus units, contrast semantics, and parameter validation.
- Define experiment conditions, event sequencing, presentation and response
  mapping in `procedure(run)`. The public `RunContext` exposes
  `run.values`, `run.display`, `run.responses`, `run.adaptive(...)`,
  `run.record(...)`, and `run.save_resolution(...)`.
- Declare adaptive controls in the **experiment**, not in a universal TUI menu.
  A future adaptive algorithm may have a different interface from a staircase.
- Each accepted response should call `run.record(...)` with scientifically
  defined canonical columns (see `docs/TRIAL_DATA_DICTIONARY.md`).
- Save the resolved scientific choices and timing/geometry definitions in
  `resolved_experiment.json` through `run.save_resolution(...)`. The generic
  framework does not infer your actual stimulus from a configuration field.
- Implement a corresponding observer in `simulations/` only when a meaningful,
  experiment-specific virtual-participant model is available.

**Important:** `RunContext.record` is a recording interface, not a scheduler,
renderer or automatic correctness assessor. You must implement the actual
trial progression and response handling. Keep hardware imports lazy where
possible and test pure stimulus calculations without a display.

## Check before collecting participant data

```powershell
python -m pytest
python scripts/portability_check.py
python -m psychophysics_lab --list-experiments
```

Then separately check Pyglet fullscreen output, physical display selection,
spatial and temporal geometry, calibration, stimulus contrast definitions and
accepted-response behaviour on the intended laboratory workstation. Headless
tests and virtual observers do not certify physical presentation.

For the legacy CSF model, preserve its existing display contrast, staircase
updates, response encoding and spatial scaling unless a reviewed scientific
change explicitly authorises a migration.
