# Experiment consistency and scientific acceptance

The [scientific redesign](SCIENTIFIC_REDESIGN.md) supersedes the earlier exact-loop
contract. Consistency should help a researcher understand the design, rather than
force fixed-trial, spatial and temporal experiments into identical code.

## File order

1. Settings, response meanings, scientific specification and stimulus selection.
2. Conditions and trial ordering, including randomisation and repeat staircases.
3. Stimulus preparation in explicit scientific units.
4. One trial: visible sequence, sounds, response collection and interval timing.
5. Response interpretation and scientifically meaningful adaptation/state changes.
6. Initialisation, run loop, stopping and declared primary estimation.
7. Framework connection and validation.

TUI-selected values remain authoritative. A fixed-trial loop may omit adaptation.
Two temporal intervals stay visible in the trial builder. The matching spatial
tasks share structure, while their scientific geometry and condition choices remain
local. No test requires identical syntax trees.

## Researcher acceptance

One experiment file and its stimulus class should reveal the discrimination,
changed quantity/units, condition/alternative schedule, adaptive rule, stopping,
exclusions and primary estimator. Shared decisions require a documented reason.
The redesign report records these exceptions. Test a researcher's comprehension
by asking them to sketch a display/timeline and modify a condition and a timing.
Automated checks do not establish human usability.

## Scientific and compatibility checks

- Preserve frozen historical full traces under explicit replay IDs; new protocols
  receive distinct identities and degree-based geometry.
- Validate stimulus parameters, response meanings and TUI overrides through actual
  trial execution. Preserve accepted input and partial state on update failure.
- Verify low-contrast differences survive scientific raster/upload, and distinguish
  software timing from measured photon onset and physical output precision.
- Use stimulus-dependent observers and report recovery bias, variability, lapses,
  incomplete runs and boundary exits. Do not hide censoring behind successful runs.
- Recompute acquisition's declared primary estimate from canonical data. Label
  alternate analyses as exploratory and require complete configured repeats.
- Keep human acquisition and managed component readiness gates until qualified.

The public `contrast_sensitivity.py` and menu name are universal. The saved ID
`csf_thesis` remains for compatibility because `contrast_sensitivity` already
identifies a scientifically different historical renderer. Never reinterpret
existing runs by recycling that ID.
