# Universal Experiment Configuration and Review

The same Configure and Review screens serve official and independently
authored studies. Experiment files declare researcher-editable `ConfigField`
values, stimulus slots and planning functions that the interface can inspect.

## Before Review: universal setup versus scientific edits

- **Configure** groups common controls such as method, run limits, trial count
  and seed where declared.
- **Review** opens the scientific input and stimulus editors. **Adaptive
  settings / Constant stimuli** hold the active method's controls.
  The fixed-level repetition count means *presentations per strength level per
  scientific condition*. Conditions can be spatial frequency, position,
  orientation, ellipse ratio, ring presence or arbitrary researcher-defined
  experimental quantities.
- Open **Edit inputs / stimuli** for named study sections such as timing,
  conditions and stimulus settings. Apply valid edits to Review.

## Review: what each cell means

The Review table identifies the **selected experiment and ID**. Every field
shows its value and units; the **Scientific meaning / origin** column draws
from the experiment's public `ConfigField.help_text`, Python/default JSON
provenance and the actual stimulus renderer and slot.

Selecting a parameter shows its value, explanation and controlling source.
Press Enter, double-click or use **Edit selected value** to reach the
controlling editor. Use **Open selected file** for advanced source or JSON
inspection. **Reload files and review** validates selected saved files before
using their new values.

Review reports derived geometry, clipping, local intensity limits, conditions
and planned timing where the selected study supplies the required declarations.
For example, the bright-probe explanation appears for the official ellipse and
line studies using their declared log-step controls and planning hooks.
Independent intensity fields use the same generic table and their own meanings.

Save local settings and preview portable imports from Review. See the
[configuration workflow](CONFIGURE_REVIEW_BOUNDARY.md),
[parameter authority](REVIEW_PARAMETER_AUTHORITY.md) and
[portable schema 2 guide](SHARING_CONFIGURATIONS.md).

### For authors of new official or local studies

Declare readable `ConfigField.label`, `units`, `help_text` and optional
`section`. Put the scientific equations, temporal experiment sequence and
controlled-strength meaning in the experiment/stimulus file, not inside TUI
widgets. Nothing needs to be added to a central CSF parameter table.

## Acceptance

Native Windows tests must include CSF, line/flanker, ellipse, teaching
orientation and a local extension. For each: modify a collapsed study field,
Review, Back, modify, Review, save/reload, run a short synthetic trial, test
invalid fields and demonstrate experiment switching without stale state.
Controls must not be hidden without a reachable way to edit them.
