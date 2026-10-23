# Slate Precision — Design E page refinement

This is the visual follow-up to [Design B's Laboratory Control Console](laboratory_console.md). The **same permanent sidebar**, F6 navigation, existing page IDs, forms and callbacks are kept. This work changes researcher-facing spacing, contrast, grouping and content placement only.

## Visual tokens

| Role | Colour |
|---|---|
| Workspace | `#101923` (near-black slate) |
| Main panels | `#1b2937` (graphite slate) |
| Sidebar/header | `#172431` / `#182634` |
| Selected navigation / primary action | `#246b8c` / `#236e90` (restrained cyan-blue) |
| Neutral border | `#344b5d` |
| Primary text | `#e2ebf3` |
| Secondary text | `#afc2cd` |
| Ready | `#5ca991` border |
| Attention | `#c2954d` border |
| Invalid input | `#c66b70` border |

Colours are for **researcher navigation and communication**, not calibrated stimulus pixels, monitor photometry or participant display output. The semantic readiness indicators retain distinct meaning beyond colour.

## Page composition

- **Setup, at 100 or more terminal columns:** edit the participant, experiment, monitor and working data directory in the wider left panel; inspect recent activity, experiment summary and monitor readiness in the narrower scrollable right panel. Both panels retain their established widget IDs, values, callbacks and validation.
- **Setup, below 100 columns:** the editable form and context pane stack vertically. Both scroll independently; neither is removed from the interface.
- **Review:** selected mode, optional response guidance and scientific settings are visually grouped. The existing full-width settings table, calibration requirements, launch controls and researcher override remain in their original functional workflow.
- **Data:** headings separate run selection, source files and derived analysis. All existing file actions and canonical-data functionality remain as before.
- **Experiment/build/calibration/stimulus pages:** inherit shared slate backgrounds, restrained buttons, section cards and clearer focus/highlight cues. Seven calibration stages and their visibility logic are unchanged.

This PR intentionally does **not** implement a new data model, local experiment loader, alternate stimulus authoring workflow, settings override mechanism, or Git update process. Those require an independent compatibility and provenance review.

## Verification and limitations

Focused tests live in `tests/test_slate_precision_layout.py` and exercise terminal sizes **60×24, 80×24, 120×40 and 160×55**, form/control preservation, moving between main routes, Review guidance and calibration access. The pre-existing `test_laboratory_console.py` remains the Option B navigation baseline.

Use the repository's existing Python 3.11 check commands:

```bash
python -m pytest tests/test_slate_precision_layout.py tests/test_laboratory_console.py
python -m pytest
python scripts/portability_check.py
git diff --check
```

GitHub CI covers Windows and Linux, but it cannot inspect a physical display, lab photometry or actual acoustic/visual timing. **Visually inspect Setup, Review, Data and all calibration stages on the target Windows terminal before accepting this design.** Do not infer hardware qualification from headless tests.

The pre-design main branch also has 12 known failing test cases documented in `laboratory_console.md`. Any full-suite failures must be compared by test identity with that baseline before attributing them to this PR.
