# PsyCoLab authoring contract — one route

**This is the authoritative rule for all new experiments and visual stimuli.**

## The only normal researcher editing locations

- **Stimuli:** `src/psychophysics_lab/stimulus_library.py`. Add a
  `LibraryStimulus` class with `PARAMETERS`, `render(parameters,x_deg,y_deg)`
  and `SPEC`. Use a unique stable stimulus ID. Basic shapes and `Scene` are
  reusable building blocks *in that same file*. No stimulus generator or
  separate per-stimulus Python file.
- **Experiments:** `src/psychophysics_lab/experiments/<id>.py`, with
  validated run settings in `configs/experiments/<id>.json`. A trial selects
  registered stimuli, places them in visual degrees, schedules `Show` and
  `CollectResponse`, updates scientific/adaptive state, and ends with
  `run.complete()`. A beep is an optional **experiment action**, never part of
  the pixel renderer.
- **External data:** the framework allocates participant/simulation runs and
  writes canonical output outside the Git checkout. The user never adds file
  writing to a `render()` method or a timed response callback.

## Creation and validation

Write the code directly. The framework loads subclasses from the shared
library without editing registration files. Experiments are explicit:
`python -m psychophysics_lab --dev-stage experiment ID`;
`python -m psychophysics_lab --dev-test ID`;
`python -m psychophysics_lab --dev-ready experiment ID`.
Preview a visual renderer with `--dev-preview STIMULUS_ID`.

Published source fingerprints, calibration requirements and hardware
readiness are independent checks. Preview/virtual success does **not**
measure luminance, temporal precision or speaker onset.

## The CSF exception is internal, not a second authoring option

`CSFGrating` in `stimulus_library.py` now owns the reference GLSL shader
source, and `experiments/contrast_sensitivity.py` owns the public CSF
experiment settings and scientific contract. The physical reference presenter,
file/event bridge and old staircase compatibility implementation live
**only** in `src/psychophysics_lab/_reference_csf/` until the shared
TrialTimeline/RunContext presenter is scientifically and physically
equivalent. Do not modify those internals to author a new experiment.

The top-level `Events/`, `Experiments/`, `Functions/`, `Interface/`
and `libC.py` paths have been removed. They are not competing public APIs.
The internal reference code is still scientifically active, not dead code.

See [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md) for the short walkthrough and
[CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md) for the remaining
validation gates.
