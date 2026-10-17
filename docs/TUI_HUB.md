# PsyCoLab TUI hub

The TUI is the interface for selecting an experiment, participant/session,
calibrated monitor profile, preview, simulation, review and acquisition.

**Build Stimuli** opens the ONE authoritative
`src/psychophysics_lab/stimulus_library.py`. Add a `LibraryStimulus`
class there, with `PARAMETERS`, `render()` and `SPEC`. No wizard,
stimulus generator or separate per-stimulus file.

**Build Experiments** opens manually written files under
`src/psychophysics_lab/experiments/` and their validated settings.
No automatic experiment copy/generator.

**Calibrate**, **Scenarios** and **Data** are distinct operations, not
alternative places to implement stimulus science.

CSF shader source is in `CSFGrating` in the shared library;
`_reference_csf/` is an internal hardware reference driver, not
another researcher authoring mechanism. See [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md).
