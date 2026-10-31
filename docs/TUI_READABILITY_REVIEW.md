# Conservative researcher-interface readability pass

Baseline: develop `649b705`, identical science/source tree to main `179d32f`.
PR #181's separate startup/environment proposal is not incorporated here.

## Three directions for maintainer selection

These are faithful **concept mockups**, not native screenshots or evidence of
human acceptance. Example values illustrate the existing CSF declarations.

| Direction | Navigation and density | Decision |
|---|---|---|
| [A — Existing console](figures/researcher-experience/direction-a.svg) | Persistent sidebar, readable wrapping table, full selected-row details below | Only its conservative readability changes implemented |
| [B — Task-focused Review](figures/researcher-experience/direction-b.svg) | Top-level navigation, Review task tabs, details alongside medium-density table | Concept only; requires maintainer choice and further interaction qualification |
| [C — Laboratory worksheet](figures/researcher-experience/direction-c.svg) | Top navigation, denser worksheet, details below | Concept only; requires maintainer choice and narrow-screen assessment |

No new navigation model, theme, framework, experiment-specific interface or
participant display change is installed. Concepts B/C are not implemented.

## Before and after

| Before | After |
|---|---|
| Eight-character group column clips scientific group names | Wider group/value/authority columns, wrapped scientific labels and values |
| Five stacked Review buttons consume fifteen terminal rows at all widths | Same five actions in two columns on wide terminals; existing vertical stack below 100 columns |
| Long values require returning from expanded Review to find the complete selected value | Both Review views show the complete selected value and its actual source/authority |
| Missing/invalid drafts look like ordinary editable rows | Plain-text Missing required input / Invalid selected input status, with the same generic correction route |
| Authority distinctions require reading individual explanations | A short legend distinguishes editable, derived/trial-controlled and inactive values, and software Ready from apparatus qualification |

The actual table values and source targets are retained. Paths remain compact
links in the table and complete addresses in selected-row details. Horizontal
and vertical table scrolling and Expand table remain available. Wrapped rows
show fewer records at once; this is an explicit readability/density tradeoff.

## Page coverage and preserved behaviour

- Home, experiment selection and sidebar: inspected with software renders; same
  headings, keyboard routes, focus, participant draft and scrolling shell.
- Configure: universal setup only. Review still owns scientific details and the
  generic experiment/stimulus editor. CSF and both ellipse procedures use the
  identical screens; the independent laboratory fixture uses these screens too.
- Calibration/readiness: existing semantic status text and checks retained;
  software testing is explicitly distinguished from physical qualification.
- Build Experiments/Stimuli, source inspection, Test → Ready and Data: existing
  routes, source ownership, trust, fingerprints and recording remain unchanged.
  Onboarding text/examples are a separate PR.
- Errors, refresh, presets and drafts: no validation relaxation or alternate
  settings store. Invalid values remain editable; running still requires the
  existing validation. Source reload/F5 retain their existing distinct meanings.

Tests exercise real Textual widgets at 60×24 and 150×50, full-value expanded
Review, correction routes, existing source activation and draft/editor paths.
The existing geometry suite covers 60×24, 80×24, 120×40 and 160×55. The independent
project/external laboratory route suite retains custom-stimulus discovery,
both methods, presets/F5, source navigation, Test → Ready and invalidation.
Exact Windows/portability counts and CI links are recorded in the PR evidence.

PASS here means software behaviour only. Native novice usability, independent
student-account acceptance and physical apparatus measurements remain **NOT
VERIFIED** by software renders. No working installation, laboratory source,
configuration, calibration, participant record or qualification evidence is edited.
