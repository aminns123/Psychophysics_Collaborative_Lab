"""The declared scalar input shared by normal and recovery parameter editors."""

from textual.widgets import Input, Select


def parameter_value_widget(field, value, *, widget_id, help_text=None, allow_blank=False,
                           options=None, disabled=False):
    settings = {"id": widget_id, "disabled": disabled, "tooltip": help_text}
    if field.kind == "choice":
        if options is None:
            options = [(str(choice), choice) for choice in field.choices]
        if value is not None:
            settings["value"] = value
        return Select(options, allow_blank=allow_blank, **settings)
    return Input(value="" if value is None else str(value), **settings)
