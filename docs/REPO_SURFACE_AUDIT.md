# What is kept and what was removed

## Everyday researcher workflow

**Edit visual stimuli only here:** `src/psychophysics_lab/stimulus_library.py`
(**classes** with `PARAMETERS`, `render`, `SPEC`; reusable `Scene`).

**Edit experiments here:** `src/psychophysics_lab/experiments/<task>.py`,
with settings in `configs/experiments/<task>.json`.

`run_psycolab.bat`, TUI, simulation, monitor profiles, adaptive registry and
trial storage remain framework-owned. There is no stimulus generator.

## Deleted from the working repository root

The top-level `Events/`, `Experiments/`, `Functions/`, `Interface/`,
`libC.py` and `packages.zip` were previously needed to **run** CSF.
All ten associated files have been rehomed to one *internal* package:
`src/psychophysics_lab/_reference_csf/`. The old paths are removed and
their old content is recoverable from Git history. Internal imports, runtime
source hashing, CSF dispatch and the shader diagnostic were updated.

**This is a relocation/consolidation, not deletion of working CSF physics.**
The `CSFGrating.FRAGMENT_SOURCE` in the single stimulus library is now
the original authoritative physical shader source. The internal OpenGL
presenter consumes it verbatim. The internal package still owns hardware
windowing and exact old timing/staircase I/O. It is *not* a place for adding
new stimuli or experiments.

## Retained for a verified reason

- `src/psychophysics_lab/_reference_csf/`: active reference CSF
  presentation; removal before parity would break human acquisition.
- `src/psychophysics_lab/core/`: universal run lifecycle, virtual/human
  experiment dispatch, actions and data provenance.
- `src/psychophysics_lab/stimuli/registry.py`, `geometry.py`,
  `spatial_calibration.py`, `contrast_validation.py`: internal
  validation and physical geometry, NOT additional stimulus authoring files.
- `simulations/`: active headless virtual scenario runner.
- `configs/`: monitor calibrations, experiment settings and reference
  parameters. `authoring/`: explicit experiment Ready history.
- `scripts/`: portability, recording validation and actual physical
  graphics probes.
- `tests/`: regression fixtures, historical numerical CSF equivalence
  tests and safety checks.
- `docs/history/`, `docs/audit_evidence/`: provenance; not part of the
  everyday authoring surface.

## The remaining scientific migration

A complete CSF rewrite must (1) replay the same condition order,
staircase, contrast/phase, input and response rules through
`TrialTimeline` + `RunContext`; (2) match the original GLSL pixels on
real hardware, including luminance encoding; (3) match measured frame
timing and sound latency; (4) compare canonical and legacy output,
aborts and completion on actual lab PCs. Until then, do not remove the
internal reference presenter or claim the two implementations are equivalent.

We do not delete files merely because they have 'legacy' in their name;
we delete unused code only after proving zero live imports and unchanged
scientific behaviour.
