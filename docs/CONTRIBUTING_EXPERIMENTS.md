# Contributing scientific experiments and stimulus classes

This is a practical contribution checklist. It does **not** require non-programmer researchers to edit code to configure, calibrate, simulate or run an existing study. Scientists who **create** new paradigms should understand the experiment Python narrative and their scientific assumptions.

## What is a contribution?

- An **experiment** is a named protocol: conditions, temporal presentation, stimulus placement in visual units, response meanings, adaptive/stopping rules and primary result.
- A **stimulus** is a reusable class: appearance and parameters, drawing/rendering operation and `SPEC`.
- A **framework change** alters shared infrastructure and must not silently change a scientific protocol.

The public experiment source is one Python file per task, in `src/psychophysics_lab/experiments/<id>.py`. The shared visual library remains one file, `src/psychophysics_lab/stimulus_library.py`: add a `LibraryStimulus` subclass with `PARAMETERS`, `render()`, and `SPEC`. **Do not** introduce a parallel JSON-only authoring engine, auto-generator, one-module-per-stimulus framework or competing registry.

## Where to begin

Read, in order: [short learning guide](LEARN_PSYCOLAB.md), [architecture](ARCHITECTURE.md), [authoring contract](AUTHORING_CONTRACT.md) and [experiment file guide](../src/psychophysics_lab/experiments/README.md).

Start from a known correct **example**, not an assumed formula. The code itself remains editable in an ordinary Python editor; the TUI is the hub for selecting, configuring, inspecting, calibrating and testing. New `SPEC`-declaring experiment files in the supported public directory are discovered automatically; manual calls to the internal registry are not normally required. Saved-design compatibility, managed Draft/Test/Ready status and legacy names have additional constraints.

## Submitting an experiment/stimulus PR

1. Fork the repository, or obtain collaborator write access, and make a dedicated branch. Do not edit `main` directly.
2. Write the study definition and stable unique ID. Document visual-angle units, digital contrast versus measured luminance, randomisation and timing, correct response/alternatives, adaptive method (if any), and a meaningful primary estimate.
3. For new stimuli, inspect more than a single nominal preview: check low/high values, backgrounds, cropping, both response alternatives, sampling and invalid inputs. Preserve digital precision and actual output requirements.
4. For experiments, verify that `ConfigField` defaults/ranges/units match the code, that each selected value influences real trial presentation and saved metadata, and that no implicit scientific constant overrides the selected setting.
5. Test a representative simulation when supported. `--dev-preview STIMULUS_ID` previews drawing; `--dev-stage experiment ID`, `--dev-test ID` and `--dev-ready experiment ID` govern declared Draft/Test/Ready stages. Some hardware-dependent results remain unqualified even when tests pass.
6. Verify canonical output and provenance: manifest, `resolved_experiment.json`, `trials.tsv`, interpretation of presented-versus-next stimulus values, response mapping, profile revision, source hashes and analysis status.
7. Add deterministic software tests. Do not hard-code an accidental default when the actual contract is that a selected parameter is honoured. Do not remove or relax an existing scientific test to make a PR green without demonstrating why its expectation was outdated.
8. Update current, relevant user documentation; mark superseded material and retain historical audit reports as evidence.
9. In the PR description, state scientific motivation, new ID/files, changes to existing experiments (if any), external dependencies, platform/testing evidence, limitations, potential backwards incompatibilities and whether hardware calibration was performed. **Do not claim participant-readiness from simulation alone.**
10. Maintainers review source, results and data compatibility before deciding to merge. A merged code change does not retroactively qualify a physical lab or justify reinterpreting historical runs.

## Short PR acceptance checklist

- [ ] Unique stable experiment/stimulus ID; no collision with official or another lab's definition
- [ ] Consistent readable Python narrative; no hidden second stimulus engine
- [ ] Units, valid ranges, scientific defaults and trial timing stated
- [ ] Key/alternative meanings and response/adaptive updates explicit
- [ ] Synthetic/headless tests and (when required) true monitor evidence reported separately
- [ ] Saved data dictionary, status and source provenance remain interpretable
- [ ] No acquisition data, personal information, local device calibration or secret files committed
- [ ] No silent schema/path change, no silent change to existing scientific behaviour
- [ ] Tests and docs updated; limitations and known failures disclosed

## Authoring and physical acceptance are different

A developer can mark a Python experiment software-ready only after the appropriate tests. A laboratory can acquire valid participant data only after checking the selected monitor, geometry, photometric response, graphics output precision, physical timing, response devices and protocol-level qualifications. Researcher override is an explicit, recorded human decision, never a hidden replacement for real qualification.

A contribution does not need expensive NVIDIA hardware to **compile or simulate**; actual presentation must nevertheless meet the lab's measured requirements. Do not infer 10-bit output, 180 Hz timing or a calibrated contrast range from marketing specifications.

## Licensing, ownership and attribution

No software licence is selected in the repository at the time this document was written. Public visibility does not automatically grant permission to redistribute code. The maintainer/institution must select an appropriate licence and consider consent for the bundled legacy renderer before accepting externally redistributed contributions. Contributor source ownership, permission to publish, acknowledgement and citations should be clarified in the PR. Do not add a guessed licence on behalf of the owner.

## Current versus future local extensions

Today, use branches/forks for custom Python and local configuration for reusable run values. A future explicitly approved external `PsyCoLab_Extensions/` workspace is planned, but is not yet wired into the official discovery and acquisition pipeline. Its acceptance requirements are in [the roadmap](INTERNATIONAL_LAB_ROADMAP.md).
