# Extending PsyCoLab

## The only authoring workflow

1. **Stimulus:** edit `src/psychophysics_lab/stimulus_library.py`.
   Each `LibraryStimulus` class keeps `PARAMETERS`, `render()` and `SPEC`
   together. Add primitives/functions and build complex Scene compositions
   *in the same file*. Do not create individual stimulus modules.
2. **Experiment:** add `src/psychophysics_lab/experiments/<task>.py`
   with `ConfigField` defaults and a matching `SPEC.id`; JSON presets are
   optional and discovery needs no module-list edit. A scientific trial owns
   conditions, placement, timing, optional beeps, responses and adaptation.
3. **Test:** `python -m psychophysics_lab --dev-preview ID` for raster
   stimuli, `--dev-stage experiment ID` then `--dev-test ID`, then
   `--dev-ready experiment ID`. Virtual simulation does not validate
   a monitor, photometer or physical timing.
4. **Acquire:** use the normal TUI and physical calibration/review gates.
   Run data and historical source hashes live in a separate data repository.

`CSFGrating` contains the physically trusted reference CSF shader in the
same stimulus library. The internal `_reference_csf/` hardware presenter
remains an uneditable implementation detail until validated replacement
under the standard RunContext presenter is available. The original top-level
legacy code directories have been removed.

The registered JSON-only spatial experiment facility and historical source
files are implementation compatibility, **not** another recommended public
authoring route.

See [AUTHORING_CONTRACT.md](AUTHORING_CONTRACT.md),
[ARCHITECTURE.md](ARCHITECTURE.md) and
[CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md).
