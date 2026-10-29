# Guided Windows candidate: qualification record

29 October 2026. Scope: software rehearsal on the existing Windows 11 x64 host;
not independent-workstation, novice-human, production-distribution or apparatus
qualification. Base main `3d7ee022946d6c5d5236f8de5bcc847e9df63f14` has
[successful Windows CI](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/40778655511).
All work used a separate checkout/environment and disposable installation store.

## Observed acceptance evidence

| Case | Outcome | Evidence / boundary |
| --- | --- | --- |
| Exact approved offline artifacts | PASS | Existing profile unchanged: 19 interpreter packages, 25 runtime/build wheels. Standalone Conda 25.7.0 reproduces accepted native fingerprint; existing setup checks pass. |
| Fresh native installation | PASS, rehearsal | Actual Windows Forms **Install separately** action, progress and successful completion observed. Earlier version remained listed. No student commands entered in a terminal. |
| Separate version-specific shortcut | PASS | Native Save dialog and success observed; resulting shortcut targets that installation's executable and `--launch` identity. No global version selector. |
| Repeat read-only validation | PASS | Two actual installed-environment checks pass; qualified state bytes unchanged. |
| Changed or added source | PASS | Real installed snapshot modifications refused; restored original bytes pass again. A new module is rejected before execution. |
| Changed environment evidence | PASS | Changed artifact evidence refused without state rewrite; original evidence restored in disposable test only. No reapproval provided by setup. |
| Failed provisioner | PASS | Micromamba experiment rejected by unchanged native fingerprint guard; incomplete attempt never listed as launchable. Not selected for the implementation. |
| Cancel at provisioning boundary | PASS | Latest native engine leaves an incomplete diagnostic attempt with no successful installation record. Existing version remains valid. |
| Retained-old recovery | PASS, bounded | Existing installed profile validates after failed/cancelled attempts; all 17,271 files in retained instance match the pre-attempt snapshot. This is not qualification of an arbitrary older release/profile. |
| Native refusal and recovery choices | PASS | Altered disposable README refused with readable message: obtain complete reviewed package, use retained version, or cancel. Retained version selectable/openable. |
| Managed user preference separation | PASS in targeted tests | Explicit configuration root receives selected-data preference and lock. Legacy checkout pointer bytes are retained; no source-root lock written. Existing path remains the default without explicit override. |
| Existing source/batch and USER_env compatibility | PASS in targeted regressions | Existing setup remains; new `--check` never invokes provisioning or metadata repair. No scientific or TUI change. |
| Full Windows source regression / final PR CI | Required on PR head | Record final outcome in PR validation/checks. Hosted CI is not an exact-profile or native-human installation qualification. |
| Native experiment TUI / acquisition | NOT VERIFIED here | Setup UI is accessible; the console is not exposed by the control tool. A start-process handoff is not evidence that a student can operate the scientific interface. |
| Final revised native host | Software tests; native rehearsal limited | The observed install used candidate 4. Later changes tighten path/store and manifest checks, disable Browse while busy, honour launch cancellation, improve completion status and separate preferences. Latest engine recovery checks compile/use current C#; final fresh candidate qualification is recorded in the PR. |
| Independent Windows 11 workstation without tools | NOT VERIFIED | Another environment on this computer and hosted CI do not establish independence. |
| First-time student acceptance | NOT VERIFIED | No independent novice researcher operated the complete workflow. |
| Managed separate-account / read-only ACL deployment | NOT VERIFIED | Code uses a per-student writable root; actual administrator/student account exercise still needed. |
| Stage 5 actual approved old/new releases and archive compatibility | NOT VERIFIED | Keep separate from bounded retained-instance checks. |
| Redistribution / authenticated distribution | NOT CLEARED | See licensing review. No public installer produced. |
| Physical laboratory qualification | Separate | No luminance, contrast, geometry, photon/input/audio timing or protocol qualification claimed. |

## Chronological native rehearsal

1. Opened the private setup executable compiled from the isolated checkout.
   Inspected labels, optional existing-root fields and Install/Open/Cancel choices.
2. Chose a disposable installation store. The earlier qualified instance appeared
   in the retained list. No functioning laboratory root was selected.
3. Clicked **Install separately**, observed package validation and runtime/setup
   progress, then the successful-installation message and both listed versions.
4. Opened the new instance through the native control. The exact-profile gate
   passed and handed off to the existing application. Console operation was not
   counted as native researcher acceptance.
5. Created a version-specific shortcut through the native Save dialog and checked
   its target identity. Qualification settings/data pointers were deliberately
   isolated by the harness before opening; these were not live laboratory roots.
6. Changed only a backed-up README in the disposable instance. **Open** refused
   it with recovery guidance. Selected the retained earlier version and opened
   through the same control. Restored the disposable README's original bytes.

No independent human acceptance is inferred from this automation. Earlier
candidate binaries are private test outputs, not deliverable release artifacts.

## Reproducible automated scope

`test_launcher_read_only.py` covers valid, stale, malformed and missing evidence,
changed source identity/profile/specification/packages/interpreter, and no repair.
`test_windows_guided_setup.py` compiles the actual native source on Windows and
tests path containment/links, Unicode and quoted argument round trips, inherited
override removal, preflight failure/cancellation preservation, unexpected source
and failed-process diagnostics. It does not mock a second installer implementation.
`test_windows_candidate_builder.py` checks cache/download hashes, missing inputs
and output non-overwrite. `test_managed_installation_preferences.py` tests explicit
configuration-root isolation, legacy behaviour and authoritative data-root choice.
Existing launcher/profile, identity and USER_env regressions remain applicable.

The final PR must include these targeted results, its full Windows CI status and
the protected-root comparison. Hash consistency is not publisher authentication.
Future qualifications must use clean reviewed source and retain the exact package
manifest, installed identity, runtime evidence, logs and acceptance outcome.

## Release recommendation

Review the private candidate mechanism. Do not describe Issue #82 Stage 4 or the
student acceptance criterion as complete yet. Complete rights/trust clearance,
the independent no-tools installation exercise, actual native scientist workflow
and institutional account policy before distributing it to students. Keep Stage 5
release-pair rollback and per-laboratory physical qualification separate.
