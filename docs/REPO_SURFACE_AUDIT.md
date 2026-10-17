# Repository clean-up audit

## Where a researcher edits code

- `src/psychophysics_lab/stimulus_library.py`: all visual drawing primitives,
  reusable Scenes and registered stimulus **classes**.
- `src/psychophysics_lab/experiments/<name>.py`: each experiment's scientific
  procedure, timing, conditions, response keys and optional beeps.
- `configs/experiments/<name>.json`: run-editable scientific settings.

The framework (`core/`, `config/`, `data/`, `stimuli/registry.py` and TUI)
is not a researcher authoring location.

## Removed

Six thin per-stimulus Python modules (fixation, line, example, Gabor,
composed scene and researcher line) whose mathematics already live in the
single shared library. The registration list no longer points at these.
Retired stimulus Draft/Ready authoring records are removed from the runtime
inventory; the Git history preserves previous tested revisions.

The old stimulus-module generator is no longer exposed in the normal TUI/CLI.
All new stimuli are direct edits to the shared library.

## Retained because they are still in use

- `Events/`, `Experiments/contrast_sensitivity_function.py`,
  `Functions/`, `Interface/`, `libC.py`: the *active* reference CSF
  renderer, staircase, setup and OpenGL/shader implementation. Deleting them
  now would disable scientific acquisition. This requires a **separate**
  tested migration and a lab hardware-comparison before removal.
- `simulations/`: the headless simulator used by tests and researchers.
- `src/psychophysics_lab/stimuli/registry.py`, `geometry.py`,
  `spatial_calibration.py`, `contrast_validation.py`: internal validation
  and monitor geometry, **not** competing stimulus definitions.
- Old research experiment code and defaults: used to decode trial
  provenance or preserve source references. Do not remove without a
  source-to-run trace and verified replacement.
- Historic JSON-only experiments: old run reproduction; not advertised as
  a new authoring workflow.

**Rule for further deletion:** demonstrate zero runtime/config/import
references, unchanged past-run readability, valid synthetic trials and
Windows/Ubuntu CI. Keep original scientific CSF until a hardware-equivalent
replacement is verified.
