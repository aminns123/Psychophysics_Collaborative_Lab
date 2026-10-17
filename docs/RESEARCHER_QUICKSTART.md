# Researcher quickstart

**Current instructions:** [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md).

1. Open `src/psychophysics_lab/stimulus_library.py` to add a
   `LibraryStimulus` class. No generator or additional stimulus .py file.
2. Write your experiment under `src/psychophysics_lab/experiments/`,
   with settings under `configs/experiments/`.
3. Use `--dev-stage experiment ID`, `--dev-test ID`, then
   `--dev-ready experiment ID`; use `--dev-preview STIMULUS_ID`
   for raster-based PNGs.
4. Run from the normal TUI after selecting a real display profile and
   satisfying calibration/human checks. Synthetic runs never prove photons.

The original reference CSF implementation is internal under
`src/psychophysics_lab/_reference_csf/`, not a second way to author
new experiments. It is retained for hardware parity until a full
TrialTimeline replacement has been verified.
