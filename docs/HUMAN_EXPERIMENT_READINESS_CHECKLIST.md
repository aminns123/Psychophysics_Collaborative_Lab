# PsyCoLab: readiness checklist for a real human experiment

**Use this after Calibrate → Review.** A green calibration stage means that its
software/measurement *records were saved*. It is not the same as verified
physical calibration or qualifying a human experiment.

Your current status is shown live under **Experiment → Configure → Review →
Human experiment**. The amber-bordered **NEXT REQUIRED ACTION** and its
button point to the first unfinished prerequisite; previously completed
requirements are shown with a green edge.

## Follow these checks in order

- [ ] **Bind the actual monitor.** Detect the connected display, select it,
  save its fullscreen pixel resolution and refresh rate, and measure actual
  active-image width/height and eye distance (do not use the bezel size).
- [ ] **Review physical geometry.** Show the ruler bar, measure the physical
  displayed length in mm, record the discrepancy and accept Geometry only
  if your laboratory's criteria are met.
- [ ] **Review real luminance measurements.** Add at least two independent
  intensity/cd/m² pairs from a photometer for *this physical display*.
  Review the instrument/source record and explicitly verify Photometry.
  **Accepting a numeric mapping is not physical photometry verification.**
  Fake/synthetic example readings cannot qualify human acquisition.
- [ ] **Review physical photon timing**, if required by the experiment.
  Software frame/flicker tests alone cannot confirm photon timing; use
  an independent photodiode or equivalent physical evidence.
- [ ] **Check the expected fullscreen resolution and spatial sampling**
  against the currently connected monitor and requested cycles/degree.
- [ ] **Check the experiment's digital contrast and staircase parameters**.
  Select appropriate background and starting probe intensities; the
  program will reject unsafe shader commands rather than silently clamp.
- [ ] **Validate the experiment settings**, including selected monitor,
  stimulus conditions, session and recorded calibration-pair values.
- [ ] **Use a pseudonymous human participant ID** for real acquisition.
  Test presentations and virtual simulations use separate records.
- [ ] **Qualify the exact experiment/profile combination** after the earlier
  applicable checks pass. This is distinct from six green calibration tabs.
- [ ] **Return to Review and run the final human preflight.** Ready on-screen
  does not replace the actual hardware check performed at launch.

## Where to click

From **Experiment → Review**, choose **Human experiment**. The yellow NEXT
panel names the first incomplete check; select the button immediately below
it to open its relevant calibration, physical-verification, experiment
settings or qualification page. Make the change, save it, return to Review,
and repeat until the checklist is complete. This is more reliable than
guessing which green Calibration subsection to revisit.

For an **uncalibrated presentation test**, select **Test experiment
presentation** instead. It is the intended route for fake/example readings
and for checking stimuli and response controls without claiming the monitor
was physically measured.

## Interpreting errors

- **Saved but unverified:** values exist, but real laboratory evidence has
  not been independently reviewed.
- **Accepted mapping:** the researcher chose a numeric mapping; that alone
  does not establish that a real photometer was used.
- **Blocker persists after a save:** check that you saved the *physical
  verification* or *experiment qualification* declaration rather than merely
  finishing a diagnostic page.
- **Run fails after all checks are green:** read the terminal crash report.
  A software exception is a bug, not evidence that the calibration failed.

**Print or save as PDF:** open this Markdown file in GitHub and use the
browser's Print → Save as PDF. The live Review checklist remains the
authoritative summary of the current profile; this sheet is a manual aid.
