# Windows workstation acceptance checklist (before human acquisition)

PsyCoLab's headless tests validate calculations, structure and simulated event
handling. They **cannot certify** the screen shown on a physical Windows
workstation, calibrated luminance, response latency, or onset timing. Run these
checks on every materially different display/graphics workstation.

## A. Refresh local source and protect your local profile

After reviewing and merging the PR through GitHub, update your Windows checkout
using your usual Git workflow. Do not replace a working `local_psychophysics_config`
folder or the external `local_psychophysics_data` folder.

Open the project terminal with Python 3.11:

```powershell
.venv\Scripts\python.exe -m psychophysics_lab --diagnose
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\portability_check.py
.venv\Scripts\python.exe scripts\windows_display_preflight.py --profile legacy_reference_display
```

For an actual local display profile, supply its ID instead of
`legacy_reference_display`. The preflight only enumerates/selects OS monitor
objects; it does **not** draw a stimulus or write participant data. Retain the
output with local laboratory calibration notes if appropriate.

## B. Physically identify the display

1. Open **Display → Edit / copy display profile**, select **Detect connected displays**.
2. Physically identify each monitor, especially if multiple screens share the
   same pixel size or device ID. Do not assume monitor 0 is the desired display.
3. Check Windows **Display settings**: resolution, scaling (%) and refresh
   rate. Compare with `os_detected_screens` in the preflight report.
4. Use **Use detected resolution and refresh** only when those values are
   appropriate. Manually enter physical active width/height (measured with a
   ruler, excluding bezels) and viewing distance.
5. If Windows reports logical desktop pixels (e.g. 1536 × 960) while the
   actual panel/display mode is different, investigate DPI awareness and
   fullscreen framebuffer dimensions before running a participant. Do not
   silently reinterpret those logical values as physical framebuffer pixels.
6. Save a new numbered local profile revision; retain provenance showing
   whether each value was OS-reported, manually entered or physically verified.

## C. Display geometry

1. **Display → Size / ruler bar**: present a bar with a known physical length
   (e.g. 100 mm) on the intended monitor. Physically measure and record the
   result (in mm), along with the expected and realised pixel-rounded values.
2. Repeat horizontal and vertical tests, and an off-centre position test.
3. Check that reported fullscreen framebuffer dimensions match the physical
   target monitor. If not, stop and inspect Windows resolution/scaling and
   profile binding.
4. Try a sine grating below spatial Nyquist and confirm its apparent orientation
   and extent. This is a visual sanity check, **not** spatial-frequency
   calibration, and does not validate the reference legacy CSF 31.5 scaling.

## D. Timing and luminance

1. Choose one binary flicker rate exactly representable at the selected
   refresh rate (e.g. 10 Hz at 60 Hz nominal), plus an inexact rate.
2. Check the announced frame quantisation, observed intervals and possible
   dropped refreshes. OS/driver nominal refresh is **not** the same as measured
   stimulus photon onset.
3. Where scientific timing matters, use a photodiode or comparable instrument
   to verify physical transitions and dropped frames.
4. Use a calibrated photometer for screen command-to-luminance mapping, including
   background and maximum luminance. An OS-reported colour setting cannot
   prove physical cd/m².
5. Record calibration date, method, equipment and measurement status in the
   machine-local profile.

## E. TUI and human pipeline checks

1. At terminal sizes such as 80 × 24 and 100 × 30, navigate all pages. Verify
   that the navigation bar and Review/Run controls remain visible and the
   scroll area moves independently.
2. Edit a parameter, inspect another page and return; ensure the intended
   draft and saved presets remain unchanged.
3. Use up/down step-size buttons with a supported 2AFC rule and confirm only
   the requested paired step changes; unsupported rules must fail explicitly.
4. Open the real stimulus/experiment source in VS Code using the TUI.
5. Confirm that the Data page can display prior human and simulated runs
   from **one common external data root** while synthetic virtual IDs cannot
   be selected as human participants.
6. Run `python -m simulations --seed 123 --max-trials 120` with no display.
   Confirm output under `local_psychophysics_data/synthetic_123/...`, the
   synthetic marker, manifest and trial timestamps. Check that the human TUI's
   last selected participant remains unchanged.
7. Validate a synthetic run with `python scripts/validate_run.py <run_folder>`.
   This checks internal data consistency, not psychophysical accuracy.

Do not collect actual participant responses as an informal software diagnostic
until physical calibration and the local experimental protocol have been
approved. Record any failed item and fix it before a production run.
