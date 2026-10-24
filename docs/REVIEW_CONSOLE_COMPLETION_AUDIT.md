# Completion audit — Review table, outside scrollbar and sidebar alignment

**Repository baseline:** merged PR #86, commit `12c4944b951ead424e6fe3e44266e3b0e894e80c` (24 October 2026).

The previous Work AI session was interrupted *after its implementation was committed* but during post-change checks. PR #86 was subsequently merged into `main`. The purpose of this follow-up is to check that implementation rather than replace scientific code with another design.

## Changes already present in merged PR #86

1. **Outer scrollbar separated from the content frame.** `console.py` introduces a `ConsolePanel` with four stationary border edges. The workspace owns the outside vertical scrollbar; the content keeps an internal margin. Review's DataTable still independently scrolls scientific rows/columns.
2. **Sidebar appearance.** The hierarchical `>`, `->`, `-` markers remain; buttons now request left text alignment and selected rows omit underline. Focus remains visually distinct.
3. **Adaptive run plan shown in Review.** `settings_review.py` groups selected editable adaptive `ConfigField` entries, identifies the adaptive algorithm and step parameterization, and appends read-only planning rows from the experiment's **own** `initialise_experiment` resolution. These include the actual selected n-down/n-up, log steps, initial phase, reversal limit, trial budget and declared threshold rule when that experiment provides them. No alternative adaptive formula or hidden model was introduced.
4. **Correct editing locations.** `review_files.py` routes editable adaptive field rows to the same experiment JSON workflow and planning rows to the defining Python source. Planning metadata is not misrepresented as a separate editable setting.

## Added completion regression

`tests/test_review_scrollbar_and_run_plan.py` renders Review at 60×24, 80×24, 120×40 and 160×55 and checks:

- The table remains inside the main content frame, without colliding with the frame.
- The outer scrollbar is in its distinct one-column rail with a separator.
- Selected adaptive settings match the values given to Review.
- The Run plan shows the corresponding scientifically resolved n-down/n-up, both log steps, reversal limit, initial phase and trial ceiling.
- Selected sidebar labels remain left-aligned, hierarchical and non-underlined.

The previously merged unit-level tests `tests/test_review_adaptive_settings.py` and shared shell checks in `tests/test_laboratory_console.py` are retained.

## Verification required before merge

Run using the supported Python 3.11 environment:

```cmd
.venv\Scripts\python.exe -m pytest -q tests\test_review_adaptive_settings.py tests\test_review_scrollbar_and_run_plan.py tests\test_laboratory_console.py tests\test_review_file_navigation.py
```

On Windows, open the actual Review page with a long table and inspect both scrollbar rails at a normal maximized terminal size and a smaller terminal. In particular, verify that the Review table can scroll horizontally and vertically, that the outer page scroll moves the surrounding content without moving the header/sidebar/footer, and that a selected adaptive value opens the correct editable experiment JSON file whereas a derived planning row opens its defining Python code.

**Tests added, not claimed run in this environment.** GitHub Actions for PR #86 were still in progress during preparation. Headless geometry checks do not replace a Windows terminal visual acceptance test.

## Protected scientific scope

This follow-up adds only a regression test and an audit note. PR #86 itself changed researcher TUI panel CSS/layout and Review source/description code, but did **not** change stimulus pixels, adaptive update arithmetic, stopping rules, monitor calibration, raw trials, saved run schemas or actual participant acquisition.
