# Researcher surface and repository-retention audit

**Status:** first safe consolidation step; no behavioural deletion of legacy
sources. This is an evidence-based audit, not a list of files to trash.

## Only two usual editing locations

1. **Stimuli:** `src/psychophysics_lab/stimulus_library.py`. Primitive
   functions and `Scene` are at the top; complete registered stimulus
   definitions are individual **classes** below. Each registered class keeps
   `PARAMETERS`, `render(parameters, x_deg, y_deg)`, and `SPEC` together.
2. **Experiments:** `src/psychophysics_lab/experiments/<task>.py` and its
   settings in `configs/experiments/<task>.json`. Define conditions, time,
   positions, adaptive rules and optionally `Beep` at this level.

Researchers can also create basic JSON-only two-choice experiments under
`configs/experiment_designs/`; calibration and participant data are separate.

## Classification and retention decision

| Area | Classification | Decision |
|---|---|---|
| `stimulus_library.py` | **Researcher-facing authoritative science** | Keep, extend here |
| `stimuli/fixation_cross.py`, `vertical_line_probe.py`, `example_stimulus.py`, `teaching_gabor.py`, `composed_scene.py` | Compatibility import modules | Reduce to *thin adapters*; retain stable IDs and import paths |
| `stimuli/geometry.py`, `spatial_calibration.py`, `contrast_validation.py` | Geometry, sampling and calibration internals | Keep separate; not researcher stimulus classes |
| `stimuli/new_probe_vertical_line.py` | Researcher-authored stimulus | Moved verbatim to `ResearcherVerticalLine` class in shared library, with original ID preserved via thin import adapter. Historical test fingerprints must be refreshed. |
| Researcher-authored experiment modules | Researcher-owned, version-sensitive trial work | Preserve exact procedures and historical data |
| `Events/stimuliC.py`, `Experiments/contrast_sensitivity_function.py` | Authoritative retained human CSF renderer/procedure | **Keep until hardware-verified parity**, not an ordinary stimulus class |
| `experiments/flanker_protocol.py`, `adaptive/legacy_flanker.py` | Development-only historical reconstructions | Keep separately; cannot acquire human data yet |
| `configs/stimuli/*.json` | Stimulus defaults, calibration/compatibility settings and reproducibility | Keep even if they look similar; some ID-specific paths are needed |
| `docs/history/`, `docs/audit_evidence/`, `tests/fixtures/` | Historical tests and scientific provenance | Keep, clearly outside everyday authoring |
| `src/psychophysics_lab/core`, `config`, `data`, `ui` | Internal framework | Never edit to create a new ordinary stimulus |

**No unconditional deletion of old research code.** This migration has
preserved every prior CSF or user-authored experiment. The converted adapter
modules now have no independent rendering implementation. Removing these
module paths outright would break existing imports/config IDs and possibly
historical fingerprints, without simplifying researcher work further.

## Stimulus inventory represented in the shared file

- **Primitive functions:** fixation, line, rectangle, square, ellipse,
  annulus, Gaussian dot, grating, Gabor.
- **Registered complete classes:** FixationCross, VerticalLineProbe,
  ExampleWhiteLine, TeachingGabor, ComposedScene, ResearcherVerticalLine.
- **Deliberately external:** geometry_bar (monitor diagnostic),
  legacy_csf (unverified shader).
- **Not stimuli:** response collection, adaptive staircase, experiment timing,
  sound cues and acquisition storage.

Do not create a duplicate renderer just to give a task a different position.
An experiment composes/positions existing drawings and selects trial timing.

## Beeps from the original PhD code

The original `Functions/functionUSE.py` uses
`winsound.Beep(frequency, duration)`. The new optional
`Beep(frequency_hz, duration_ms)` is the equivalent public declaration:
`Show(..., beep=...)` requests one after a visual flip (including a blank
Show); `CollectResponse(..., beep=...)` requests one after accepting a valid
response. Disabled by omitting the argument. Real playback is Windows-only,
asynchronous and **not** proof of sound onset/latency calibration.

## Criteria for later removal

Only remove an old source after proving (1) zero import or registry/config
references, (2) unchanged historical data decoding and reproducibility,
(3) no scientific or timing parity loss, and (4) CI on Windows and Ubuntu.
Prefer moving older prose into `docs/history/` over deleting evidence.
