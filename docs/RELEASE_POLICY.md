# Release policy and evidence checklist

PsyCoLab currently exposes a Python software version, but a version string alone is not a validated international laboratory release. `main` remains a development integration branch until a maintainer explicitly publishes a reviewed tagged release.

## Proposed version semantics

Use `vMAJOR.MINOR.PATCH` tags when released: breaking API/format changes require an explicitly documented migration; compatible functionality goes in MINOR; documented repairs go in PATCH. A new scientific experiment with a new ID can be a compatible addition, while changing existing trial timing, contrast or response meaning must be reviewed as a scientific/protocol change even if technically compatible Python.

Never claim that a new software version automatically qualifies hardware. A lab should report **software version and Git/source hashes**, experiment identity, selected scientific values, monitor identity/profile revision and physical qualification status.

## Before a stable release

- [ ] Repo owner/institution selects a **software licence**, checks ownership and bundled third-party graphics/runtime licences, and documents citation/attribution requirements.
- [ ] Scientific core, official experiments and external/local extension boundary are clear. No duplicate active authoring systems.
- [ ] Windows and Linux headless tests reviewed. Pre-existing failures are fixed or independently justified with a release decision; do not silently mark red CI green.
- [ ] Installation documented for supported OS, Python version, dependency constraints and reproducible clean environment.
- [ ] Source provenance records every executable scientific file, including supported local extensions where applicable.
- [ ] Canonical data formats, old-version readers and any migrations are tested against preserved fixtures.
- [ ] Selected Windows laboratory monitor/GPU/driver/photometer/input chain is physically checked: frame timing, output precision, display geometry and photometric transfer as required.
- [ ] Backups, recovery after update conflicts and documented safe downgrade procedures are reviewed.
- [ ] A release note specifies exactly what changed, known limitations and whether published experiment outputs can be compared.
- [ ] Maintainer creates an annotated signed-off tag/release only after these gates. Avoid creating hypothetical `v1.0.0` tags as placeholders.

## Suggested release note headings

1. Version/tag, commit, publication date and supported platforms.
2. Scientific changes (explicitly 'none' if purely visual/docs).
3. User-facing changes and new studies.
4. Saved-file schema changes, backwards compatibility and migration steps.
5. Calibration, output precision and timing limitations.
6. Fixed regressions, outstanding issues and test results.
7. Update/backup instructions and provenance/reproduction checklist.

See [the compatibility policy](SCHEMA_COMPATIBILITY.md), [international roadmap](INTERNATIONAL_LAB_ROADMAP.md) and [Windows hardware acceptance](WINDOWS_HARDWARE_ACCEPTANCE.md). This policy does not itself publish a release or claim validation.
