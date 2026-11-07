# Review: which setting controls the presented stimulus?

Review uses the selected experiment's real planning and `prepare_stimuli` path.
The table shows effective values for one representative trial, with a short
authority/status. Select a row for scientific meaning, units, selected base,
source and **Where to change**. Use **Edit selected value** for the controlling
Configure field or the stimulus TUI editor. Enter or double-click on a parameter
does the same. Expand table provides the same
information in a full-terminal view. Advanced source/JSON navigation remains
available explicitly; it is not the normal way to configure a study.

Review works from each study's declarations and planning functions. The
specialised bright-probe explanation appears when the study uses the shared
digital-increment convention, declares the required log-step controls, and
supplies the condition and contrast-bound hooks. The four official ellipse and
line studies retain this explanation for their supported methods. Independent
studies with their own intensity and background controls receive their own
declared fields and meanings.

**Save configuration**, **Export JSON…** and **Import JSON…** beside the table
share the complete selected experiment/stimulus configuration in portable
schema 2. Import previews values and differences before approval. Dedicated
scientific editors retain authority. The recipient keeps local calibration and
participant information. See [Sharing configurations](SHARING_CONFIGURATIONS.md).

Use **Show parameter group** to focus the list. **Full parameter details / F2**
opens the complete selected row in a scrollable, soft-wrapped view, including
declared ranges and choices; Escape returns. Hover also shows the explanation.
F2 provides full text in Configure, the input/stimulus editors and authoring
information views. Display/calibration snapshots and original protocol text are
read-only; the selected method's Run plan explains its actual execution.

In the stimulus editor, **Use these values** retains the draft. Then
**Apply to Review** validates the complete experiment and saves explicit edits
in the existing `parameter_files/<experiment>/<slot>.json` format under local
configuration. An existing different file is preserved and a new versioned JSON
is selected. Review, Test, Run and provenance use that saved selection.
No named preset or Python edit is required. **Save preset** remains optional.
To restore a saved selection after restarting, use the stimulus selector's
**Local experiment** JSON choices. Starting from class defaults still uses the
original defaults until a local selection is chosen.

The last table column and **Open selected file** retain explicit advanced
JSON/definition inspection. Editable class-default parameters point to local
JSON export, not to the shared Python class. Develop rendering implementations
through **Build Stimuli → Open stimulus_library.py**. See the
[configuration/authoring boundary audit](audits/local-stimulus-configuration-20261105.md).
Derived geometry and trial-controlled values are explanations, not independent
editable inputs. The [parameter audit](audits/parameter-accessibility-20261105.md)
includes ellipse axes, intensity definitions and scientific decisions left open.

Experimental Test/Run windows hide the OS cursor and restore it on close/error;
the TUI cursor remains visible. Mouse-response implementations retain an explicit
visible-cursor choice. See [native Windows cursor verification](audits/presentation-cursor-20261105.md).

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

**Reload files and review** rereads the saved JSON linked to the run and
validates the complete replacement before applying it. Reloading the same
selected files and saving derived edits carry the original import history
alongside current values and file hashes. Selecting an independent preset or a
different stimulus drops the earlier origin for that slot. **Refresh (F5)**
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
