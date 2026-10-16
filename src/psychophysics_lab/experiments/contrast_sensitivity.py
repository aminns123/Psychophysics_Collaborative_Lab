from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from ..config.models import MonitorProfile
from .spec import ConfigField, ExperimentSpec
from ..adaptive import AdaptiveSelection
from .responses import LEFT_RIGHT

LUMINANCE_CHOICES = (19.0, 29.0, 41.0, 49.0, 204.0, 255.0, 300.0, 322.0, 370.0, 403.0, 415.0, 500.0)
SCREEN_INTENSITY_CHOICES = (0.24, 0.294, 0.34, 0.374, 0.72, 0.8, 0.86, 0.89, 0.95, 0.98, 0.99)

# These are the original (63,252) CSF renderer condition scalars.
# Never silently label these values calibrated cycles/degree.
DEFAULT_CSF_CONDITIONS = "2,8"
FREQUENCY_UNITS = ("cycles_per_degree", "degrees_per_cycle", "legacy_shader_radians")


def resolved_condition_frequencies(values: str, units: str) -> tuple[float, ...]:
    """Convert user-entered periodicity to canonical cpd, or retain explicit legacy."""
    parsed = parse_condition_values(values)
    if units not in FREQUENCY_UNITS:
        raise ValueError("Unknown spatial frequency unit.")
    if units == "degrees_per_cycle":
        return tuple(1.0 / period for period in parsed)
    return parsed


def _legacy_condition_defaults(values):
    # A saved pre-calibration setup with explicit legacy condition scalars
    # but no units must never be silently reinterpreted as cpd.
    d = dict(values)
    if "condition_values" in d and "condition_unit" not in d:
        d["condition_unit"] = "legacy_shader_radians"
    return d



def parse_condition_values(values: str) -> tuple[float, ...]:
    """Strict ordered numeric condition list; no empty/duplicate/nonfinite items."""
    if not isinstance(values, str):
        raise ValueError("Condition values must be comma-separated numeric text.")
    parts = [piece.strip() for piece in values.split(",")]
    if not 1 <= len(parts) <= 24 or any(not part for part in parts):
        raise ValueError("Provide 1–24 numeric condition values separated by commas, without blanks.")
    try:
        result = tuple(float(part) for part in parts)
    except ValueError as exc:
        raise ValueError("Each condition must be a numeric value in the selected units.") from exc
    if any(not math.isfinite(value) or value <= 0 or value > 10000 for value in result):
        raise ValueError("Every stimulus condition must be finite and in (0, 10000] in the selected units.")
    if len(set(result)) != len(result):
        raise ValueError("Condition values must be unique; use staircases per condition for repeats.")
    return result



def _folder_number(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".").replace(".", "p")


def _data_path_parts(
    values: Mapping[str, Any],
    monitor_profile: MonitorProfile,
) -> tuple[str, ...]:
    """Human-readable fixed run conditions for CSF acquisition.

    The current reference profile has no trusted encoded luminance-command
    mapping, so the background folder is visibly marked ``_unverified``.
    """
    max_luminance = _folder_number(float(values["Max_monitor_Luminance"]))
    background_luminance = _folder_number(float(values["Background_Luminance"]))

    background_folder = f"background_{background_luminance}cdm2"
    if not monitor_profile.has_verified_luminance_mapping:
        background_folder += "_unverified"

    return (
        f"max_{max_luminance}cdm2",
        background_folder,
    )


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
    if not 0 <= int(values["initial_one_down_limit"]) <= 1000:
        errors.append("Initial 1-down response limit must be between 0 and 1000 (0 disables).")
    try:
        parsed_conditions = resolved_condition_frequencies(values["condition_values"], values["condition_unit"])
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if int(values["number_conditions"]) != len(parsed_conditions):
            errors.append(
                f"Number of conditions ({values['number_conditions']}) must match "
                f"the {len(parsed_conditions)} comma-separated values."
            )
    if not 1 <= int(values["staircases_per_condition"]) <= 24:
        errors.append("Staircases per condition must be between 1 and 24.")
    if values["condition_unit"] != "legacy_shader_radians":
        physical = resolved_condition_frequencies(values["condition_values"], values["condition_unit"])
        if any(freq > 1000 for freq in physical):
            errors.append("Spatial frequency above 1000 cycles/degree is not physically plausible.")
    if not 0 <= float(values["Background_Screen_intensity"]) < 1:
        errors.append("Background screen intensity must be in [0, 1).")
    starting = float(values["starting_probe_intensity"])
    background = float(values["Background_Screen_intensity"])
    if not background <= starting <= 1:
        errors.append("Starting probe intensity must lie between background intensity and 1.0.")
    if float(values["Max_monitor_Luminance"]) <= 0:
        errors.append("Maximum luminance must be positive.")
    if float(values["Background_Luminance"]) >= float(values["Max_monitor_Luminance"]):
        errors.append("Background luminance must be below maximum monitor luminance.")
    # In the retained renderer T=0 waits for a key indefinitely. These phases
    # have no response keys, so reject a setup that cannot advance.
    for key in ("timeFixate", "timeInterval", "timeAB"):
        if int(values[key]) <= 0:
            errors.append(f"{key} must be positive; zero would stall this keyless phase.")
    if int(values["timeT"]) < 0:
        errors.append("timeT must not be negative.")

    return errors


def _validate_monitor(values, profile):
    profile.validate_luminance_pair(luminance_cdm2=float(values["Background_Luminance"]), screen_intensity=float(values["Background_Screen_intensity"]))
    endpoints = [point.luminance_cdm2 for point in profile.luminance_calibration if point.screen_intensity == 1.0]
    if profile.has_verified_luminance_mapping and endpoints and abs(endpoints[0]-float(values["Max_monitor_Luminance"])) > 1e-6:
        raise ValueError("Maximum luminance differs from the measured full-command endpoint.")


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
    calibration_requirements=("geometry", "luminance", "timing"),
    data_path_builder=_data_path_parts,
    trial_column_overrides={
        "stimulus_condition": {
            "units_or_encoding": "cycles/degree for cpd/period modes; historical shader radians for explicit legacy mode (check experiment_config.json)",
            "meaning": (
                "Experiment-configured legacy spatial-frequency scalar associated with the accepted response."
            ),
            "notes": (
                "For cpd and degrees/cycle input, the conditions.runtime.json values are canonical cpd "
                "and the renderer evaluates physical visual angle per fragment from display geometry. "
                "Legacy mode preserves the old fs shader phase coefficient from the "
                "historical 31.5 multiplier (63 and 252 reference values). "
                "Photometric/temporal calibration remains independent."
            ),
        },
        "stimulus_position_px": {
            "units_or_encoding": "horizontal Pyglet window coordinate in pixels",
            "meaning": (
                "Horizontal x-position of the 2AFC target selected for this accepted response."
            ),
            "notes": (
                "The corresponding left/right alternatives and window centre are recorded in "
                "resolved_experiment.json."
            ),
        },
        "target_alternative": {
            "units_or_encoding": "0 = left; 1 = right",
            "meaning": "Correct spatial alternative for the current CSF response.",
        },
        "participant_response": {
            "units_or_encoding": "0 = left; 1 = right",
            "meaning": "Participant's encoded left/right response for the current CSF trial.",
        },
        "response_key": {
            "units_or_encoding": "LEFT or RIGHT",
            "meaning": "Accepted keyboard key recorded for the current CSF response.",
        },
    },
    adaptive=AdaptiveSelection("consecutive_up_down",
        ("n_down", "n_up", "logUNIT_UP", "logUNIT_DW", "initial_one_down_limit", "staircases_per_condition", "reversal_termination", "max_trials"),
        "garcia_perez_1998", "log10_display_contrast"),
    response_paradigm=LEFT_RIGHT,
    fields=(
        ConfigField(
            "Max_monitor_Luminance",
            "Maximum monitor luminance (cd/m²)",
            "float",
            default=None,
            minimum=0.0,
            help_text="Measured maximum luminance for this display; verified profiles enforce the measured endpoint.",
        ),
        ConfigField(
            "Background_Luminance",
            "Background luminance (cd/m²)",
            "float",
            default=None,
            minimum=0.0,
            help_text=(
                "Choose a saved intensity/luminance pair above to set both values from this "
                "display's calibration table. Choose Manual only when necessary; verified "
                "profiles enforce the corresponding measured digital command."
            ),
        ),
        ConfigField(
            "Background_Screen_intensity",
            "Background digital screen intensity",
            "float",
            default=None,
            minimum=0.0, maximum=1.0,
            help_text=(
                "Normalised digital display command for the selected background. Saved luminance "
                "pairs set this automatically; profile-only test values are NOT certified "
                "photometry. Manual values require separate review for human acquisition."
            ),
        ),
        ConfigField(
            "number_conditions", "Number of stimulus conditions", "int", default=2,
            minimum=1, maximum=24, section="Stimulus conditions",
            help_text="Must equal the number of comma-separated numeric condition values below.",
        ),
        ConfigField(
            "condition_unit", "Spatial-frequency units", "choice",
            default="cycles_per_degree", choices=FREQUENCY_UNITS,
            section="Stimulus conditions",
            help_text="cycles/degree (cpd), degrees/cycle (period), or explicit historical uncalibrated shader phase. "
                      "cpd is calibrated geometrically from screen size, resolution and viewing distance.",
        ),
        ConfigField(
            "condition_values", "Condition values (comma-separated, in selected units)", "text",
            default=DEFAULT_CSF_CONDITIONS, section="Stimulus conditions",
            help_text="Enter spatial frequency in cycles/degree, or period in degrees/cycle. "
                      "Legacy mode retains historical shader radians for reproducibility.",
        ),
        ConfigField("n_down", "Correct responses required for a downward step", "int", default=2, minimum=1),
        ConfigField("n_up", "Incorrect responses required for an upward step", "int", default=1, minimum=1),
        ConfigField("logUNIT_UP", "Up-step size (legacy log units)", "float", default=0.35),
        ConfigField(
            "logUNIT_DW",
            "Down-step size (legacy log units)",
            "float",
            default=0.5488 * 0.35,
        ),
        ConfigField(
            "initial_one_down_limit", "Initial 1-down maximum accepted responses per staircase (0 = disabled)",
            "int", default=5, minimum=0, maximum=1000,
            help_text="On each staircase, one correct response steps down until the FIRST incorrect "
                      "answer or this many accepted answers, whichever happens first. "
                      "The first incorrect answer uses the normal n-up rule; subsequent "
                      "trials follow the selected n-down/n-up rules.",
        ),
        ConfigField("staircases_per_condition", "Independent staircases per condition", "int", default=1, minimum=1, maximum=24,
                    help_text="Creates separately indexed adaptive staircases for each condition. The maximum-response ceiling is shared across ALL staircases."),
        ConfigField("reversal_termination", "Reversals required per staircase", "int", default=10, minimum=1),
        ConfigField("max_trials", "Maximum accepted responses (safety ceiling)", "int", default=30, minimum=1),
        ConfigField("timeFixate", "Fixation duration (ms)", "int", default=250, section="Timing (advanced)"),
        ConfigField("timeInterval", "Interval duration (ms)", "int", default=250, section="Timing (advanced)"),
        ConfigField("timeAB", "Stimulus duration (ms)", "int", default=200, section="Timing (advanced)"),
        ConfigField("timeT", "Response timeout (ms; 0 = self-paced legacy behaviour)", "int", default=0, section="Timing (advanced)"),
        ConfigField("starting_probe_intensity", "Starting probe digital intensity", "float", default=1.0),
    ),
    fixed_setup={
        "trialPOINT": 9,
        "stimulus_SF": 1.0,
        "index_last_PosList": 0,
        "Npoints": 12,
        "positionBool": 1,
        "positionFind": 1,
    },
    validator=_validate,
    monitor_validator=_validate_monitor,
    source_paths=("src/psychophysics_lab/experiments/contrast_sensitivity.py", "Experiments/contrast_sensitivity_function.py"),
    stimulus_slots={"target": "csf"}, stimulus_defaults={"target": "legacy_csf"},
    stimulus_field_bindings={"target": {key: key for key in ("number_conditions", "condition_unit", "condition_values")}},
)
