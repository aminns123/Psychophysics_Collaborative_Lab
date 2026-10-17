# Researcher testing workflow

The normal route is **Experiment → Configure → Review**, followed by **Try the
experiment**, **Simulate responses**, or **Collect participant data**. Each mode
uses the same selected experiment, stimulus snapshots and study settings.

## Visible previews and parameter editing

Build Stimuli previews a selected class's default parameters. An experiment's
stimulus panel previews its selected parameters. Preview renders a PNG and opens
the platform image viewer automatically; the form stays available. It uses the
existing renderer and introduces no new graphics dependency. A viewer failure
reports the saved image path rather than claiming it opened.

The plain parameter editor uses declared field types, choices, bounds and the
stimulus validator. Previewing unsaved values does not mutate the selected preset.
Save creates a new named local preset; existing files and shared defaults are
preserved. Direct file paths and JSON editing remain under Advanced.

PNG previews remain 8-bit appearance aids. They can collapse small contrast
differences and do not reproduce calibrated physical size or timing. Experiment
condition overrides are applied during actual trial preparation; a static preview
does not pretend to show them. Use physical testing to inspect the sequence.

## Physical tests without participant acquisition

The runner already had an isolated, marked presentation-test folder and reserved
identities. Modern experiment guards incorrectly rejected that mode as though it
were participant acquisition. That policy now lives in RunContext.initialise:
modern physical tests are permitted, participant blocks remain enforced, and
historical blocked procedures retain their restrictions.

Physical tests are **not synthetic**. They use the normal display/input backend,
actual trial builder, scoring and adaptive changes. The explicit test limit
(default eight responses, blank for full experiment) is recorded separately from
study parameters. At the next trial boundary it produces `test_finished`, after
accepted responses and adaptive state are durably saved. It does not set a
staircase complete, pad a trial count, change TUI adaptive controls or manufacture
a primary threshold. Escape preserves accepted responses and abort provenance.

Monitor binding, configured geometry, sampling limits, finite/gamut validation and
renderer support are still checked. Test presentation does not require full
photometric/timing qualification and does not modify verification records.
Collect participant data still uses the strict acquisition preflight.

## One setup route

Normal navigation no longer offers the competing Scenarios form. A compatibility
link redirects to the shared experiment setup with simulation selected. Review
shows the selected run action; calibration resolution is shown for participant
acquisition. Observer models, seeds and scenarios sit under optional settings.

The previous scenario editor remains only in explicit historical compatibility
mode and the established command-line tools. This preserves existing scripts and
historical test coverage without making a new researcher select between forms.

## Shorter scientific files

Five modern detection protocols now call shared recording helpers instead of
repeating the canonical state projection and counter-snapshot callback.
`adaptive_trial_record` records presented/next strength, repeat identity, trial
index, reversals and completion. `staircase_record_action` observes counters after
the experiment's explicit UpdateAdaptive action. Neither chooses conditions,
changes a strength, selects a stopping rule or chooses an estimator.

Each experiment still declares its stimulus strength, maximum allowed increment,
log steps, extra measurements, response scoring, contrast update, retention and
primary statistic. Fixed-trial and temporal structures remain distinct.
Historical procedures and frozen fixture files were not changed.

The short README and LEARN_PSYCOLAB guide are the normal entry points. Detailed
scientific specifications, calibration evidence and data contracts remain in their
existing reference documents.

## Verification scope

Tests exercise the real presentation-test runner with injected window/input
boundaries, all five modern detection protocols, a fixed-trial protocol, isolated
test storage, acquisition rejection, image export/open requests, typed parameter
editing, preserved presets, scientific estimation and historical traces. These
software tests do not certify a physical monitor or measure researcher usability.

## Completed verification

- Full regression suite: **1,025 passed**. Four warnings retain the existing managed custom-probe readiness gate; no component was silently republished.
- Final UI and learning-guide checks after the Help-page simplification: **23 passed**. Focused workflow/calibration checks and scientific trace checks also passed; these counts overlap with the full suite.
- Patch whitespace checks pass. Frozen historical fixtures were not edited.
- The four modern line/ellipse tasks show the configured response keys during the self-paced response stage. Timed stimulus geometry and adaptive settings remain experiment-owned.
- Python source edits require restarting PsyCoLab; parameter edits preview immediately. Source code is not hot-reloaded.
- Physical window/input boundaries and image-viewer launching were injected in automated tests. The actual laboratory display, viewer integration and photon timing still need a hands-on check.

Changes are uncommitted on refactor/researcher-test-workflow. Nothing was pushed.
