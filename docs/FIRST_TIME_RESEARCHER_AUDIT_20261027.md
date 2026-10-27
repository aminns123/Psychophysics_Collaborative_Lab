# First-Time Researcher Usability Report — 27 October 2026

This is a scripted researcher-workflow audit, not a human-subject usability study
or perceptual validation. Intake was main
`c81b1db74d995c867c0b846e9aced35dfaafadcc`. The audit started from README,
Learn/help and the CSF guide before detailed implementation inspection. Evidence
combines an actual Windows entry-point keyboard session and Textual pilot tests
at 80×24, 120×40, 130×50 and 160×55; not every scenario was repeated through a
native graphical desktop driver.

The intended novice task was: choose CSF and display, set background and grating
geometry, choose a contrast method/repetitions, understand Review, edit the right
input, preserve choices, save/reload, attempt a safe test and inspect data.

## Ranked findings

### 1. P1 — Resolved width appeared independently editable in Python (repaired)

**Where:** `settings_review.review_rows`, `review_files.targets_for_rows`,
`review_authority.authority_for_row` and `ReviewScreen`.

**Reproduce:** select circular CSF, set diameter 1° and fade 0.1°; retain a
stimulus snapshot width 7° or refresh a Python width default of 5°. Inspect both
experiment diameter and resolved stimulus width.

**Before:** duplicate-looking width rows offered different file destinations.
Changing the Python default did not alter the experiment-controlled result;
the interface did not make the overriding input clear.

**Expected/fix:** resolved `size_deg` is Experiment-controlled, routes to
`aperture_diameter_deg`, and is not an independent renderer setting. Selected
details give meaning, units, actual value, status, source and Configure route.
The same mechanism covers existing bindings and extension-declared control
links, without hard-coded experiment IDs. Gaussian sigma/cutoff, line geometry,
teaching stimulus bases and a new local length field were exercised.

An additional Refresh trap was repaired: selecting an already-selected class
defaults item does not necessarily fire a change event. **Adopt current class
defaults** now explicitly replaces the retained snapshot. Class defaults are
also available when the stimulus provides a default JSON; that named JSON stays
the normal initial preset. Tests verify that adopting a base default changes
an editable orientation size while circular CSF's experiment diameter still wins.

### 2. P1 — Sidebar Review silently discarded the current draft (repaired)

**Where:** `LaboratoryNavigation.on_button_pressed`.

**Reproduce:** Review → Edit selected value → frequency list `2,nan` → F6,
Tab, Tab, Enter (sidebar Review). Repeat with valid `2,4`.

**Before:** navigation popped to an existing Review underneath Configure and
showed the old `2,8`, rather than applying or rejecting the current values.
This was reproduced through the actual Windows entry point.

**Expected/fix:** sidebar Review invokes Configure's normal collection and
validation. Valid values apply; invalid values remain on the editable screen
with feedback and can be corrected. Regression cases cover both inputs at
80×24 and 120×40. A longer-term dirty-draft navigation policy for every editor
would be useful, but no automatic save of scientific Python is proposed.

### 3. P2 — Response guidance choice reset on edit-and-return (repaired)

**Where:** `ExperimentConfigScreen.on_button_pressed`.

**Reproduce:** uncheck Show response-key guidance, edit a selected value and
return to Review. The request previously reset to `True` because a replacement
`SetupRequest` used its default.

**Expected/fix:** preserve the explicit choice when returning to the same
Review. The regression asserts both the setting edit and the retained false
guidance flag. Researcher override qualification is not silently transferred.

### 4. P2 — Small-terminal workflow still requires considerable scrolling (open)

**Where:** `PsyCoLabSetupApp.compose_content`, `ReviewScreen.compose_content`,
shared `CONSOLE_CSS`; Issue #140.

**Reproduce:** launch at 80×24. Initial Setup shows action buttons and run-mode
prose; experiment/display choices are below the first viewport. Configure's
source/JSON actions precede its scientific inputs. Review has substantial
readiness/context text before the table.

**Expected:** a novice should see the selected experiment/display and next
scientific action promptly. **Current mitigation:** sidebar and keyboard routes,
smaller Review table, selected-row details and expanded table. All four expanded
actions now fit a two-column toolbar. Long labels and the advanced source column
still need scrolling; full details remain available rather than shortening units.

**Proposed:** a separately reviewed content-order change putting selection and
editable science first, with advanced actions collapsed. Do not reorder the
entire calibration workflow during this repair. Keep #140 open for this and
native laboratory acceptance.

### 5. P2 — Advanced source activation can still surprise beginners (partly repaired)

**Where:** `ReviewSettingsTable`, `ReviewTableFullscreen` and field help; #140.

**Reproduce:** select a value and press Enter or double-click. Existing behavior
opens/exports an advanced source file rather than starting a TUI edit.

**Current improvement:** a prominent Edit selected value route and explicit
instructions distinguish these actions; scientific meaning is no longer in a
very wide prose column. **Remaining proposal:** evaluate changing the primary
activation to TUI editing after maintainer review of the established source-link
workflow. This PR preserves source-navigation compatibility.

### 6. P2 — The learning guide begins as an authoring guide (open)

**Where:** `docs/LEARN_PSYCOLAB.md`, section 1; #140/#82.

**Reproduce:** follow Learn as a researcher who only wants to configure an
existing CSF. Its first action is opening `stimulus_library.py` to draw a
stimulus. This reinforces the mistaken belief that ordinary parameter editing
requires Python.

**Expected/proposed:** a short Run an existing experiment path before stimulus
authoring. Link the new `REVIEW_PARAMETER_AUTHORITY.md` and show Configure →
Review → Edit → save/reload, including the difference between a selected preset
and an updated Python default. Preserve the existing authoring material.

### 7. P2 — Raw missing-component warning is easy to misattribute (open)

**Where:** `_internal/contributions.load_authored` / catalogue diagnostics;
Issues #128/#123.

**Reproduce:** start this checkout: a previously published component references
missing `new_probe_vertical_line_stimulus.py`. A warning names a source path before
the TUI. All ten official experiments still load and their synthetic matrix runs
pass; the warning does not establish the cause of the collaborator's native exit.

**Expected/proposed:** retain the isolation and actionable component identity,
but present a clearly scoped Draft/missing-source diagnostic with supported
restore/retest steps. Do not instruct deletion of unrelated files or silently
mark missing/unreviewed code Ready. Reconcile the historical publication entry
only with maintainer-approved component history.

### 8. P2 — Terminology needs task-level explanation (partly repaired)

**Where:** ConfigField help, Review details, CSF guide; #140/#82.

**Reproduce:** ask what changes when sigma, cutoff, diameter, fade, digital
peak-to-peak contrast, repetitions, reversal completion or a safety ceiling is
changed. Field units/ranges are present, but related consequences span several
panels. Thirty field names previously lacked scientific help. This PR adds that
metadata in the declarations: every official experiment field now has help,
without changing its values, constraints or execution. This includes the initial
one-down **accepted-response** limit, which also ends at the first incorrect
response; it is not a reversal-count limit.

**Current findings:** circular diameter/fade have clear angular definitions;
sigma is Gaussian spread, not support radius; cutoff sets finite support;
digital commands are not optical contrast. Fixed repetitions multiply every
scientific condition and level. The ceiling can stop before threshold convergence.
Software Ready, monitor binding, physical qualification and researcher override
are different statuses. The unbound test preflight explains how to recover.

**Proposed:** short per-study worked examples connecting each input to a visible
or analytical consequence, plus an explicit no-threshold explanation for short
teaching runs. Do not relabel digital quantities as measured contrast.

### 9. P2 — A native range error contains an incorrectly encoded dash (open)

**Where:** scientific validation feedback displayed by Configure; #140.

**Reproduce:** in the actual Windows entry point, enter circular CSF frequencies
`2,nan` and choose sidebar Review. The repair correctly blocks progression, but
the displayed permitted range includes `0.5â€“32` rather than a readable dash.
The numeric limits remain understandable; this is not evidence of changed bounds.

**Proposed:** trace whether the incorrect encoding originates in the source
message or terminal rendering and correct that boundary with a focused Windows
display check. Avoid a repository-wide character substitution.

### 10. P3 — Compact selected-parameter inspector could reduce repeated navigation (open)

**Where:** `ReviewScreen` and `ReviewTableFullscreen`; #140.

**Reproduce:** compare a long scientific description with an effective value in
an 80-column terminal. Fullscreen removes the sidebar and provides the same
authoritative rows, but the selected details consume much of the vertical area.

**Proposed:** evaluate a dedicated parameter-detail view or a collapsible
description, with an always-visible Edit action. Avoid adding more wide columns
or a second independent configuration model.

## Task outcomes and acceptance limits

The final automated path selects the experiment, reads effective Review rows,
follows the controlling input, changes it and verifies the effective value on
return. Gaussian sigma and circular diameter are saved/exported and JSON-reloaded;
line-position, orientation and teaching dimensions use the stimulus TUI editor.
A custom external experiment uses the same route. Conflicting Python defaults,
stimulus JSON and experiment settings remain correctly distinguished.

Thirty same-process method transitions across all ten experiments passed.
Existing full-suite cases additionally cover presets/reuse, failed JSON/Python
reload preservation, checkboxes/confirmation cancellation, researcher overrides,
unrelated invalid component isolation, run browsing/analysis and calibration
gates. Those are automated software cases, not newly performed hardware checks.

Native fullscreen presentation did not proceed because the isolated profile was
unbound. No physical calibration or human acquisition was performed. The final
manual checklist is in [the scientific stress audit](SCIENTIFIC_STRESS_AUDIT_20261027.md).
The collaborator's `0xC000041D` remains unverified on that machine; retain #123.
No release candidate recommendation follows until #82's deployment, recovery,
ownership/licensing and apparatus-qualification gates are accepted.
