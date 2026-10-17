> **Historical acceptance record, not current authoring instructions.**
> For the only supported new authoring route see
> [LEARN_PSYCOLAB.md](LEARN_PSYCOLAB.md). Older generator/scaffold details
> below describe a past release, not options now available in the TUI.

# PsyCoLab teaching readiness — acceptance and handover

This document records **software evidence**, not certification of a physical laboratory setup.
Its purpose is to accompany the P1 guided-stimulus/experiment authoring changes
based on the P0 lifecycle/calibration work (PR #35, merged in `main`).

## Release decision

- **P0:** calibration and public-procedure lifecycle changes are on `main` via
  [PR #35](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/35).
  Do not equate acceptance of saved luminance values with physical photometry.
- **P1:** guided Gabor stimulus, fixed-trial and adaptive orientation tasks,
  scaffold, JSON defaults/presets, source inspection and saved-data validation are
  implemented in the proposed teaching changes. They must pass CI on the actual
  proposed revision before merge.
- **Human laboratory qualification:** **NOT TESTED** by the teaching changes.
  Geometry, luminance (where applicable), photon timing (where applicable) and
  response-device behaviour require checks on the actual monitor and computer.

## Acceptance matrix

| Priority | Criterion | Evidence / remaining gate |
|---|---|---|
| P0 | Calibration and experiment preflight agree; missing physical checks are visible | PR #35; repeat hardware UI walkthrough on the actual monitor |
| P0 | New public experiments explicitly declare calibration requirements | `tests/test_public_lifecycle.py`, `tests/test_teaching_components.py` |
| P0 | Complete/abort/fail preserve correct status and artifacts | `tests/test_public_lifecycle.py`, `scripts/validate_run.py` |
| P0 | Historical CSF and saved datasets remain compatible | CSF regression tests; run the complete supported-platform suite |
| P1 | Select and edit per-stimulus JSON; no default overwrite; preserve snapshots | `tests/test_teaching_components.py`, `tests/test_teaching_tui.py` |
| P1 | New stimulus scaffold and reuse in existing orientation task | `tests/test_teaching_components.py::test_scaffold_register_configure_simulate_save_validate` |
| P1 | New experiment scaffold and reuse of existing Gabor | Same test; `docs/TEACHING_GUIDE.md` |
| P1 | Reuse an adaptive method and author a new one | `tests/test_teaching_components.py::test_adaptive_blueprint_registers_through_contribution_list_and_runs` |
| P1 | Response mappings and source inspection through TUI | `tests/test_teaching_tui.py`, `tests/test_source_inspection.py` |
| P1 | Completed simulation validates and has immutable parameter records | `tests/test_teaching_components.py`, `scripts/validate_run.py` |
| P1 | Offline static preview | `python -m psychophysics_lab --preview-stimulus teaching_gabor --preview-output example.png` |
| P1 | Actual human response display/timing/monitor behaviour | **NOT TESTED**; see hardware dry run below |
| P2 | General animated or colour renderers, arbitrary input devices | **DEFERRED**; current teaching contract is static grayscale and standard keyboard |

## Known limits to explain to students

1. The blueprint renderer returns **digital grayscale commands**. A requested
   Michelson modulation fraction is not a measured optical contrast. Do not
   infer calibrated contrast thresholds without physical photometry and an
   appropriate validated mapping.
2. Simulated reaction times are virtual. Hardware response times are software
   intervals measured after the swap request; they are not photon onset or
   independently calibrated key latency.
3. The teaching example is **self-paced static presentation**. Precise stimulus
   duration and advanced animated stimuli require an additional validated
   presentation contract.
4. New researcher modules require adding their dotted names to the documented
   `src/psychophysics_lab/contributions.py` list. This is user-facing registration,
   not an edit to the core registry/runner. Future automatic opt-in registration
   could simplify this, but indiscriminate directory scanning is undesirable.
5. Local JSON presets are distinct from read-only shared defaults. Saved runs
   retain a resolved snapshot, so later preset edits do not alter old results.
6. Calibration status depends on both the physical setup and the particular
   experiment/stimulus requirements; a simulation never qualifies a monitor.

## Teaching-day acceptance sequence

1. On the actual Windows computer, use **Python 3.11**, install in a clean venv,
   and record the exact Git commit and the environment package versions.
2. Run `python -m pytest` and `python scripts/portability_check.py`.
3. Launch PsyCoLab; ensure CSF, Orientation Task and Orientation Adaptive appear.
4. Select **Simulation**. On Orientation Task, edit Gabor JSON in a named preset,
   change orientation, preview, reload, review, simulate and inspect saved data.
5. Run `python scripts/validate_run.py PATH_TO_RUN`. Confirm successful status,
   `stimulus_parameters.json`, `trial_presentations.json` and run provenance.
6. Scaffold one student stimulus and one student experiment. Add their modules
   to the documented contribution list, restart and repeat simulation.
7. Inspect the corresponding stimulus, experiment and procedure Python sources
   through the TUI and test invalid JSON / duplicate names produce clear errors.
8. Confirm CSF simulation and historical data readers still work.
9. Before any **human** trial: bind the real monitor, measure viewing geometry,
   verify spatial calibration, verify required luminance and timing separately,
   inspect response keys and Escape/window-close abort, and satisfy the human
   preflight. Keep actual photometer evidence separate from synthetic data.
10. Run a short permitted human session and a deliberate abort. Inspect both
    output folders and record any discrepancies. If a required physical check is
    missing, continue **simulation teaching only**.

## Review, rollback and preservation

Do not merge until Windows/Ubuntu CI passes on the proposed P1 commit. For an
unverified hardware requirement, do not claim the installed lab is qualified.
Keep the last verified `main` revision and installation unchanged; try the P1
change on a separate branch/checkout. If rollback is needed, switch back to
that checkout. Do not delete participant data or monitor-profile history. Keep
saved runs attached to the version which produced them.

See [TEACHING_GUIDE.md](TEACHING_GUIDE.md) and
[PUBLIC_PROCEDURE_LIFECYCLE.md](PUBLIC_PROCEDURE_LIFECYCLE.md) for exercises and
supported lifecycle contracts.
