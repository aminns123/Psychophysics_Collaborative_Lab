# Issue #82 — reproducible Windows installation and safe updates

**Approved plan, recorded 26 October 2026.** Start from the
[accepted development baseline](ACCEPTED_SOFTWARE_BASELINE.md), commit
`5fec547ecf3f86cd6bbd202a9e463637deca07d3`. The reliability-repair phase is
complete. Earlier Issue #82 references to 12 or 23 baseline failures describe
older revisions; they are not current release blockers.

The five stages below are separate, independently reviewable PRs. Stage numbers
are plan stages, not GitHub PR numbers. **This PR implements stage 1 only.**

| Stage | Scope | Dependencies and acceptance |
|---|---|---|
| **1 — Baseline documentation and release evidence** | Record the accepted commit/environments, reconcile Issue #80 and active release/install documentation, preserve historical evidence. | Documentation review and link/evidence checks; no new wording tests or runtime changes. Remains subject to PR review. |
| **2 — Editable-install identity repair** | Address confirmed source `0.3.0` / installed metadata `0.2.2` mismatch in the existing setup/validation path. | Use stage 1's reproduction evidence; add a targeted isolated regression for changed source version with unchanged pyproject. Do not reinstall the live environment automatically. This is the next task. |
| **3 — Reviewed Windows constraints and launcher integration** | Select an approved x64 Python 3.11 distribution/patch; pin runtime/transitive, bootstrap/build and separate development dependencies; validate environment identity on setup, reuse and recovery. | Build on stage 2's identity handling. Review complete versions/artifact hashes and how constraints affect optional lab requirements. Preserve user requirements; no new package manager or architecture. |
| **4 — Real fresh-install acceptance** | Exercise the existing launcher/setup using disposable full checkouts and empty environments; verify imports, source/package identity, catalogue, a short synthetic validation, repeat launch and failure recovery. | Uses the stage 3 environment specification. Reconstruct twice and compare inventories, then record an independent Windows workstation rehearsal. CI's direct `pip install -e .[dev]` and mocked launcher tests are not substitutes. |
| **5 — Safe update/rollback rehearsal and versioned release guidance** | Test old/new pinned checkouts with separate environments and copied lab/config/archive fixtures; record preservation, readiness, archive compatibility and recovery steps. | Uses stages 3–4's accepted environments; can draft guidance earlier, but must validate it before sign-off. Retain old installation, protect newer observations and document downgrade boundaries. |

Stages 2–5 are planned, not implemented by this documentation change. No
scientific equations, stimulus rendering, experimental defaults, UI appearance,
calibration, participant data or established architecture are changed here.

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
Its remaining manual work is only the current-readiness/native-editor handoff.
Do not repeat the completed extension audit. Broader installation/update/
rollback acceptance belongs to stages 4–5, not a new extension feature project.

Keep [Issue #82](https://github.com/aminns123/Psychophysics_Collaborative_Lab/issues/82)
open for the five-stage evidence, licensing/ownership and third-party
attribution decisions, the claimed physical experiment/apparatus scope, and
maintainer approval of a new version/tag. Existing `v0.3.0` remains its original
research pre-release. A stable software development baseline is neither a
reproducible laboratory release nor a physically qualified experiment.

No release or merge is automatic. Stop after stage 1; stage 2 requires its own
reviewed implementation task. See [release policy](RELEASE_POLICY.md),
[installation](INSTALLATION.md) and [safe updates](SAFE_UPDATES_AND_LOCAL_WORK.md).
