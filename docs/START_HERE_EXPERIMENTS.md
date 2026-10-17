# Start here

**Use [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md) — the only current
researcher authoring walkthrough.**

- Add `LibraryStimulus` classes in
  `src/psychophysics_lab/stimulus_library.py`.
- Put each experiment procedure in
  `src/psychophysics_lab/experiments/<task>.py` and settings in
  `configs/experiments/<task>.json`.
- No automatic code generation or separate per-stimulus modules.
- The physical reference CSF uses an **internal** retained driver whose
  GLSL stimulus shader is defined by `CSFGrating` in the same library.

For verification and internal boundaries see
[ARCHITECTURE.md](ARCHITECTURE.md).
