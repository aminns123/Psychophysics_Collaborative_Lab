# Researcher stimulus configuration — 5 November 2026

Baseline: develop `0843338`; main `22fd7cc`. Neither protected branch is changed
directly. This is a focused repair to Review activation and local configuration.

## Finding

ProbeLine already declares `length_deg` and `width_deg`, and the generic TUI
editor already passes both to the existing renderer. The problem was the
researcher route: Enter/double-click opened a file, and unchanged class-default
rows linked to shared stimulus Python with instructions to edit it. The previous
Apply action retained only an in-memory snapshot until a run or explicit export.

The same target rule applies to all official experiments' editable unbound
stimulus parameters, including grating envelopes, teaching geometry and fixation
appearance. This is a common presentation/persistence issue; no duplicate
experiment-level dimension fields are needed.

## Corrected workflow

Select ellipse_centre → Review → select probe length/width → Enter or
**Edit selected value** → **Use these values** → **Apply to Review**.
The complete existing validators and actual planning path run before saving.
Selected dimensions are saved in local configuration under
`parameter_files/ellipse_centre/probe.json`, using the existing stimulus JSON
schema and declared class fields. Existing different files are preserved through
the existing versioned-export mechanism. The selected filename is shown in
Review and its bytes are checked before Test/Run.

The same selected snapshot feeds Test, Run and saved-run provenance. Local JSON
choices are available in the existing stimulus selector after a restart. A fresh
selection of class defaults still means class defaults; no saved local file is
silently substituted. Named presets and advanced JSON editing remain available.

Enter/double-click now configures inputs in both Review table views. The final
column/Open selected file remains explicit advanced inspection. Editable
class-default rows export local JSON. Shared Python implementation editing stays
in Build Stimuli and is clearly labelled as authoring. Derived, fixed and
trial/experiment-controlled values keep their existing authority and validation.

## Verification and compatibility

All ten official experiments are checked for editable stimulus routes to JSON
rather than Python. Native TUI tests cover small/expanded tables, both probe
dimensions, invalid complete configurations, fresh-app reload, preserved older
JSON files, concurrent-change detection and explicit source authoring. The real
ellipse test also exercises renderer geometry, Test handoff, synthetic execution
and exact saved configuration/provenance from the selected JSON.

No shared stimulus class, experiment definition, default dimension, adaptive
arithmetic, historical fixture, scientific data format, calibration record or
installation record is changed. Existing advanced JSON reload/source-inspection
tests retain their assertions, using the explicit file column for file actions.
Full native and Windows CI results are recorded in the PR; no automatic merge.
