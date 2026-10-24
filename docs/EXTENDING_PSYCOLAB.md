# Extending PsyCoLab

## Local ownership and safe updates

These steps describe contribution to the **official** PsyCoLab source tree.
A local scientist should normally change selected values in the TUI and save
them as **local presets**, not edit official source defaults.

**Independent laboratory experiments are now supported through an explicitly
trusted external source folder**. Follow the separate
[laboratory extensions guide](LABORATORY_EXTENSIONS.md) to author, preview,
simulate, mark Ready and run lab-owned scientific Python without editing the
framework checkout. The private-branch/fork steps below remain appropriate
when proposing an **official repository contribution**.
See [safe Git updates](SAFE_UPDATES_AND_LOCAL_WORK.md),
[contributor policy](CONTRIBUTING_EXPERIMENTS.md) and
[the architecture roadmap](INTERNATIONAL_LAB_ROADMAP.md).

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

The official experiment catalogue uses package-owned experiment files in
`src/psychophysics_lab/experiments/`. Once a trusted laboratory root is enabled,
validated local experiments also enter the **same** registry and runner; their
IDs must be namespaced and their source filenames must match those IDs. `contrast_sensitivity.py` is a general-purpose psychophysics
experiment, **not** a thesis-specific contract. Retired experiment engines,
their renderer, and their executable adapters were removed in PR #73; they
can be examined at older Git revisions if historical provenance is needed.

Old participant data and original run identifiers must never be silently
renamed. New runs use the current public experiment identity and a
human-readable directory; check each run's `manifest.json` and
`resolved_experiment.json` for the effective acquisition version.

The active stimulus library's `ContrastSensitivityGrating` accepts a Gaussian
width, frequency and digital contrast set by the selected experiment. It is
not a physical contrast calibration by itself. Ruler, photometer and timing
evidence remain separate from a syntactically valid Python experiment.

Adaptive runs automatically attempt post-acquisition QC figures in the run's
`analysis/` directory; the primary threshold estimator is
experiment-defined and should never be inferred from a graph alone.

See [AUTHORING_CONTRACT.md](AUTHORING_CONTRACT.md),
[ARCHITECTURE.md](ARCHITECTURE.md) and
[CSF_ACTION_MIGRATION.md](CSF_ACTION_MIGRATION.md).
