"""Explain acquisition precedence and route edits to the controlling input.

Planning uses the experiment's real prepare_stimuli path. Explicit control
links describe that path; they never change acquisition or infer scientific
equivalence from two coincidentally equal numeric values.
"""
from .settings_review import parameter_controller, parameter_sources
from .config_sections import grouped_config_fields
from ..stimuli.registry import get_stimulus


def authority_for_row(spec, values, snapshots, description, row, target, sources):
    group, label, value, meaning = row
    fields = {f.key: f for f in spec.fields}
    field = next((f for f in spec.fields if group in {"Experiment", "Adaptive"}
                  and f.display_label == label), None)
    key = field.key if field else target.get("key") if target.get("kind") == "experiment_json" else None
    result = dict(status="Derived / scientific", route="Review → Edit inputs / stimuli",
                  edit_kind="configuration", field=None, slot=None, meaning=meaning,
                  explanation="Calculated by the selected experiment; this row is not an independent input.")
    if group in snapshots:
        stimulus = get_stimulus(snapshots[group]["document"]["stimulus_id"])
        parameter = next((f for f in stimulus.parameters if f.display_label == label), None)
        if parameter:
            key = parameter_controller(spec, group, parameter.key)
            base = snapshots[group]["document"]["parameters"][parameter.key]
            if not key:
                if parameter.key in parameter_sources(description, group):
                    result.update(status="Trial-controlled", explanation=(
                        "The experiment sets this value for each trial. Change its scientific conditions or "
                        "selected inputs in Review; editing a stimulus default will be overridden."))
                else:
                    result.update(status="Editable stimulus base" if parameter.editable else "Fixed definition",
                        edit_kind="stimulus" if parameter.editable else None, slot=group, field=parameter.key,
                        route=f"Review → Edit inputs / stimuli → {group} → {parameter.label}",
                        explanation=f"Selected base: {base!r}. Effective sample: {value}. "
                                    f"Current Python default: {parameter.default!r}. Source: "
                                    f"{snapshots[group]['file_identity']}. "
                                    "The selected snapshot/preset takes precedence over later Python default edits. "
                                    "Use Edit selected value for this run, or press Adopt current class defaults "
                                    "in the Review parameter editor to replace the retained snapshot with refreshed defaults.")
                    if parameter.key in description["overrides"].get(group, {}):
                        result["explanation"] += " The experiment reads this base and transforms it during trials."
                return result
            result["explanation"] = (f"Renderer input {parameter.key} is controlled by {key}. "
                "This resolved value is not an independent setting. Stimulus JSON and Python defaults "
                "do not override the experiment's selected controlling value.")
            result["status"] = "Experiment-controlled"
    if key in fields:
        field = fields[key]
        section = next((name for name, items in grouped_config_fields(spec)
                        if any(f.key == key for f in items)), field.section)
        result.update(edit_kind="experiment" if field.editable else None, field=key,
                      route=f"{'Configure' if section == 'Universal setup' else 'Review → Edit inputs / stimuli'} → {section} → {field.display_label}")
        if group not in snapshots:
            result["status"] = "Editable experiment" if field.editable else "Fixed definition"
            saved = sources.get("experiment")
            result["explanation"] = (f"Acquisition uses the current selected experiment setting {key}={values[key]!r}. "
                + (f"Matching saved experiment JSON: {saved}. " if saved else "Authority: current TUI/run selection. ")
                + "Changing a Python default does not overwrite this selected value. "
                "Use the generic input editor; advanced JSON editing remains available.")
        if key in description.get("inactive_fields", ()):
            result.update(status="Inactive for selected method", edit_kind=None,
                          route="Configure → Contrast selection method",
                          explanation=(f"{key} is retained but does not control this method's trials or estimator. "
                                       "Existing settings validation still applies; no value has been changed."))
    if group in {"Responses", "Trial action", "Audio", "Session start (once)", "Recorded measurements", "Saved data"} and not key:
        result.update(status="Scientific definition", edit_kind=None,
                      route="Advanced source inspection; response keys and timing inputs are editable above")
    return result
