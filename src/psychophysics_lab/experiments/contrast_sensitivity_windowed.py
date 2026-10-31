"""Circular-windowed CSF: the same selection rules with a distinct grating envelope.

Read parameters, opening and trial events here. The named Gaussian-CSF scientific
functions are reused explicitly below; no second staircase/recorder is copied.
Circular diameter, edge/fade, geometry, intensity units and saved identity remain
distinct. Software implementation does not establish optical equivalence.
"""
from dataclasses import replace
from psychophysics_lab.experiments import contrast_sensitivity as csf
from psychophysics_lab.methods.contrast import run_contrast_experiment
from psychophysics_lab.researcher import (
    ConfigField, WaitForKey, Show, Stimulus, CollectResponse, legacy_trial_factory,
)

# PART A1 — EXPERIMENTAL CHOICES
# Question: which side contains the grating at each selected spatial frequency?
# Frequency (cycles/degree) is a condition; left/right is the target alternative.
# Adaptive repeats are independent tracks per frequency. Fixed repeats are
# presentations in frequency/strength cells, not staircases. Selection order,
# independent target draws and the median/arithmetic estimator are explicit in A2.
# DO NOT CONFUSE: peak-to-peak DIGITAL modulation with measured optical contrast.

# Reuse the exact CSF ConfigFields for frequency, timing, side offset, method,
# response keys, background and adaptive steps. Replace only Gaussian-envelope
# fields with the explicit circular controls below; no defaults are redefined.
ENVELOPE_FIELDS = (
    ConfigField(
        "aperture_diameter_deg", "Circular grating aperture diameter",
        "float", 3., minimum=.1, maximum=45., units="degrees",
        help_text="Exact circular support diameter, not Gaussian sigma. "
                  "Full sinusoidal modulation envelope in the centre; only "
                  "the outer annulus fades when edge_mode=soft_edge.",
        section="Stimulus conditions",
    ),
    ConfigField(
        "edge_mode", "Circular grating edge", "choice", "soft_edge",
        choices=("soft_edge", "hard_edge"),
        help_text="soft_edge is flat inside the aperture and fades only at "
                  "the outer rim; hard_edge stops modulation abruptly at "
                  "the circle boundary and adds high-frequency edge energy.",
        section="Stimulus conditions",
    ),
    ConfigField(
        "fade_width_deg", "Circular outer-edge fade width", "float", .15,
        minimum=0., maximum=20., units="degrees",
        help_text="Radial thickness of the smooth raised-cosine edge in "
                  "visual degrees. Only used for soft_edge; zero means "
                  "immediate hard cutoff. Must not exceed half the diameter.",
        section="Stimulus conditions",
    ),
)

_FIELDS_REMOVED = frozenset(("grating_sigma_deg", "grating_cutoff_sigmas"))

FIELDS = tuple(
    field for field in csf.SPEC.fields if field.key not in _FIELDS_REMOVED
) + ENVELOPE_FIELDS

STIMULUS_SLOTS = dict(csf.STIMULUS_SLOTS) | {"grating": "circular_windowed_sinusoidal_grating"}
STIMULUS_DEFAULTS = dict(csf.STIMULUS_DEFAULTS) | {"grating": "circular_windowed_sinusoidal_grating"}
RESPONSES = csf.RESPONSES
PARADIGM = csf.PARADIGM


# Session opening — once; readiness is not an accepted scientific response
# SESSION_START = [] disables readiness without changing the scientific trial.
SESSION_START = [
    WaitForKey("ready", key="SPACE", slot="ready_fixation", instructions="Press SPACE when ready"),
    Show("settle", slot="ready_fixation", duration=1000),
]


# Chronological events — repeated from the current condition and strength
def trial_events(settings, condition):
    offset = settings["grating_offset_deg"]
    x = -offset if condition["target"] == 0 else offset
    return [
        Show("fixation", slot="fixation", duration="fixation_ms"),
        Show("grating", stimuli=(Stimulus("grating", x_deg=x),), duration="grating_ms"),
        CollectResponse(actions=("left", "right"), slot="fixation"),
    ]


# Shared journal values: frequency (cycles/degree), adaptive staircase repeat
# and grating x (degrees); fixed mode records cell repeat and presented digital
# modulation. The one-way Gaussian dependency owns those named record functions.


# PART A2 — SCIENTIFIC METHODS

def prepare_stimuli(run, condition, state):
    settings = run.values
    background = settings["background_intensity"]
    return {
        "grating": run.stimulus_parameters(
            "grating",
            size_deg=settings["aperture_diameter_deg"],
            edge_mode=settings["edge_mode"],
            fade_width_deg=settings["fade_width_deg"],
            spatial_frequency_cpd=condition["frequency_cpd"],
            contrast=condition["contrast"],
            background=background,
        ),
        "fixation": run.stimulus_parameters("fixation", background=background),
    }

def grating_resolution(settings):
    """Accurate stimulus provenance, shared by adaptive and fixed-level CSF."""
    radius = settings["aperture_diameter_deg"] / 2.
    fade = (settings["fade_width_deg"]
            if settings["edge_mode"] == "soft_edge" else 0.)
    return {
        "grating_stimulus_id": "circular_windowed_sinusoidal_grating",
        "intensity_mapping": (
            "I(x,y)=background+(digital_peak_to_peak/2)*sin(2*pi*frequency*x)"
            "*circular_window(r; radius, fade_width)"
        ),
        "grating_envelope": "flat circular interior, optional raised-cosine outer annulus",
        "aperture_shape": "circle",
        "grating_support_radius_deg": radius,
        "grating_support_diameter_deg": settings["aperture_diameter_deg"],
        "grating_edge_mode": settings["edge_mode"],
        "grating_edge_fade_width_deg": fade,
        "grating_flat_radius_deg": radius-fade,
    }

# These public scientific functions own frequency/side selection, fixed schedules
# and post-response log steps. The circular envelope does not change those rules.
make_conditions = csf.make_conditions
choose_condition = csf.choose_condition
make_fixed_schedule = csf.make_fixed_schedule
fixed_contrast_levels = csf.fixed_contrast_levels
interpret_response = csf.interpret_response
update_experiment = csf.update_experiment
validate_monitor = csf.validate_monitor


SCIENTIFIC_SPEC = dict(csf.SCIENTIFIC_SPEC) | {
    "version": "csf-spatial-windowed-1",
    "stimulus": "Circular windowed sinusoidal grating; flat central disk, optional outer-edge raised-cosine fade.",
    "contrast_quantity": "Same digital peak-to-peak modulation as reference CSF, not optical Michelson contrast.",
    "historical_equivalence": "Distinct from thesis Gaussian-windowed CSF. Do not pool thresholds without examining envelope and aperture effects.",
}


def initialise_experiment(run, conditions):
    # The inherited CSF staircase machinery uses identical parameters/rules.
    return csf.initialise_experiment(
        run, conditions,
        grating_resolution=grating_resolution(run.values),
    )


def validate_settings(values):
    yield from csf.validate_settings(values)
    radius = values["aperture_diameter_deg"] / 2.
    if values["edge_mode"] == "soft_edge" and values["fade_width_deg"] > radius:
        yield ("Circular outer-edge fade cannot exceed aperture radius; "
               "decrease fade width or increase aperture diameter.")


# Stopping, scientific estimators and results
# Reversal completion, safety ceiling, canonical units and estimator are shared;
# grating_resolution above records the circular support instead of Gaussian sigma.
is_finished = csf.is_finished
primary_rule = csf.primary_rule
finish_experiment = csf.finish_experiment
trial_record = csf.trial_record
fixed_trial_record = csf.fixed_trial_record


TRIAL_COLUMN_OVERRIDES = {
    key: dict(value) for key, value in csf.SPEC.trial_column_overrides.items()
}
for column in ("presented_display_contrast", "next_display_contrast"):
    details = TRIAL_COLUMN_OVERRIDES[column]
    details["notes"] = (
        "Strength before circular edge weighting; "
        "background + (strength/2) * sin(2*pi*f*x) * circular_window. "
        "Not calibrated optical Michelson contrast or historical C_disp."
    )


def adaptive_contrast_method(run):
    return csf.adaptive_contrast_method(
        run, initialise=initialise_experiment
    )


def fixed_contrast_method(run):
    return csf.fixed_contrast_method(
        run, grating_resolution=grating_resolution(run.values)
    )


# PART B — FRAMEWORK INTEGRATION
# FRAMEWORK CONNECTION: same runner, recorder, Review hooks and public identity.
# Scientific choices/measurements are above; normally leave these bindings alone.


def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_contrast_method(run),
            "constant_stimuli": lambda: fixed_contrast_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        trial_events=trial_events,
        interpret_response=interpret_response,
    )

# Compatibility and registration
make_trial = legacy_trial_factory(trial_events)


def definition(identity="contrast_sensitivity_windowed"):
    return replace(
        csf.SPEC,
        session_start=SESSION_START,
        stimulus_field_bindings={"ready_fixation": {"background": "background_intensity"}},
        id=identity,
        display_name="Contrast Sensitivity — Circular Windowed Grating",
        description=(
            "The same left/right CSF design and contrast methods as the Gaussian "
            "reference, but a circular sine grating whose centre has a flat "
            "amplitude envelope and whose outer edge can fade smoothly or stop abruptly."
        ),
        legacy_module=__name__,
        legacy_experiment_type="contrast_sensitivity_windowed",
        data_directory_name="contrast_sensitivity_windowed",
        fields=FIELDS,
        stimulus_parameter_controls={
            "grating": {"size_deg": "aperture_diameter_deg", "edge_mode": "edge_mode",
                        "fade_width_deg": "fade_width_deg", "background": "background_intensity"},
            "fixation": {"background": "background_intensity"},
        },
        stimulus_slots=STIMULUS_SLOTS,
        stimulus_defaults=STIMULUS_DEFAULTS,
        procedure=procedure,
        validator=validate_settings,
        monitor_validator=validate_monitor,
        method_planner=make_fixed_schedule,
        trial_column_overrides=TRIAL_COLUMN_OVERRIDES,
        scientific_spec=SCIENTIFIC_SPEC,
        source_paths=(
            "src/psychophysics_lab/experiments/contrast_sensitivity_windowed.py",
            "src/psychophysics_lab/experiments/contrast_sensitivity.py",
        ),
    )


SPEC = definition()
