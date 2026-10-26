# Universal Experiment Configuration and Review

PsyCoLab's TUI is a general scientific experiment launcher. **It must not
assume the selected study is CSF.** Experiment files declare researcher-
editable `ConfigField` values and stimulus slots; the TUI presents them.

## Before Review: universal setup versus scientific edits

- **Universal setup** groups declared `contrast_method`,
  `background_intensity`, `starting_probe_intensity` or
  `starting_strength`, trial limits and trial-order seed where present.
  Their absence in a local study is valid.
- **Adaptive settings / Constant stimuli** hold the active method's controls.
  The fixed-level repetition count means *presentations per strength level per
  scientific condition*. Conditions can be spatial frequency, position,
  orientation, ellipse ratio, ring presence or arbitrary researcher-defined
  experimental quantities.
- **Experiment-specific parameters** and named study sections
  (`Stimulus conditions`, `Timing`, etc.) remain expandable and editable.
  **Experiment-specific stimulus parameters** retain their own public
  stimulus-library editor in a separate expandable section.
- The configuration shell shows concise validation. It does not derive CSF
  support radii, optical contrasts, ellipse overlap or other detailed
  scientific narratives; those belong in Review.

## Review: what each cell means

The Review table identifies the **selected experiment and ID**. Every field
shows its value and units; the **Scientific meaning / origin** column draws
from the experiment's public `ConfigField.help_text`, Python/default JSON
provenance and the actual stimulus renderer and slot.

Selecting a cell shows its study, group, parameter, value, explanation and
source. Enter or double-click opens the selected JSON or Python source where
supported. **Back** returns to Configuration, where expandable sections
remain editable. Saved file edits require the existing Reload + validation
flow before acquisition.

Calculated support geometry, clipping, local intensity limits, trial
conditions and planned timing are reported from the **actual selected
experiment/stimulus**; they are not hard-coded for CSF.

### For authors of new official or local studies

Declare readable `ConfigField.label`, `units`, `help_text` and optional
`section`. Put the scientific equations, temporal experiment sequence and
controlled-strength meaning in the experiment/stimulus file, not inside TUI
widgets. Nothing needs to be added to a central CSF parameter table.

This is a presentation change only: it does not modify scientific defaults,
configuration keys, external local run folders, calibration evidence or the
canonical 20-column `trials.tsv` schema.

## Acceptance

Native Windows tests must include CSF, line/flanker, ellipse, teaching
orientation and a local extension. For each: modify a collapsed study field,
Review, Back, modify, Review, save/reload, run a short synthetic trial, test
invalid fields and demonstrate experiment switching without stale state.
Controls must not be hidden without a reachable way to edit them.
