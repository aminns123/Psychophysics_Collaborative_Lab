"""CSF — CIRCULAR WINDOWED SINE GRATING

A second scientific CSF protocol, sharing the established CSF experiment's
conditions, staircase/constant-stimuli policies, response interpretation,
timing, threshold calculation and canonical data schema.

WHAT CHANGES SCIENTIFICALLY: Only the selected grating envelope. A circular
aperture of exact researcher-selected angular diameter carries a full-strength
sine wave across its central disk, fading only in an optional outer annulus.
The historical Gaussian CSF remains available as contrast_sensitivity.

Read this short file top to bottom: settings -> prepare stimulus -> shared
scientific procedure -> registered experiment. The common CSF experiment
contains the complete adaptive mathematics and original response timeline.
"""
from dataclasses import replace

from psychophysics_lab.experiments import contrast_sensitivity as csf
from psychophysics_lab.methods.contrast import run_contrast_experiment
from psychophysics_lab.researcher import ConfigField

# 1. SETTINGS — one envelope-specific substitution, all remaining CSF settings
# (frequencies, target offset, timings, contrast methods and response mappings)
# are inherited directly from the public reference CSF.
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
FIELDS = tuple(field for field in csf.FIELDS if field.key not in _FIELDS_REMOVED) + ENVELOPE_FIELDS

STIMULUS_SLOTS = dict(csf.STIMULUS_SLOTS) | {
    "grating": "circular_windowed_sinusoidal_grating",
}
STIMULUS_DEFAULTS = dict(csf.STIMULUS_DEFAULTS) | {
    "grating": "circular_windowed_sinusoidal_grating",
}

# 2. SCIENTIFIC CONDITIONS, TIMING AND RESPONSE RULES — deliberately shared.
# These are aliases rather than a copied staircase engine or second timeline.
make_conditions = csf.make_conditions
make_fixed_schedule = csf.make_fixed_schedule
fixed_contrast_levels = csf.fixed_contrast_levels
choose_condition = csf.choose_condition
make_trial = csf.make_trial
interpret_response = csf.interpret_response
trial_record = csf.trial_record
fixed_trial_record = csf.fixed_trial_record
update_experiment = csf.update_experiment
is_finished = csf.is_finished
finish_experiment = csf.finish_experiment
primary_rule = csf.primary_rule
validate_monitor = csf.validate_monitor


# 3. PREPARE THE *DIFFERENT* STIMULUS — only scientific change in presentation.
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


def initialise_experiment(run, conditions):
    # The inherited CSF staircase machinery uses identical parameters/rules.
    return csf.initialise_experiment(
        run, conditions,
        grating_resolution=grating_resolution(run.values),
    )


def adaptive_contrast_method(run):
    return csf.adaptive_contrast_method(
        run, initialise=initialise_experiment
    )


def fixed_contrast_method(run):
    return csf.fixed_contrast_method(
        run, grating_resolution=grating_resolution(run.values)
    )


# 4. ONE COMMON TRIAL LOOP — the windowed experiment does NOT implement its
# own staircase updates, recording pipeline or data directory conventions.
def procedure(run):
    return run_contrast_experiment(
        run,
        methods={
            "adaptive": lambda: adaptive_contrast_method(run),
            "constant_stimuli": lambda: fixed_contrast_method(run),
        },
        prepare_stimuli=prepare_stimuli,
        make_trial=make_trial,
        interpret_response=interpret_response,
    )


# 5. VALIDATION — experiment-specific fade geometry, otherwise CSF invariant.
def validate_settings(values):
    yield from csf.validate_settings(values)
    radius = values["aperture_diameter_deg"] / 2.
    if values["edge_mode"] == "soft_edge" and values["fade_width_deg"] > radius:
        yield ("Circular outer-edge fade cannot exceed aperture radius; "
               "decrease fade width or increase aperture diameter.")


SCIENTIFIC_SPEC = dict(csf.SCIENTIFIC_SPEC) | {
    "version": "csf-circular-windowed-spatial-1",
    "stimulus": "Circular windowed sinusoidal grating; flat central disk, optional outer-edge raised-cosine fade.",
    "contrast_quantity": "Same digital peak-to-peak modulation as reference CSF, not optical Michelson contrast.",
    "historical_equivalence": "Distinct from thesis Gaussian-windowed CSF. Do not pool thresholds without examining envelope and aperture effects.",
}

# The metadata and calibration requirements are preserved exactly, while a
# unique experiment ID/data directory prevents confusing the two stimulus
# conditions or accidentally overwriting legacy CSF runs.
TRIAL_COLUMNS = {
    key: dict(value) for key, value in csf.SPEC.trial_column_overrides.items()
}
for column in ("presented_display_contrast", "next_display_contrast"):
    details = TRIAL_COLUMNS[column]
    details["notes"] = (
        "Strength before circular edge weighting; "
        "background + (strength/2) * sin(2*pi*f*x) * circular_window. "
        "Not calibrated optical Michelson contrast or historical C_disp."
    )

SPEC = replace(
    csf.SPEC,
    id="contrast_sensitivity_windowed",
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
    stimulus_slots=STIMULUS_SLOTS,
    stimulus_defaults=STIMULUS_DEFAULTS,
    procedure=procedure,
    validator=validate_settings,
    monitor_validator=validate_monitor,
    method_planner=make_fixed_schedule,
    trial_column_overrides=TRIAL_COLUMNS,
    scientific_spec=SCIENTIFIC_SPEC,
    source_paths=(
        "src/psychophysics_lab/experiments/contrast_sensitivity_windowed.py",
        "src/psychophysics_lab/experiments/contrast_sensitivity.py",
    ),
)
