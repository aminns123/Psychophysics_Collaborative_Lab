# PsyCoLab TUI hub

The setup interface is now intended to be the main human-facing entry point for
PsyCoLab. It remains a thin configuration/inspection layer: scientific runtime
behaviour stays in experiment, stimulus, adaptive and lifecycle modules.

## Pages

- **Run / Setup** — external data workspace, participant, starting settings,
  experiment and compatible monitor profile.
- **Experiments** — inspect explicitly registered experiments and their source.
- **Stimuli** — inspect reusable stimulus modules. The first new reusable
  stimulus is the geometry-test white bar.
- **Display Check** — fullscreen ruler test for physical size / visual angle.
- **Data** — inspect previous run manifests, canonical trials and saved adaptive
  state; run post-hoc threshold summaries without modifying acquisition data.
- **Help / Developer** — package boundaries and rules for extending PsyCoLab.

The TUI deliberately does not edit Python source. Inspection is safe during lab
use; source creation/editing should continue through normal development tools
and review until a constrained scaffolding workflow is designed.

## Setup semantics

"Reuse last settings" means *copy the previous configuration into a new run*.
It does not resume a partial staircase.

Experiment selection updates the description immediately and restricts the
monitor selector to profiles explicitly compatible with that experiment. The
monitor information card exposes physical geometry, refresh rate, viewing
distance and calibration status before the researcher proceeds.

The review page shows the intended acquisition hierarchy using `run_NNN` as a
placeholder. The run number is allocated atomically only when acquisition starts.
