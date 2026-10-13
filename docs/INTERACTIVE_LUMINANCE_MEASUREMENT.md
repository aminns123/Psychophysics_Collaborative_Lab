# Luminance calibration: three researcher-operated ways to enter measurements

**Scientific boundary:** PsyCoLab controls a normalized grayscale digital
command but cannot determine the resulting physical luminance in cd/m² without
an external calibrated photometer. Screen geometry is not photometry.
Luminance collected here is stored as **unverified** measurement data until the
laboratory checks the actual screen, instrument, uncertainty and protocol.

Everything in this workflow is under the **machine-local calibration config**
(`calibration_sessions/`, `calibration_templates/`, `profiles/`); no raw
human-participant data or synthetic experiment trials are touched.

## Route 1 — Import an existing JSON table

Go to **Calibrate → 4 · Luminance**. Use the direct JSON path and **Import + SAVE real readings → Continue to Timing** button. The advanced profile editor remains an alternative.

Choose **Create/open example luminance JSON** if you need to see the format.
Enter measured pairs as an array of
`{"screen_intensity": 0.5, "luminance_cdm2": <your real meter reading>}`
objects. The instrument/method, date and notes are **recommended but optional**.
You must supply at least two real measured points; unused template rows may remain `null`.
The command is a normalized grayscale RGB value in **[0,1]**; the reading is the emitted light
in **cd/m²**. Neither is a percentage.

Paste the **absolute path** to the JSON file into the Luminance page and click
**Import + SAVE real readings → Continue to Timing**. Values are checked
against the selected monitor profile/revision and written to a new local revision.
Missing method/date/notes generate warnings, not save errors. The stage turns
green for **saved evidence**, while physical photometric verification remains
unverified until separately declared. Advanced editing offers draft → save.

Do not use fabricated example values as measurements.

## Route 2 — Fullscreen photometer measurement session

1. Select the local monitor in **Calibrate**, with verified physical dimensions,
   eye distance, OS resolution and correct monitor binding.
2. Set **Lowest intensity in interactive sweep** to the actual intended
   experiment background command (for example 0.25); it is a *digital
   command*, not luminance. The default uses the last experiment's
   `Background_Screen_intensity` when available. Set the arrow-key step,
   e.g. 0.05.
3. Click **Start interactive luminance measurement**. PsyCoLab closes the
   Textual interface temporarily, opens a fullscreen diagnostic on the
   selected bound monitor and shows a centred **6° × 6° square** in visual
   angle. The surround is black (digital 0). The square starts at command
   **1.0000**. The patch uses independent physical x/y pixel pitches, so
   its on-screen pixel widths may differ.
4. Position a calibrated photometer over the **central square**, not the dark
   border, the small label or a transition. At the very bottom-right,
   small/low-brightness text shows the command and editable cd/m² field,
   current repeat count and mean. The label does **not** replace the meter.
5. Type the actual meter value, such as `86.4`, and press **Enter**.
   Every Enter saves **one observation immediately**. Repeat at the same
   command as many times as useful; don't combine/average values mentally.
   PsyCoLab retains each sample and computes the mean and sample standard
   deviation for you.
6. Press **Left** to decrease command by the configured step, or **Right**
   to increase it, clamped to the specified floor and 1.0. A partially typed
   value must be saved or cleared before changing command; this prevents
   misattributing a reading to the wrong intensity. Press **Backspace** to
   edit the text input. Press **Esc** to finish.
7. On return to the TUI, the summary gives a path to **session.json**
   (individual readings with timestamps and exact monitor snapshot/hash)
   and **pilot_luminance.json** (mean per command, n, sample SD and the
   original repeated readings).
8. Click **Open pilot/test JSON** to inspect the actual measured values.
   Method, date and notes may be added at any time but are not import blockers.
9. On the **Luminance** page, paste the pilot JSON path and click **Import + SAVE**.
   After values are saved, the stage turns green and advances to **Timing**.
   That green status does **not** mean the photometry is physically verified.

Notes:

- The screen square can become very dim or black near the floor. Photometer
  aperture, ambient light and the monitor's dark-level processing matter.
- The bottom-right label is intentionally dim and outside the centre, but
  it is still emitted light: verify stray-light influences and restrict the
  meter's measurement field to the square. If necessary, use a laboratory
  method that accounts for dark surround contamination.
- One intensity with three repeated values is a legitimate **partial
  session**, but importing a calibration curve requires **at least two
  distinct commands**. Record other commands or edit the pilot appropriately.
- Each Enter is saved to `session.json` immediately. If the renderer
  unexpectedly crashes, previously saved raw observations remain. A
  newly started session always creates a new uniquely named folder.
- The pilot JSON can be edited after the fullscreen session ends. If
  changing screen geometry, monitor identity or software processing,
  confirm whether earlier luminance readings still apply; the JSON
  importer rejects files for a different monitor profile/revision.
- The mean is an arithmetic mean over repeats at the same command;
  `sample_sd_cdm2` is null when fewer than two readings are available.
  Preserving individual repeats is essential for later quality assessment.

## Route 3 — Pilot/test JSON file (no meter yet)

Click **Open pilot/test JSON** before taking measurements. If no previous
session exists for the selected display, PsyCoLab creates an example JSON
with **null** readings. It opens the latest session's editable JSON file if
available; otherwise an example is available for later measurement.

You can examine, edit and store this file as preparation for the lab.
**Do not replace null with guessed luminances**. When a photometer becomes
available, record real numbers through Route 1 or Route 2. You can reuse
the same import workflow after filling the file.

## What is saved, and what is NOT saved

- **Raw session:** each measurement, digital command, timestamp, software
  patch settings, and a snapshot/hash of the monitor revision.
- **Pilot JSON:** command-level mean, count, sample SD, individual readings,
  and links to the source session. This is deliberately *unverified* and
  can be imported without method/notes; missing metadata produces warnings.
- **Monitor profile:** the actual validated command-to-mean-cd/m² pairs
  and any optional method/date/notes supplied, only when you explicitly import
  and save another versioned local revision.
- **Never automatic:** laboratory photometric verification, uncertainty
  certification, display gamma correction, photon timing or experiment
  qualification. An imported pair is evidence of a user-entered
  measurement, not proof of instrument validity.

Hardware acceptance on Windows must check the actual 6° square and
keyboard controls. Headless CI can test the calculations, metadata,
JSON round-trips, input validation and file safety, **not emitted light**.

### Failed exports and partial sessions

`session.json` is the authoritative raw record. If saving the derived pilot
fails, the application says the raw reading was saved and shows an export
warning. **Open pilot/test JSON** rebuilds a missing pilot from that raw record;
it never replaces an existing edited pilot. Inspect partial/interrupted records
and complete instrument notes before import. Sessions with fewer than two
distinct commands are marked incomplete. Clear or save a partially typed
reading before Escape. Physical verification remains a separate review.
