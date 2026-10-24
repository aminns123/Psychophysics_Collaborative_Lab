# Review table — one authoritative value, expanded view and source navigation

**Scope:** researcher-facing Review presentation and source navigation only. This change does not alter stimulus generation, staircase transitions, thresholds, trial timing, monitor calibration, participant responses, acquisition schemas or experiment defaults.

## 1. Duplicated staircase rules

The prior Review included the same selected `ConfigField` values under **Adaptive**, **Adaptive scale → Response rule**, and `Run plan → adaptive_rule`. The repeated rows made the table harder to read.

Review now presents an editable **Adaptive** row for each selected control (n-down, n-up, log step up/down, reversal count, initial one-down stage, etc.) and omits the matching derived copy. The derived **Run plan** section still includes distinctive scientific meaning and resolved outputs such as the threshold estimator/rule, asymptotic interpretation and other metadata.

Crucially, if an experiment's own `initialise_experiment` yields an **effective value different from the selected setting**, Review explicitly shows `Effective <planning key>` as a read-only row, with a note explaining the mismatch. It never hides a meaningful scientific discrepancy to cosmetically remove duplicates.

The difference-from-background and other derived contrast calculations remain explanatory rather than a second configuration.

## 2. Expanded table

From Experiment → Review choose **Expand table**.

A standalone **full-terminal table view** opens *inside PsyCoLab*, without the left sidebar or other Review panels. It retains:

- All five existing columns and the same authoritative Review rows.
- Independent table scrolling (vertical/horizontal), mouse selection, Enter and double-click to open an existing scientific source or local JSON.
- **Open selected file**, **Reload saved files**, **Back to Review**, and **Esc** to close.
- A location/status hint for the selected row.

The expanded screen is intentionally not a second source of truth: it mirrors the original Review table, delegates file editing/reload to Review, and returns the selected cursor row on exit. A separate operating-system terminal was not introduced because it would create a second application process with the risk of stale drafts or divergent configuration state.

## 3. Jump near the selected definition/value

- **Python:** existing source navigation finds a `ConfigField` declaration, stimulus class parameter or planning function via AST. VS Code uses `--goto FILE:LINE`.
- **Experiment JSON:** opening a selected editable field now locates the matching key **inside `values`**, not an identically named entry in `parameter_info`.
- **Stimulus JSON:** opening a field locates the key **inside `parameters`**.
- **Unsaved selections:** Review first creates an ordinary user-owned working JSON with existing validation/provenance behaviour, refreshes the source link, then navigates to the precise field.
- **Fallback editors:** only editors supporting line navigation (e.g. VS Code) can guarantee jumping to a line; basic Notepad may open the correct file at its beginning. Compact/one-line or unusual JSON formats may also fall back to line 1.

All edits still require **Save** in the editor followed by **Reload saved files** in PsyCoLab; actual runs use the resulting validated snapshots.

## Verification

Relevant tests:

```cmd
.venv\Scripts\python.exe -m pytest -q tests\test_review_adaptive_settings.py tests\test_review_scrollbar_and_run_plan.py tests\test_review_fullscreen_and_source_jump.py tests\test_review_file_navigation.py tests\test_laboratory_console.py
```

Focus on a real Windows terminal: open Review, verify each staircase value appears only once, expand the table at a narrow and wide terminal size, independently scroll it, open a JSON adaptive setting and confirm the editor lands on the value. Change the value, save, reload from the expanded view and verify the normal Review table displays the updated value; Esc returns to the same Review session.

**Testing status:** these regression tests have been added or adjusted but were not executed in the assistant's container because there was no checkout or network access to GitHub. Do not claim a pass until the local Windows environment runs them. The previous unrelated full-suite failures should be evaluated separately.
