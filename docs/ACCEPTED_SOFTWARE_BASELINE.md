# Accepted software development baseline

**Recorded 26 October 2026.** The reliability-repair phase is complete at
`5fec547ecf3f86cd6bbd202a9e463637deca07d3`, the merge of
[PR #120](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/120).
This identifies an accepted development snapshot, not a new release tag or a
certificate of physical experiment quality. The authoritative Windows checkout
was clean on `main` and matched GitHub when this record was checked.

## Four distinct acceptance states

| State | Meaning at this baseline |
|---|---|
| Stable software development baseline | The reviewed repair series and completed Windows/Ubuntu regression evidence support continued development at the exact commit above. |
| Published research pre-release | Existing `v0.3.0`, published 24 October 2026, identifies its earlier source snapshot. Do not move or republish that tag to include later fixes. |
| Future reproducible laboratory release | Still gated by the [Issue #82 stages](ISSUE82_RELEASE_ROADMAP.md), clean installation/update/rollback evidence, rights/licensing review and owner release approval. |
| Physically qualified experiment/apparatus | Requires lab-specific evidence for the actual experiment, display, geometry, photometric transfer, output depth and timing/input chain as applicable. Neither headless CI nor software Ready supplies this evidence. |

## Verified test evidence

The completed [post-merge main workflow](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40198555501)
tested the accepted commit itself. Both test jobs and both portability checks
succeeded.

| Environment and scope | Result |
|---|---|
| [Windows main CI](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40198555501/job/121184609422): Windows Server 2025 x64, CPython 3.11.9 | **1,562 passed, zero failures, 1 skipped, 1 warning**; 997.36 s; portability passed |
| [Ubuntu main CI](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40198555501/job/121184609327): Ubuntu 24.04 x64, CPython 3.11.17 | **1,560 passed, zero failures, 3 skipped, 4 warnings**; 814.48 s; portability passed |
| Local Windows acceptance recorded in [PR #120](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/120): CPython 3.11.15 (conda-forge), 64-bit, Windows build 26300 | **1,562 passed, 1 skipped, 1 warning**; 847.00 s; relevant extension/TUI selection **121 passed, 1 skipped**; `pip check` passed |

The local full run tested PR head `4bfbbe8875c31e744bbc3f2edc807ae17a1e6734`;
its source tree and the accepted merge tree are identical
(`9542a54496df6d7ebe691c33a76d36e4867a6d6f`). Counts overlap and must not be
added together. Local tests used disposable configuration, data and pytest
directories; these are software checks, not participant observations.

Windows skips the native POSIX symlink case. Ubuntu skips the Windows junction,
case-alias and batch-launcher cases. Nested-root validation runs on both systems.
The retained registry warnings concern invalid/changed published components;
they are not suppressed or interpreted as physical faults. Deliberate error
injection also produces a diagnostic log inside disposable test data.

## Tested dependencies, not a release lock

Both main CI jobs installed NumPy **1.26.4**, Pyglet **1.5.27**, Textual **1.0.0**,
Matplotlib **3.11.2**, pytest **8.4.2** and PsyCoLab distribution **0.3.0**.
Their job logs retain the exact installed transitive versions. The existing
local environment has the same five principal dependency versions but differs
in transitive packages: for example, local/CI Pillow **12.3.0 / 13.0.0** and
python-dateutil **2.9.0.post0 / 3.0.0**. These observations do not define one
uniformly locked environment or downloaded-artifact hash set.

Read-only inspection on 26 October confirmed that the local interpreter loads
this checkout's source version **0.3.0**, while its editable distribution
metadata still reports **0.2.2**. The next, independently reviewed Issue #82
stage addresses that installation identity mismatch. This documentation PR
does not reinstall packages or repair metadata. Use the exact Git/source
identity, not the version string alone, to identify this baseline.

The observed Python patches are evidence of completed tests, not a decision
that every Python 3.11 distribution or future dependency resolution is an
approved laboratory environment. Exact runtime/toolchain selection and fresh
installation acceptance remain future work.

## Scientific-output preservation

The local independent acceptance summarized in
[PR #119](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/119)
covered **60 synthetic runs and 1,080 validation checks**, across ten official
experiments, three seeds and two repeats. All 30 experiment/seed pairs retained
byte-identical canonical trial output against the prior `bfa29ea` acceptance
and earlier audit. Reads/validation preserved raw records; manifests matched
statuses and accepted counts. Short adaptive runs intentionally exercised the
trial ceiling, not a claim of converged thresholds or human perceptual validity.

The four reliability probes passed: cascading finalisation preserves the error
manifest/raw rows; fingerprint version 2 invalidates obsolete Ready records;
export aliases cannot overwrite canonical trials; malformed recovery inputs
are rejected without changing valid calculations. These are recorded local
acceptance results, not a new matrix executed by this documentation task.
Only the two repaired test files differ between `bfa29ea` and this baseline;
the preserved scientific implementation did not change in PRs #119–#120.

## Remaining limits and decisions

- Historical Review geometry failure at **160×55** has an unconfirmed cause
  and has not reproduced in subsequent acceptance/CI. Mounting can precede
  layout, but that observation does not establish the failure's cause. Keep
  existing assertions and capture lifecycle evidence if it recurs.
- Headless Ubuntu coverage is not physical Linux acquisition qualification;
  no macOS or fresh manual desktop acceptance is claimed by this record.
- Lab-owned extension software capability and observed manual evidence are
  reconciled in [Issue #80's handoff](ISSUE80_VALIDATION.md). Only current
  readiness and native source-editor handoff remain there; no automatic
  requalification of real extensions is authorised.
- Fresh Windows installation, exact dependencies, safe update/rollback and
  versioned release instructions remain [Issue #82](ISSUE82_RELEASE_ROADMAP.md)
  work. Licensing/ownership and owner release approval are separate gates.
- Physical geometry, luminance, output depth, emitted-photon timing and
  experiment-specific qualification remain the laboratory's responsibility.
  Researcher override does not mark calibration verified or waive essential
  validity/hardware safety checks.

Older audits and their failures remain evidence for their original revisions.
This record supersedes their use as *current* pass/fail status; it does not
rewrite historical results. No new release, retag, issue closure or runtime
change is implied.
