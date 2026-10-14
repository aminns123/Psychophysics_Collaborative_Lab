# Follow-up audit: interrupted spatial-calibration Work session (2026-10-14)

**Source reviewed:** `main` at `266df7752f61171e63b1c7b4a4d4a5e0c044e81e`
("not finished work-ai update."). This note reviews the *pushed* commit; it
cannot discover unsaved files in the interrupted Work cloud/local workspace.

## Confirmed GitHub evidence

The interrupted Work session **did push** its proposed implementation to
`main` (15 changed/added paths, 860 lines added, 83 deleted). It introduced:

- `config/spatial_observation.py` — separate append-only observation files
  associated with immutable spatial diagnostic identities and content hashes;
- `config/calibration_progress.py` — successful presentation alone no longer
  satisfies Spatial; the latest compatible report requires a saved, visually
  consistent observation with no rendering abnormality;
- `ui/setup.py` — Spatial observation controls, calibration-navigation
  persistence/restoration and linked luminance-background selection;
- `config/background_mapping.py` and `core/runner.py` — a single current
  monitor's saved mean pairs and run-level mapping provenance;
- `tests/test_spatial_observations.py` and
  `tests/test_background_mapping_selection.py` — isolated regression tests.

The **Headless checks** GitHub Actions run for this exact commit
[38558948955](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/38558948955)
completed successfully on **Windows and Ubuntu** (732 tests passed on each;
portability check passed on each). This establishes the mocked/headless
software result, **not** optical frequency, luminance, actual fullscreen
keyboard or physical timing performance on the lab PC.

## Focused source review

1. `run_geometry_check` records the spatial *presentation* and its own
   diagnostic UUID. The separate `record_observation` function checks the
   recorded report's monitor identity/physical setup and appends an assessment
   without rewriting the diagnostic report. A repeated unchanged Save is a
   no-op. The UI offers review of individual presentation reports.
2. `calibration_progress` uses the latest compatible spatial report and
   considers Spatial complete only with a visually consistent response and
   `abnormality == "none"`. Uncertain, discrepant and non-assessed responses
   are retained without a green Spatial stage. It explicitly reports
   `physical_spatial_frequency_certified=False`.
3. Fullscreen launch buttons persist a one-shot `calibration_navigation`
   containing the active subsection, monitor and draft test settings.
   `app.py` no longer auto-advances Spatial/Timing after presentation.
   `_restore_diagnostic_review` in `ui/setup.py` attempts to reconstruct
   the Calibration screen on return, with special handling for entry from
   Experiment Review. Failures are recoverable and do not automatically
   certify or qualify a monitor.
4. `mapping_choices` reads a single selected monitor's committed active
   dataset and verifies its physical snapshot and mean pairs match the
   profile; the experiment selector can fill both background fields
   together. Changing the monitor or active measurement identity requires
   explicit confirmation. Synthetic methods/observations remain test-only.
   Starting probe intensity remains a distinct adaptive parameter.
5. A hardware failure, desktop/window-manager-specific key behaviour, an
   operating-system termination, and physical photometric/temporal accuracy
   are **not proven** by these source/headless checks. These remain lab tasks.

No confirmed regression requiring a scientific-code alteration was identified
in this source-level follow-up. The documentation previously still described
old Spatial green-state semantics and manual comma-separated experiment-ID
qualification; those passages are corrected in this review branch.

## Acceptance check on the actual Windows monitor PC

**Before testing:** close any participant session; do not use a genuine
participant identity or alter existing participant data. Save/inspect the
selected physical monitor's profile and record the Git commit, monitor ID,
profile revision, observed framebuffer resolution/refresh, physical active
width/height and viewing distance. Use a disposable diagnostic session.

From a PowerShell window in the repository:

```powershell
git rev-parse HEAD
.venv\Scripts\python.exe -m pip check
$testDir = Join-Path $env:TEMP ("psycolab-calibration-" + [guid]::NewGuid().ToString("N"))
.venv\Scripts\python.exe -m pytest -q --basetemp=$testDir
.venv\Scripts\python.exe scripts\portability_check.py
```

Then manually check:

- [ ] In **Calibrate → Spatial**, launch a 5° grating at 1 cpd below Nyquist,
      noting the chosen orientation and the selected display. Confirm that
      closing with Esc/Enter returns to **the same Calibrate → Spatial** page.
- [ ] Confirm a new report is visible and Spatial is not marked complete
      merely because fullscreen presentation succeeded. Check the report's
      nominal cycles/actual resolved angular extent; nominally 5 cycles for
      5° × 1 cpd. Remember individual bright maxima are phase-dependent.
- [ ] Record **Uncertain** or **Discrepancy** on a disposable new report.
      Confirm the assessment is saved and Spatial is not green.
- [ ] Repeat the test, select **Yes — visually consistent** with
      **No obvious abnormality**, and click **Record observation**. Confirm
      Spatial becomes green for the new reviewed presentation and the page
      stays in Calibrate until **Next stage** is explicitly chosen. This is
      still **subjective observation, not physical certification**.
- [ ] Launch a size/ruler test, exit and confirm return to Geometry; enter
      the *actual* ruler measurement and confirm its signed error is shown.
      Launch Timing, exit and confirm return to Timing; check software flip
      summary without declaring independent photon timing.
- [ ] Launch a disposable interactive luminance session and exit; confirm
      return to Luminance, preservation of saved readings and separation
      from any physical-verification declaration. Do **not** enter invented
      values as measured photometry.
- [ ] Open **Experiment → Contrast Sensitivity → Display and contrast**.
      Select a row from **Background from this display's saved measurements**;
      verify both luminance and digital intensity are populated and match
      the actual saved means. Ensure repeated raw readings appear only as
      one mean choice per command, not as separate selectable backgrounds.
- [ ] Switch to a different saved display/mapping, if available. Confirm
      old scientific values are retained for review, not silently replaced
      with another monitor's calibration; deliberately choose a new pair or
      Manual. Return and reopen a saved configuration/preset to check its
      value/provenance consistency.
- [ ] Verify a synthetic photometry table is labelled test-only and cannot
      qualify human acquisition. Check that an unqualified session can use
      simulation or designated test presentation without masquerading as
      certified participant data.
- [ ] Reopen/leave Calibration and save unchanged settings. Verify no new
      monitor-profile revision was created. After a *deliberate physical
      configuration change* on a test profile, verify prior spatial
      observations become stale and cannot requalify that different setup.

**If any check fails:** record the exact screen, operating-system details,
profile ID/revision, diagnostic UUID, expected and observed behaviour, and
the external diagnostic/error-log path. Keep all existing calibration and
participant files; don't bypass preflight by changing Verified labels or
relabelling synthetic readings. Investigate the failing step with a targeted
fix and regression test before human acquisition.

## Remaining delivery boundary

The interrupted Work session did not publish its usual final handoff report or
separate PR. This review branch only corrects documentation and provides the
hardware acceptance plan; it does not claim physical testing or possession of
Work-only uncommitted files. Existing `main` includes the unfinished Work
commit, so do not reapply the entire feature from scratch.
