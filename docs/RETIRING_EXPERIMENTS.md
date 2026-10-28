# Retiring a PsyCoLab experiment

Retirement is an **explicit, reversible change to active software eligibility**,
not deletion of scientific source or data. It does not rewrite recorded runs,
calibration, participant files, stimulus classes or historical presets.

## Researcher workflow

1. Open **Build Experiments** and select the researcher-authored experiment.
2. Choose **Retire experiment**. Review the exact ID, origin, current state and
   source path in the confirmation screen; **Cancel** or Escape makes no changes.
3. Confirm **Retire experiment**. The source remains intact but the experiment is
   no longer runnable/Ready. Press **Refresh (F5)** before selecting experiments.
4. If you want it back, select the retired entry in Build Experiments and choose
   **Restore retired**. This restores **Draft**, never Ready.
5. Run **Simulate / validate**, deliberately select **Mark Ready**, then Refresh.
   Confirm the effective stimulus/response parameters again before acquisition.

A retired experiment may remain listed in **Build Experiments** so it can be
restored. This is not the same as being listed among runnable experiments.

## Why deleting a Python file is different

Removing a source file is ambiguous: the file might be unintentionally lost,
an installation might be incomplete, or the researcher might wish to retire it.
PsyCoLab therefore keeps its missing-source warning for unexpected absence.
Use explicit Retire rather than deleting the Python file. If the source already
went missing, restore it from a reviewed backup/Git before resuming use.

Project-published researcher experiments maintain their status in
`authoring/components.json`. An explicit retired status prevents automatic
source rediscovery while leaving the Python file in the repository. Official
curated experiments cannot be retired through Build Experiments: maintainers
must use a reviewed Git PR and preserve protocol/archive compatibility.

Trusted external laboratory experiments use their own machine-local
`extension_readiness.json` status under the existing configured extensions
folder. They never modify the official repository publication manifest.
Restoration explicitly revokes Ready and requires fresh Test → Ready.

Removing a laboratory experiment from disk after retiring is a separate,
deliberate source-archiving decision. Keep the source in version control or a
scientific archive if you may need to reproduce historical experimental
behaviour. Saved run metadata and the public read-only run reader remain
available, but a source hash alone cannot reconstruct deleted code.

**Retirement does not affect a separately defined stimulus with a similar name.**
In particular, the retired `new_probe_vertical_line_stimulus` experiment is not
the `new_probe_vertical_line` stimulus.

## Acceptance boundary

Automated regression tests check cancellation, retirement, restoration and
non-destructive records. Native Windows TUI acceptance by a human and an
independent first-time researcher remain Stage 4 requirements. An automated
test pass does not qualify a laboratory display or scientific protocol.
