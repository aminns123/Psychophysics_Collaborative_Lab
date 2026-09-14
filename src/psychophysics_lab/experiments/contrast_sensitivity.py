from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .spec import ConfigField, ExperimentSpec

LUMINANCE_CHOICES = (19.0, 29.0, 41.0, 49.0, 204.0, 255.0, 300.0, 322.0, 370.0, 403.0, 415.0, 500.0)
SCREEN_INTENSITY_CHOICES = (0.24, 0.294, 0.34, 0.374, 0.72, 0.8, 0.86, 0.89, 0.95, 0.98, 0.99)


def _validate(values: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    if int(values["n_down"]) < 1:
        errors.append("n-down must be at least 1.")
    if int(values["n_up"]) < 1:
        errors.append("n-up must be at least 1.")
    if float(values["logUNIT_UP"]) <= 0:
        errors.append("Up-step size must be positive.")
    if float(values["logUNIT_DW"]) <= 0:
        errors.append("Down-step size must be positive.")
    if int(values["reversal_termination"]) < 1:
        errors.append("Reversal termination must be at least 1.")
    if int(values["max_trials"]) < 1:
        errors.append("Maximum responses must be at least 1.")
    if not 0 <= float(values["Background_Screen_intensity"]) < 1:
        errors.append("Background screen intensity must be in [0, 1).")
    starting = float(values["starting_probe_intensity"])
    background = float(values["Background_Screen_intensity"])
    if not background <= starting <= 1:
        errors.append("Starting probe intensity must lie between background intensity and 1.0.")
    for key in ("timeFixate", "timeInterval", "timeAB", "timeT"):
        if int(values[key]) < 0:
            errors.append(f"{key} must not be negative.")

    return errors


CSF_SPEC = ExperimentSpec(
    id="contrast_sensitivity",
    display_name="Contrast Sensitivity Function (reference experiment)",
    description=(
        "Current reference experiment using the legacy Pyglet/OpenGL grating renderer "
        "and the repaired independent adaptive staircase implementation."
    ),
    legacy_module="Experiments.contrast_sensitivity_function",
    legacy_experiment_type="contrast_sensitivity_function",
    compatible_monitor_profiles=("legacy_reference_display",),
    fields=(
        ConfigField(
            "Max_monitor_Luminance",
            "Maximum monitor luminance (cd/m²)",
            "choice",
            default=None,
            choices=LUMINANCE_CHOICES,
            help_text="Legacy calibration choice. Select the value appropriate to the display/session.",
        ),
        ConfigField(
            "Background_Luminance",
            "Background luminance (cd/m²)",
            "choice",
            default=None,
            choices=LUMINANCE_CHOICES,
            help_text="Recorded legacy physical-luminance condition.",
        ),
        ConfigField(
            "Background_Screen_intensity",
            "Background digital screen intensity",
            "choice",
            default=None,
            choices=SCREEN_INTENSITY_CHOICES,
            help_text=(
                "Legacy normalised display command. The physical-luminance and digital-intensity "
                "lists are intentionally not auto-paired until calibration mapping is reviewed."
            ),
        ),
        ConfigField("n_down", "Correct responses required for a downward step", "int", default=2),
        ConfigField("n_up", "Incorrect responses required for an upward step", "int", default=1),
        ConfigField("logUNIT_UP", "Up-step size (legacy log units)", "float", default=0.35),
        ConfigField(
            "logUNIT_DW",
            "Down-step size (legacy log units)",
            "float",
            default=0.5488 * 0.35,
        ),
        ConfigField("reversal_termination", "Reversals required per staircase", "int", default=10),
        ConfigField("max_trials", "Maximum accepted responses (safety ceiling)", "int", default=30),
        ConfigField("timeFixate", "Fixation duration (ms)", "int", default=250),
        ConfigField("timeInterval", "Interval duration (ms)", "int", default=250),
        ConfigField("timeAB", "Stimulus duration (ms)", "int", default=200),
        ConfigField("timeT", "Response timeout (ms; 0 = self-paced legacy behaviour)", "int", default=0),
        ConfigField("starting_probe_intensity", "Starting probe digital intensity", "float", default=1.0),
    ),
    fixed_setup={
        # Preserved legacy CSF setup values. Their scientific meaning will be
        # reviewed with the stimulus layer rather than silently reinterpreted here.
        "trialPOINT": 9,
        "stimulus_SF": 1.0,
        "index_last_PosList": 0,
        "Npoints": 12,
        "positionBool": 1,
        "positionFind": 1,
    },
    validator=_validate,
)
