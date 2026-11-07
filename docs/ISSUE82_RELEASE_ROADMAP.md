# Issue #82 — reproducible Windows installation and safe updates

**Status updated 7 November 2026.** The approved plan dates to 26 October.
The [26 October baseline](ACCEPTED_SOFTWARE_BASELINE.md) records its own
revision. Current development evidence and the scope of hosted Windows CI
are listed in the [release policy](RELEASE_POLICY.md). The
[Issue #82 checklist](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/82)
tracks the remaining release and acceptance decisions.

**Stages 1–3 are complete. Stages 4–5 remain open.** Same-workstation
installation and rollback rehearsals are recorded as bounded evidence.
Independent Windows 11 acceptance and the intended release-to-release
update and rollback still need their own results.

| Stage | Scope | Dependencies and acceptance |
|---|---|---|
| **1 — Baseline documentation and release evidence** | Completed in merged #121 and subsequent acceptance documentation. | Historical results remain dated; do not misrepresent them as current CI. |
| **2 — Editable-install identity repair** | Completed in merged #122. | Editable source/metadata identity checks remain required on reuse. |
| **3 — Reviewed Windows constraints and launcher integration** | Complete in [PR #161](https://github.com/aminns123/Psychophysics_Collaborative_Lab/pull/161), merged as `56d8eff`. The approved [Windows profile](WINDOWS_ENVIRONMENT.md) identifies conda-forge CPython 3.11.15 x64 and hash-locked runtime, build and development artifacts. | Two real fresh setups and repeat startup passed on the same host. The source setup and existing qualified installation remain separate routes. |
| **4 — Real fresh-install acceptance** | Open. Use a separate Windows 11 workstation, a fresh interpreter provisioner and an independent first-time researcher. Verify setup, imports and source/package identity, catalogue, a short synthetic run, repeat launch and recovery. | Use the approved Stage 3 profile and disposable source, configuration and data. Record native Configure and Review, external authoring, developer Test → Ready and execution as specified in the issue checklist. |
| **5 — Safe update/rollback rehearsal and versioned release guidance** | Open. Validate the intended approved old and new releases with separate environments and copied lab/config/archive fixtures. | Record readiness changes, archive compatibility, protected-root preservation, recovery and supported downgrade boundaries before sign-off. Preserve participant observations. |

Exercise the supported `PsyCoLab.bat` entry point and follow the
[installation guide](INSTALLATION.md) for each route. Preserve the laboratory's
existing scientific source, calibration and data during acceptance.

## Deployment boundaries to preserve

Keep the complete editable source checkout and its environment separate from
the explicitly trusted laboratory source, local configuration/calibration/
presets, and participant data roots. Normal Git updates do not overwrite those
external roots. When moving to a new checkout, explicitly retain the existing
root selections: ignored `.psycolab_local.json` pointers and sibling defaults
are not an independent backup. Never infer that an empty catalogue authorises
copying over an existing lab folder.

Exact constraints, a real fresh-install acceptance test, rollback guidance and
versioned release documentation are all required. Preserve the current source
installation model; wheel-only deployment would require unrelated resource
packaging work. A constraints file is not by itself a complete hash-checked
installation manifest. Record the Python installer/distribution and build tools
as well as runtime packages. Lab-specific dependencies need their own reviewed
compatibility evidence; do not silently replace their requirements.

The update rehearsal must use disposable copies before any lab adoption:
record old commit/environment/roots, retain independent backups, prepare and
validate the new checkout/environment, compare protected content, and reopen
the retained old installation on compatible copied configuration if rollback
is needed. Never roll back participant observations or force an old reader to
accept unsupported newer schemas. Fingerprint changes can legitimately return
unchanged lab source to Draft; normal retesting and deliberate Ready approval
remain required. Do not copy virtual environments between computers or overlay
source ZIPs onto an existing installation.

## Issue #80 and release gates

The [Issue #80 evidence reconciliation](ISSUE80_VALIDATION.md) records completed
trust, simulation, provenance, offline archive and source-invalidation checks.
Issue #80 is closed for its software scope. Its remaining native-editor/current
readiness acceptance is consolidated into #82; do not repeat the extension audit. Broader installation/update/
rollback acceptance belongs to stages 4–5, not a new extension feature project.

Issue #82 remains open for Stages 4–5, native researcher acceptance, licensing,
ownership and third-party attribution, and maintainer approval of a new
version and tag. Its checklist retains other unresolved acceptance items.
Apparatus-specific acquisition qualification is recorded separately by each
laboratory. The existing `v0.3.0` identifies its original research pre-release.
See [release policy](RELEASE_POLICY.md) and
[safe updates](SAFE_UPDATES_AND_LOCAL_WORK.md).
