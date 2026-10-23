## Purpose / scope

Describe **what the change does** and **why**, referencing the experiment(s), stimulus class(es), TUI, calibration or data formats affected. Prefer one scientific purpose per PR; do not combine unrelated refactoring with scientific fixes.

## Change type

- [ ] Scientific experiment/stimulus definition
- [ ] TUI or researcher workflow only
- [ ] Calibration/device input or hardware validation
- [ ] Adaptive/simulation/analysis engine
- [ ] Persisted data/schema/provenance
- [ ] Documentation, build or dependency maintenance

## Scientific impact (required)

- Existing experiment IDs affected:
- New IDs added:
- Parameter units/ranges/defaults changed:
- Stimulus equations, timing, response alternatives, updates or estimator changed:
- Expected comparability to historical runs:
- If no scientific behaviour changes, explain how that was verified:

## Validation evidence

- [ ] Relevant deterministic headless checks run; commands/results below
- [ ] Selected TUI paths and keyboard navigation checked, if relevant
- [ ] Generated canonical run data and source/parameter hashes inspected, if relevant
- [ ] Physical hardware/timing/photometry checked, if necessary (describe setup)
- [ ] Existing failures and test limitations listed; no test weakened to hide regressions
- [ ] Data paths/schema migration impact assessed and documented
- [ ] No participant records, secret settings or local monitor calibration committed
- [ ] Documentation/release-note implications reviewed

Commands/results, hardware evidence, and limitations:

## Compatibility and rollback

Describe impact on saved presets, previous monitor profile revisions, old runs, external lab code and Git update safety. If a schema migration is required, link its separately reviewed, non-destructive plan. State the source version/commit used as baseline.

**Do not merge automatically.** For contribution rules see [scientific contributor guide](../docs/CONTRIBUTING_EXPERIMENTS.md); for local code ownership see [safe updates](../docs/SAFE_UPDATES_AND_LOCAL_WORK.md).
