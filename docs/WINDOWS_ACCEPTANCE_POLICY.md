# Windows-only software acceptance policy

Maintainer policy, 28 October 2026: **Windows 11 is the sole officially supported
platform** for installation, experiment execution and laboratory release
qualification. Use 64-bit Python 3.11 under the existing compatibility contract.
No Linux or macOS acquisition, installation or release support is implied.

## Continuous integration and repository settings

The automatic Headless checks workflow runs the full regression suite and the
existing portability guard on Windows only. Its existing check name,
`test (windows-latest)`, is retained to avoid an unnecessary status-name change.
Repository administrators should make that Windows check required in the active
branch protection/ruleset and remove any obsolete required Ubuntu check. Workflow
source cannot itself change repository protection settings; verify those settings
separately before adopting this policy PR.

GitHub's hosted `windows-latest` runner currently uses Windows Server, not a
Windows 11 research workstation. Its successful headless job is automated Windows
regression evidence. **It does not satisfy the separate Windows 11 fresh-install,
researcher workflow or physical apparatus acceptance gates.** Record runner OS,
Python/dependency versions, tested source/merge commit and results in each audit.

Linux portability diagnostics may be run separately if useful, but must remain
optional and must not gate a Windows release. Do not spend development effort on
Linux-only failures unless they expose a demonstrated Windows scientific,
reproducibility or data-integrity defect. Do not skip or weaken scientific tests
on Windows to make another platform green.

## Stage C Ubuntu failure disposition

The Stage C workflow run 40507371203 had 24 Ubuntu failures, all at the frozen
`resolved_experiment.json` comparison. Its Windows job passed 2,206 tests with
one POSIX-only skip. A Windows-only reconstruction of all 24 reported Ubuntu
hashes changed only raw preset provenance fields (`experiment_settings.sha256`
or stimulus snapshot `file_sha256`), using LF instead of CRLF bytes for the same
parsed JSON presets. This reproduces every
observed failing hash. No scientific values, rows, schedules, state or event plans
need to change to explain those failures.

These are raw-byte provenance differences in a Windows-captured fixture, not
evidence of a Windows scientific defect. Preserve exact source/preset hashes and
the frozen Windows fixture. No Linux runtime or fixture repair is included in
this policy change. If optional cross-platform equivalence is pursued later,
compare parsed scientific settings separately from validated raw-file provenance.

## Release and apparatus gates

A green Windows job does not authorize a release or certify psychophysics.
Before a laboratory release, retain an approved reproducible Windows environment,
clean installation/reuse/recovery evidence, protected external source/config/data
roots, upgrade/rollback evidence, compatible archived-run readers, licensing and
maintainer sign-off. Exercise the real interface with a human researcher on
Windows 11; a virtual observer or injected display is software evidence only.

For acquisition, independently qualify actual display binding and geometry,
photometric transfer/contrast, output precision, sampling, photon timing, input
latency and audio where applicable, plus protocol-specific scientific validity.
Keep the existing calibration, readiness and acquisition safeguards. Never infer
qualification from a copied profile or alter participant/calibration data during
software acceptance. No merge, tag or release is automatic.
