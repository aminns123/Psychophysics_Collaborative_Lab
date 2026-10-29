# Main-baseline startup recovery hotfix

This is a focused port of PR #170 onto approved `main` at
`93efe9cdc1e868b2898186b6f44f5482a2c72944`. It includes no Wave 1 experiment
migration and changes no scientific, stimulus, TUI or recording definitions.
See [startup recovery](STARTUP_RECOVERY.md) for the common implementation and
failure/choice rules. Final exact-head smoke, regression and CI evidence belongs
in this hotfix's PR; a report generated before its final commit is not sign-off.

## Review of PR #170

The Windows job for PR #170 completed with 2,436 passed, one skipped and four
failed. Each failure is an obsolete authoring guard on the two experiments
migrated in PR #169. Recovery regressions passed. A separate `develop` test-only
correction records the two explicitly approved source hashes, retains the old
frozen source and AST checks, and keeps deterministic current/frozen scientific
comparisons. Those experiment/test changes do not belong in this main hotfix.

One diagnostic wording correction is included: a nonzero exit during the reported
startup phase is a **startup failure**, not necessarily an unhandled crash (for
example, invalid command-line input also exits nonzero). This changes only native
diagnostic classification/text, not acquisition, saved data or retry decisions.

The real qualified-source smoke also exposed an import-path defect masked by
pytest's configured root path: launching the application with `-I` hid the
reviewed repository's top-level `simulations` package. Application launch now
uses `-E -s -B` with that validated source as cwd, preserving normal source imports
while ignoring ambient Python variables and user-site packages. All application
launch paths reuse one argument helper; the read-only qualification subprocess
still uses `-I` unchanged. No package reinstall, Python-path environment override,
recording change or new execution engine is introduced.

## Deployment decision and limits

Keep PR #168's native host and its existing locked setup. Do not add a host cache,
binary downloader, Python selector, installer engine or policy override merely
to change deployment. The source batch compiles that same reviewed native source
using the Windows .NET Framework compiler, then runs read-only checks. It does
not run pip or provisioning. Repeated compilation creates temporary executable/
compiler-log files but does not repair an environment or change scientific files.

This source route requires .NET Framework's compiler and permission to execute
the resulting native host in the user's temporary directory. The available
Windows computer has the compiler and a **non-elevated** token. The real batch
regression also launches under a child Windows PowerShell process with
`Restricted` policy, without running a script file or changing machine/user
policy. Compilation itself is not governed by PowerShell script-file policy.

This is a bounded, viable source/development route on that Windows profile; it
is **not** a claim that per-launch compilation is suitable for every managed
student computer. AppLocker/WDAC, antivirus rules, missing .NET components,
blocked temporary executables, network-folder restrictions and custom ACLs are
not universally qualified here. Do not weaken those policies to start PsyCoLab.
An administrator must approve a deployment route for such machines. Existing
fixed-version native executables/shortcuts remain supported and do not compile
on ordinary launch; source updates do not overwrite them. They are not silently
upgraded to this hotfix. Public distribution/signing remains separate.

If the native bootstrap fails, its plain native message/compiler log gives the
administrator a specific restore/check route. If even the Windows native support
is unavailable, console guidance is the last fallback. There is no arbitrary
automatic correction for every restricted computer.

The legacy laboratory record lacks modern qualification evidence. It must remain
unchanged: neither working packages nor absent metadata establish approval.
Recovery recommends a retained installation only after its own checks pass. A
source-compiled host has no sealed installer resource, so loose cached wheels do
not enable an install button. Without a verified retained version or complete
approved setup package, diagnostics/administrator guidance is the safe action.

## Acceptance matrix

| Requirement | Evidence / decision |
| --- | --- |
| Healthy repeated startup, no setup/menu | Actual batch/host regression; real qualified-source smoke required on final head |
| Broken application Python | Native diagnosis before Python execution; final-head native legacy smoke required |
| Standard non-elevated Windows account | Available token is not elevated; compiler and batch are exercised without elevation |
| PowerShell script restrictions | Actual batch tested with process-only `Restricted`; no script-file bypass |
| Fixed-version identities/shortcuts | Existing source-seal/read-only checks retained; never rewrite old executables, records or shortcuts |
| No protected scientific/laboratory changes | No official experiment/stimulus/TUI/recorder diff; disposable roots for runs; read-only legacy evidence inspection |
| Full Windows regression, portability, CI | Require final results in the PR before recommending merge |
| Separate managed student account / AppLocker-locked computer | NOT VERIFIED |
| Independent workstation / independent student acceptance | NOT VERIFIED |

The available computer is the previously tested workstation. Native Windows
interaction and real-process smoke are useful software evidence, not an
independent researcher acceptance test or physical apparatus qualification.

## Integration after explicit maintainer approval

1. Review the separate test-only guard correction against `develop` independently.
2. Merge this hotfix PR into `main` only after explicit approval and protected
   Windows checks pass. No branch protection bypass, tag or installer publication.
3. Prepare a normal **merge of the actual updated `main` into `develop`** on a new
   synchronisation branch/PR. This preserves Wave 1 and shares the actual main
   recovery ancestry, even if the maintainer used a squash merge for the hotfix.
4. Do not merge/cherry-pick PR #170 separately, and do not merge all of `develop`
   into `main`. PR #170 retains review history and is superseded as an integration
   route. The approved hotfix is the one recovery implementation.

The synchronisation is conditional on approval and merge. It is not performed by
this preparation task, and no later experiment migration wave starts here.
