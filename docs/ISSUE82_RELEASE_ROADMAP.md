# Issue #82 — reproducible Windows installation and safe updates

**Approved plan, recorded 26 October 2026; status reconciled 28 October 2026.**
The [26 October baseline](ACCEPTED_SOFTWARE_BASELINE.md) at
`5fec547ecf3f86cd6bbd202a9e463637deca07d3` is historical evidence, not
the current release candidate. The source/package identity repair is merged,
the event-first migration is complete and Windows-only acceptance is in force.
Use the latest reviewed `main` and exact-commit Windows evidence for new work.
Earlier reports of 12 or 23 baseline failures are not current blockers.

The five stages below remain separate acceptance units. Stage numbers are
plan stages, not PR numbers. **Stages 1 and 2 are completed; stage 3 is next.**
Stages 4 and 5 must validate the selected stage-3 environment, rather than
treating one-machine rehearsal as independent qualification.

| Stage | Scope | Dependencies and acceptance |
|---|---|---|
| **1 — Baseline documentation and release evidence** | Completed in merged #121 and subsequent acceptance documentation. | Historical results remain dated; do not misrepresent them as current CI. |
| **2 — Editable-install identity repair** | Completed in merged #122. | Editable source/metadata identity checks remain required on reuse. |
| **3 — Reviewed Windows constraints and launcher integration** | Select an approved x64 Python 3.11 distribution/patch; pin runtime/transitive, bootstrap/build and separate development dependencies; validate environment identity on setup, reuse and recovery. | Build on stage 2's identity handling. Review complete versions/artifact hashes and how constraints affect optional lab requirements. Preserve user requirements; no new package manager or architecture. |
| **4 — Real fresh-install acceptance** | Exercise the existing launcher/setup using disposable full checkouts and empty environments; verify imports, source/package identity, catalogue, a short synthetic validation, repeat launch and failure recovery. | Uses the stage 3 environment specification. Reconstruct twice and compare inventories, then record an independent Windows workstation rehearsal. CI's direct `pip install -e .[dev]` and mocked launcher tests are not substitutes. |
| **5 — Safe update/rollback rehearsal and versioned release guidance** | Test old/new pinned checkouts with separate environments and copied lab/config/archive fixtures; record preservation, readiness, archive compatibility and recovery steps. | Uses stages 3–4's accepted environments; can draft guidance earlier, but must validate it before sign-off. Retain old installation, protect newer observations and document downgrade boundaries. |

Stages 3–5 remain open. The approved implementation sequence must not change
scientific equations, stimulus rendering, experimental defaults, UI appearance,
calibration, participant data or the established architecture.

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

Keep [Issue #82](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/82)
open for stages 3–5, native researcher acceptance, licensing/ownership and
third-party attribution decisions, and maintainer approval of a new software
version/tag. Apparatus-specific acquisition qualification is a separate,
recorded laboratory obligation, not a universal software-release blocker. Existing `v0.3.0` remains its original
research pre-release. A stable software development baseline is neither a
reproducible laboratory release nor a physically qualified experiment.

No release or merge is automatic. Stage 3 must have its own reviewed,
Windows-validated implementation. See [release policy](RELEASE_POLICY.md),
[installation](INSTALLATION.md) and [safe updates](SAFE_UPDATES_AND_LOCAL_WORK.md).
