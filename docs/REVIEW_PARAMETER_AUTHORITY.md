# Review: which setting controls the presented stimulus?

Review uses the selected experiment's real planning and `prepare_stimuli` path.
The table shows effective values for one representative trial, with a short
authority/status. Select a row for scientific meaning, units, selected base,
source and **Where to change**. Use **Edit selected value** for the controlling
Configure field or the stimulus TUI editor. Expand table provides the same
information in a full-terminal view. Advanced source/JSON navigation remains
available explicitly; it is not the normal way to configure a study.

Use **Show parameter group** to focus the list. **Full parameter details / F2**
opens the complete selected row in a scrollable, soft-wrapped view, including
declared ranges and choices; Escape returns. Hover also shows the explanation.
F2 provides full text in Configure, the input/stimulus editors and authoring
information views. Display/calibration snapshots and original protocol text are
read-only; the selected method's Run plan explains its actual execution.

In the stimulus editor, **Apply for this run** keeps a validated selection
without saving a preset. Then **Apply to Review** validates the full experiment
and updates Review. **Save preset** remains available for reusable selections.
Derived geometry and trial-controlled values are explanations, not independent
editable inputs. The [parameter audit](audits/parameter-accessibility-20261105.md)
includes ellipse axes, intensity definitions and scientific decisions left open.

The actual pipeline first resolves experiment settings and the selected stimulus
snapshot (a validated JSON preset or copied Python defaults), then the experiment
supplies its trial overrides to `run.stimulus_parameters`. Those overrides win.
Review's new control links only explain that relationship; they never change
validation, acquisition, rendering or saved observations.

For circular CSF, **Circular grating aperture diameter** is the editable input.
The grating's resolved `size_deg` is marked **Experiment-controlled** and routes
back to that same field. Changing a Python `size_deg` default or a stimulus JSON
does not change the diameter selected in the experiment. Gaussian CSF similarly
routes its effective sigma and cutoff to the corresponding experiment settings.
Trial-controlled frequency/strength rows describe a sample; their conditions and
method settings determine later trials. Other stimulus-base inputs remain editable
through the stimulus TUI editor, including line dimensions and teaching geometry.

**Reload files** rereads the saved JSON files currently linked to the run and
validates the complete replacement before applying anything. **Refresh (F5)**
starts a fresh process with updated Python definitions while preserving selected
experiment settings and stimulus snapshots. To adopt a new stimulus class
default, press **Adopt current class defaults** in Review's input/stimulus editor. This explicit action
also replaces a retained defaults snapshot when the selector already says
Stimulus class defaults. An already
selected run value is not silently overwritten by a changed Python default.

An extension can declare review-only links alongside its scientific definition:

```python
stimulus_parameter_controls={"target": {"length_deg": "my_line_length_deg"}}
```

The real `prepare_stimuli` must pass that experiment setting to the renderer.
Links must reference declared slots and fields, and should be regression-tested
against an actual presented-trial record. These are separate from the existing
`stimulus_field_bindings`, which participate in acquisition resolution. Review
combines existing bindings with explicit review-only links without guessing from
coincidentally equal values. Unlinked dynamic values remain clearly trial-controlled.

The selected-row explanation distinguishes a retained stimulus snapshot from the
current Python default, and shows whether the experiment transforms a base value.
Source inspection remains useful for scientific algorithms, response definitions
and new stimulus development. Software preview and Review do not qualify physical
contrast, photon timing or participant equivalence.
