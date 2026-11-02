# Archived pre-atomic authoring implementation (read-only evidence)

This directory holds exact, byte-preserving copies of seven source files from
pre-migration commit `aa57e84f59148510035cef0e4e6ebf55f893b1d4` (PR #206).
They are retained for historical comparison during PR #207 and possible
explicitly reviewed deletion after the atomic architecture is accepted.

The directory is **outside** the installable `src/psychophysics_lab` package.
Do not import, register, execute, or modify these copies during current runs.
Do not treat old DetectionScene's composite parameters as the current
experiment authoring interface.

## Included exact source snapshots

| Original path (under `src/psychophysics_lab/`) | Original Git blob |
| --- | --- |
| `experiments/ellipse_centre.py` | `4860552bbbe3677ebf74b792b083e307307a0d85` |
| `experiments/ellipse_major_axis.py` | `2a18b66c398f7d86bedbe1b3c77151737a53d20b` |
| `experiments/line_position_baseline.py` | `9ffa7a908b68e0b05b264aec4bb97ad48da6d9d4` |
| `experiments/line_position_flanker.py` | `e583fde32713d1794c5343309c7b412c9446f15b` |
| `experiments/_internal/detection_limits.py` | `d572f3a6659f5046fade1f98be81ee3a9ad64f3f` |
| `stimulus_library.py` | `284e1dcd0faa031aff04fa4e44cf98a0c0b4e8b5` |
| `methods/probe.py` | `5d41a5ccd76593618709f8511d7814974abccbed` |

## What this does not authorize

- Removing code still used for legacy saved-file reading or scientific
  acceptance before an alternative is verified.
- Replacing frozen historical tests or fixtures with new-run baselines.
- Silently changing raw nominal digital probe-increment semantics to
  headroom-normalised display contrast.
- Assuming green tests prove pixel-level parity, display timing or hardware
  qualification.

**Retirement procedure:** explicitly enumerate remaining active references,
verify old/new numerical and event equivalence and reader migration, move only
unneeded authoring/runtime code out of the package, then run the full Windows
acceptance suite and check saved-data compatibility. A retained archival copy
is not itself a reason to bypass a failing scientific guard.
