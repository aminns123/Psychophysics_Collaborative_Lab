# Guided Windows installation and retained versions

Status: private qualification candidate for Issue #82, not a released installer.
This workflow requires rights clearance, authenticated delivery and independent
student acceptance before public distribution. No installer download is currently
promised by this document. The working Git/batch installation remains supported.

## Decision and alternatives

| Approach | Assessment |
| --- | --- |
| Instructions around Git, Conda and the current batch file | Keeps current provisioning but fails the demonstrated student usability requirement. |
| Frozen single application executable | Would change editable-source identity, extension discovery and native dependency packaging; unnecessary new qualification. |
| MSI/MSIX or an installer engine with an in-place updater | Adds packaging, signing, elevation and update machinery before these are needed; in-place updates endanger retained environments. Consider institutional deployment wrappers later. |
| Native Windows setup, complete offline package, separate version directories | Selected. Uses Windows' existing .NET Framework 4.8 and the existing locked Python setup. Installation and launch are separate actions; old versions remain addressable. |

The small native host is necessary before Python exists. It contains no science,
TUI controls or Python execution engine. A maintainer builds it with Windows'
existing C# compiler. Students need neither a compiler nor Git, Conda or Python.
The provisioning tool is internal and never becomes a student prerequisite.

## Student workflow after an approved package is available

1. Obtain the complete package through the laboratory's authenticated delivery
   channel. Extract the whole folder using Windows Explorer, then double-click
   `PsyCoLabSetup.exe`. Do not open it from inside the compressed folder.
2. Keep the proposed software folder, or use **Browse**. New students leave the
   optional laboratory settings and participant-data fields blank. These use
   each student's Local AppData and Documents folders respectively.
3. Choose **Install separately**. Setup verifies all packaged artifacts, creates
   a new version and reports whether it passed the locked checks. No commands,
   dependency choices, hashes or environment approvals are requested.
4. Choose **Open selected version**. Use **Create shortcut** to save a shortcut
   bearing the version label. Subsequent ordinary launches use that shortcut.

An update is another reviewed complete package, opened deliberately in Setup.
The three choices are **Install separately**, select a retained version and
**Open selected version**, or **Cancel**. There is no automatic update, Git pull,
global active-version pointer or replacement of an existing shortcut. A shortcut
always selects the same installation identity. Keep the previous shortcut until
the new software has been accepted by the laboratory.

Cancellation during a provisioning step waits for that step to finish safely.
It never promotes the incomplete attempt. Failed attempts and their logs remain
for diagnosis; they do not appear as launchable installations. Retry creates
another new identity. Setup has no delete/uninstall action.

If verification fails, select a retained version or cancel and contact the
laboratory administrator with **View setup log**. Obtain a complete reviewed
package again if files are missing or changed. Never disable validation, edit
the setup record, approve a mismatch, or overlay another environment.

## Existing laboratories and teaching computers

Existing checkouts, `.venv`, `USER_env`, batch files and their shortcuts are not
adopted or modified. Retain them and their original paths. A Git update of a
developer checkout is not an update to an installed package snapshot.

The optional settings/data fields point to existing external roots; setup does
not copy, migrate, delete or change their contents. Settings retain extension
root pointers and calibration records. Installation does not copy or create
software Ready approvals. Existing Test → Ready, source invalidation and
calibration safeguards continue to apply. Extra dependencies in a laboratory's
existing USER_env are not silently installed in a standard package environment:
continue using the previous installation until a separately reviewed compatible
profile is available. Test new software using copied archives/settings before
sharing live roots. Returning to old software does not roll back observations.

For managed teaching computers an administrator installs into a new, protected
software store, then provides the version-specific shortcut with read/execute
access to students. No elevation is requested on ordinary launch. Leave the
optional roots blank for per-student configuration/data; a shared lab must make
its writable-root policy explicit. The launch gate writes diagnostics to the
launching user's temporary directory, not the software directory. Actual
separate-account ACL/deployment acceptance remains required; this candidate
does not configure Windows permissions or install a system service.

## Installation identity and validation

Each attempt has a new GUID directory created at its final absolute path:

```text
Installations/
  .psycolab-installations.json
  versions/<identity>/
    source/                 complete tracked source snapshot, editable .venv
    python/                 own approved interpreter, never relocated
    provisioner/            attempt-local package cache
    setup.log
    incomplete.json         attempt evidence, retained after success
    installation.json       written only after verification
    PsyCoLab.exe            version-specific native launcher
```

Setup checks the complete package SHA-256 inventory before allocating an
attempt. The exact manifest is embedded in the native host; editing the external
manifest cannot approve altered payloads. The host itself requires authenticated
delivery/signing rather than a circular self-hash. It rejects path traversal, linked folders, overlapping software/data
roots, nonempty unmanaged stores and inconsistent inventories. Conda receives
only local explicit artifacts, uses an attempt-local cache and does not register
environments globally. The existing `launcher_setup.py` installs locked wheels
offline and the source editably. Exact interpreter/native fingerprint, installed
file integrity, inventory, artifact reports, source identity and pip checks must
pass before `installation.json` is written.

Ordinary launch seals the packaged source, rejects added source files and uses
`launcher_setup.py --check`. This is a read-only gate: no installation, metadata
repair, state refresh or dependency resolution. It starts the installed TUI only
after the checks pass. Inherited environment overrides are removed; configuration
and data roots are passed only to the child application. Source and environment
checks detect accidental changes; they are not a security boundary against an
attacker who can replace the launcher and its manifests. Publisher authentication,
signing and protected institutional installation directories are separate gates.

## Exact existing profile and provisioner

Application artifacts remain the 19 interpreter packages and 25 runtime/build
wheels in `requirements/windows-cp311/`; no version or scientific lock changed.
Python is conda-forge 3.11.15 `h0159041_1_cpython`.

`packaging/windows/bootstrap.json` pins conda-standalone 25.7.0
`h57928b3_0`, container SHA-256
`1cc7702b0d1c5173e00054d380d98e978e91e15bfcfc8f4e1593edb197a718d4`,
and extracted executable SHA-256
`147e07937bb6509b69e9630eec6c6a281cd916c246d5fa5851a8b8f3b502f31f`.

Micromamba 2.10.0 was investigated and rejected for this profile: its generated
pip/wheel launchers differed from the accepted interpreter native fingerprint.
The guard correctly refused that attempt. Standalone Conda 25.7.0 reproduced the
accepted fingerprint without weakening the guard.

## Maintainer implementation and qualification plan

1. Review this native host and `--check` compatibility; run targeted Windows tests
   and the complete Windows source suite.
2. Build a **private** candidate with `scripts/build_windows_candidate.py` from
   the reviewed checkout and approved artifact cache. Its build toolchain needs
   Git, the Windows C# compiler and conda-package-handling; students do not.
   Downloads require deliberate `--download-reviewed` and exact pinned hashes.
   The builder refuses to overwrite existing output and records the source commit,
   dirty status and full file inventory. It has no publication or signing mode.
   For maintainers only, from the reviewed source checkout:

   ```powershell
   python scripts/build_windows_candidate.py --output C:\PsyCoLabBuild\Candidate --cache C:\PsyCoLabBuild\ReviewedArtifacts --label "Reviewed qualification candidate"
   ```

   These are build-tool commands, never student installation instructions.
3. Repeat first install, native opening, shortcut launch, cancellation, corrupt
   package/environment refusal and retained-old recovery on an independent
   Windows 11 workstation without developer tools. Confirm no network is needed
   after the authorized complete package is obtained.
4. Complete [redistribution review](WINDOWS_INSTALLER_LICENSING.md), authenticated
   delivery/signing and managed-computer acceptance before producing a public
   installer. A final approved package must come from a clean reviewed commit.
5. Qualify actual approved old/new release pairs and archive compatibility in
   Stage 5. This candidate's bounded retained-instance tests do not complete it.

See [the qualification record](WINDOWS_GUIDED_QUALIFICATION.md) for observed
results and remaining gates. Physical laboratory qualification is separate from
software distribution; no display, photometric, input or audio timing claim is
made by installer tests.
