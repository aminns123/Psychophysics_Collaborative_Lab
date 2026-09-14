PsyCoLab TUI event-routing hotfix
================================

Observed failure
----------------
Textual traceback:

    NoMatches: No nodes match '#setup-status'

on the final review screen.

Cause
-----
Textual Button.Pressed messages bubble upward. The ReviewScreen handled its
Back/Run button, but the same event then reached PsyCoLabSetupApp. The root app
immediately queried '#setup-status', a widget that exists only on the first
setup screen. On the review screen that query necessarily failed.

Fix
---
- Review/config screen buttons now stop propagation when handled.
- The root app ignores button IDs it does not own BEFORE it queries root-screen
  widgets.
- UI-handler exceptions are also sent to PsyCoLab's crash-report writer, because
  Textual may handle callback exceptions internally before the outer Python
  exception boundary sees them.
- No experiment, staircase, stimulus, timing, calibration, or data semantics are
  changed.

Apply
-----
Extract this ZIP over the root of Psychophysics_Collaborative_Lab and allow the
matching setup.py file to be replaced.

Then run:

    .venv\Scripts\python.exe -m psychophysics_lab

Go through the TUI to the final review page again. Clicking Back or Run should no
longer raise NoMatches. If another UI callback error occurs, PsyCoLab will print
it and make a best-effort crash report in .psycolab_logs.
