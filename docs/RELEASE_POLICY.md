# Release policy and evidence checklist

PsyCoLab currently exposes a Python software version, but a version string alone is not a validated international laboratory release. `main` remains a development integration branch until a maintainer explicitly publishes a reviewed tagged release.

## Release scope: software is not apparatus certification

A **stable Windows software release** establishes only its documented software
scope: reviewed source/version, an approved reproducible Windows/Python environment,
correctly functioning scientific software and records, compatible updates/readers,
an independent researcher workflow, distribution rights and maintainer approval.
It **does not** certify any monitor, GPU/output chain, photometer, response device,
speaker, laboratory calibration or scientific protocol on another machine.

**Physical and protocol qualification is a separate laboratory responsibility.**
Before claiming valid human acquisition for a specific setup, that laboratory must
check geometry, luminance/contrast, sampling, physical presentation and response
timing, sound where applicable, and protocol-specific validity against justified
criteria. Keep calibration/preflight safeguards and explicit recorded qualification
status; a software pass or researcher override never creates measured evidence.
Lack of universal hardware qualification **must not block** an otherwise approved,
explicitly scoped software release. Conversely, a software release must never be
advertised as physical apparatus qualification.

## Proposed version semantics

Use `vMAJOR.MINOR.PATCH` tags when released: breaking API/format changes require an explicitly documented migration; compatible functionality goes in MINOR; documented repairs go in PATCH. A new scientific experiment with a new ID can be a compatible addition, while changing existing trial timing, contrast or response meaning must be reviewed as a scientific/protocol change even if technically compatible Python.

Never claim that a new software version automatically qualifies hardware. A lab should report **software version and Git/source hashes**, experiment identity, selected scientific values, monitor identity/profile revision and physical qualification status.

## Published research pre-release and next decision

**PsyCoLab `v0.3.0` was already published as a research pre-release on 24 October 2026**:
[GitHub Release v0.3.0](https://github.com/aminns123/Psychophysics_Collaborative_Lab/releases/tag/v0.3.0).
Its source tag identifies its original release commit, not the current `main`
tree. **Do not recreate, move or republish that tag** to incorporate later fixes.
The pre-release was not a physical laboratory or human-acquisition certificate.

The **historical 26 October software development baseline** was
`5fec547ecf3f86cd6bbd202a9e463637deca07d3`: post-merge main CI has
**1,562 Windows passes** and **1,560 Ubuntu passes**, zero failures, and
passing portability checks. See the [baseline evidence and limitations](ACCEPTED_SOFTWARE_BASELINE.md)
for exact Python/dependency versions, skips, warnings and scientific-output
preservation. This is not a new release or physical qualification.

The earlier **1,505-pass** Windows result at `98f4119` on 25 October remains
historical evidence for that earlier revision; it is superseded as the current
baseline, not erased or applied retroactively to `v0.3.0`.

The [five approved Issue #82 stages](ISSUE82_RELEASE_ROADMAP.md) separate
baseline documentation, editable-install identity, exact Windows environment,
fresh-install acceptance and safe update/rollback guidance. Stages 1–2 are
complete; stage 3 is next. The original 26 October evidence above remains a
historical snapshot, not the current accepted release target. Source version
`0.3.0` alone does not identify an approved environment or authorize a release.

For any **future** proposed release, review all changes and their scientific
impact, use an independently reproduced clean installation, record the exact
source commit, software tests and acceptance scope, and create a **new** approved
version/tag only after owner sign-off. Document physical qualification separately
for each laboratory apparatus/protocol for which acquisition claims are made. Never silently retag a published
source snapshot. Use the [accepted baseline](ACCEPTED_SOFTWARE_BASELINE.md)
for historical evidence and the [Issue #82 roadmap](ISSUE82_RELEASE_ROADMAP.md)
for remaining stages. The [original Windows acceptance plan](WINDOWS_RELEASE_ACCEPTANCE_AND_STRESS_TEST_PLAN.md)
retains the historical evidence matrix; Issue #82 remains the stable release gate.

## Before a stable release

- [ ] Repo owner/institution selects a **software licence**, checks ownership and bundled third-party graphics/runtime licences, and documents citation/attribution requirements.
- [ ] Scientific core, official experiments and external/local extension boundary are clear. No duplicate active authoring systems.
- [x] The historical accepted baseline and subsequent Windows regression evidence are recorded. The release target must still pass its own exact-commit Windows tests. Windows 11 is the sole supported target; see [acceptance policy](WINDOWS_ACCEPTANCE_POLICY.md).
- [ ] Installation documented for supported OS, Python version, dependency constraints and reproducible clean environment.
- [ ] Source provenance records every executable scientific file, including supported local extensions where applicable.
- [ ] Canonical data formats, old-version readers and any migrations are tested against preserved fixtures.
- [ ] A real researcher completes a native Windows 11 workflow acceptance on a fresh, approved installation (separate from headless tests and virtual observers).
- [ ] Backups, recovery after update conflicts and documented safe downgrade procedures are reviewed.
- [ ] A release note specifies exactly what changed, known limitations and whether published experiment outputs can be compared.
- [ ] Maintainer explicitly approves the software claims/limitations and creates a new signed-off tag/release only after the *software* gates above. Avoid hypothetical `v1.0.0` tags.

**Separate, apparatus-specific acquisition gate (not a universal software
distribution blocker):** each laboratory must qualify its own actual
monitor/GPU/output precision, photometric transfer and contrast, geometry and
sampling, emitted-frame timing, input/audio latencies and protocol validity as
applicable. State plainly when this is unverified. Never convert an unchecked
physical measurement into a green software Ready indicator.

## Suggested release note headings

1. Version/tag, commit, publication date and supported platforms.
2. Scientific changes (explicitly 'none' if purely visual/docs).
3. User-facing changes and new studies.
4. Saved-file schema changes, backwards compatibility and migration steps.
5. Calibration, output precision and timing limitations.
6. Fixed regressions, outstanding issues and test results.
7. Update/backup instructions and provenance/reproduction checklist.

See [the compatibility policy](SCHEMA_COMPATIBILITY.md), [international roadmap](INTERNATIONAL_LAB_ROADMAP.md) and [Windows hardware acceptance](WINDOWS_HARDWARE_ACCEPTANCE.md). This policy does not itself publish a release or claim validation.
