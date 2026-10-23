# Coffee & Forest — researcher page-layout refinement

**Proposal following Slate Precision (Design E).** Applies to the **researcher-facing Textual TUI** only. The Option B permanent sidebar and existing scientific workflows remain in place.

## Goals and decisions

The supplied Windows screenshots show the layout is close to the desired state but that some actions fill entire rows, groups of buttons are unevenly arranged, large free-text fields dominate the workspace, and scrollbars can visually touch the content. A warmer theme is preferred.

| UI element | Design rule |
|---|---|
| Sidebar | Remains permanently on the left, with F6 keyboard focus and existing navigation |
| Researcher palette | Dark coffee/espresso background, muted forest-green selected controls and panel edges, warm light text |
| Ordinary Input/Select | Maximum **76 terminal columns**, shrinking on narrower screens, rather than forcing full-content width |
| Ordinary body actions | Maximum **38 terminal columns**, consistent height, stacked vertically in logical groups |
| Primary navigation/launch controls | Stay in fixed action strip (not in the document's vertical scroll); preserve existing IDs and handlers |
| Info panels | Dark brown/olive-gray surfaces with restrained borders; no invented readiness colours |
| Scrollable forms | Right padding separates text from scrollbar; scroll only where content exceeds available height |
| Setup page | Keep the existing two-column wide layout and stacked compact layout; no change to values |
| Build Stimuli / Experiments / Help | Add concise section labels and group existing buttons without changing their actions |
| Calibration | Preserve all seven workflow stages, readiness labels, fixed next/previous/navigation controls and measurement functionality; leave its detailed forms scrollable |
| Review | **Keep the full parameter/condition table**, clickable source/JSON editing, response guidance, launch controls and current saved/requested values |
| Configure | The legacy 'Stimulus conditions' Collapsible already has `display=False`. Its underlying fields are deliberately retained for compatibility and run-value resolution, while the Review table remains available for researchers to inspect/edit each parameter. Do not delete those fields to achieve visual simplification |
| Participant fullscreen display | Completely outside this CSS and screen-layout change |

Colours are **not** physical stimulus intensities and do not certify luminance, timing, output precision or calibration readiness. Green/amber/red safety semantics remain meaningful and explicit.

## Scope and verification

Files changed: `ui/coffee_forest.py` (a small presentation override), `ui/setup.py` (load the style and add section headings), and focused tests for widths, stacked actions, routing and Review. Scientific source files, registries, calibration calculations, adaptive methods, run formats and external file paths are not touched.

**Recommended manual Windows validation before merge:** check Setup, Build Stimuli, Build Experiments, Configure, Review, Calibration (all seven stages), Data and Learn/Help at approximately 60×24, 80×24, 120×40 and normal maximized-window sizes. Confirm no important control is clipped, the action-strip controls remain stationary, all dropdowns can open, the Review table still provides access to the selected scientific parameter/source, and F6/sidebar navigation works. Specifically check long calibration text, long source paths and narrow-window button labels.

Focused headless test file: `tests/test_coffee_forest_layout.py`. Existing baseline files: `tests/test_laboratory_console.py` and `tests/test_slate_precision_layout.py`. CI availability may be limited; **do not infer a test pass** without actual execution. Preserve and compare the twelve established pre-existing failure names if a complete suite is run.

This is a **visual-only proposal**, separate from [the international laboratory roadmap](INTERNATIONAL_LAB_ROADMAP.md) and issues #80–#82. It does not implement external extensions, data migrations or releases.
