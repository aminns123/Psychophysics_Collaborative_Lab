"""Digital probe headroom against the *presented* stimulus composition.

Atomic experiments declare the source stimuli, positions, overlaps and targets.
This module does not reconstruct an experiment-specific DetectionScene. For
actual display profiles it renders exactly the same per-pixel layered phases
as native presentation; only the safety calculation's full-strength endpoint
may exceed gamut (no clipping). A synthetic run without a selected resolution
uses an explicitly unqualified 256-pixel sampling grid instead.
"""
import numpy as np


def probe_limit(parameters, coordinates, pixel_steps=None):
    """Historical DetectionScene comparison API; not used by atomic experiments."""
    from psychophysics_lab.stimulus_library import DetectionScene
    x, y = coordinates
    base = DetectionScene.render(parameters | {"contrast": 0.0}, x, y, pixel_steps=pixel_steps)
    unit = DetectionScene.render(parameters | {"contrast": 1.0}, x, y, pixel_steps=pixel_steps) - base
    if not np.isfinite(base).all() or base.min() < 0 or base.max() > 1:
        raise ValueError(f"Scene without probe exceeds digital gamut: min={base.min():g}, max={base.max():g}; allowed [0, 1].")
    active = unit > 0
    nominal = 1 - parameters["background"]
    limits = np.full_like(base, np.inf)
    limits[active] = (1-base[active])/unit[active]
    index = np.unravel_index(np.argmin(limits), limits.shape)
    maximum = min(nominal, float(limits[index]))
    if maximum < nominal:
        maximum = float(np.nextafter(maximum, 0.0))
    return maximum, (float(x[index]), float(y[index]))


def _synthetic_phase(phase, parameters_by_slot, background):
    """Unqualified fallback: correct ordered blend, approximate sampling only.

    No physical headroom guarantee follows from this grid. A real run always
    uses the calibrated resolution and actual angular-viewport clipping.
    """
    from psychophysics_lab.core.layer_composition import compose_ordered_layers
    from psychophysics_lab.core.presentation import render_values, stimulus_geometry
    from psychophysics_lab.stimuli.registry import get_stimulus

    extent = max(
        14.0,
        *(
            stimulus_geometry(get_stimulus(parameters_by_slot[p.slot][0]),
                              parameters_by_slot[p.slot][1])["raster_extent_deg"]
            + 2 * max(abs(p.x_deg), abs(p.y_deg))
            for p in phase.placements
        ),
    )
    axis = (np.arange(256) + .5 - 128) * extent / 256
    xx, yy = np.meshgrid(axis, axis)
    layers = []
    for placement in phase.placements:
        identity, params = parameters_by_slot[placement.slot]
        stimulus = get_stimulus(identity)
        if stimulus.layer_alpha is None:
            raise ValueError("Atomic headroom preflight requires explicitly layered stimuli.")
        x, y = xx - placement.x_deg, yy - placement.y_deg
        image = render_values(
            stimulus, params, pixels=(256, 256), coordinates=(x, y)
        )
        alpha = stimulus.layer_alpha(params, x, y)
        layers.append((0, 0, image, alpha, params["background"], placement.blend))
    _, _, image = compose_ordered_layers(layers, background, require_gamut=False)
    return (0, 0, image), (xx, yy)


def _phase_image(run, phase, parameters, stimuli, background):
    """Identical physical presentation path, with an unclipped safety endpoint."""
    selected = {slot: (stimuli[slot], params) for slot, params in parameters.items()}
    resolution = getattr(run.display, "expected_resolution_px", None)
    if resolution:
        from psychophysics_lab.core.presentation import render_layered_phase
        x, y, image, _ = render_layered_phase(
            run.display, resolution, phase, selected, background,
            require_gamut=False,
        )
        return (x, y, image), None
    if not run.synthetic:
        raise ValueError("Probe headroom requires the selected display resolution.")
    return _synthetic_phase(phase, selected, background)


def _limit_from_frames(base_frame, full_frame, nominal):
    """Maximum nominal digital increment from an affine, *unclipped* composition."""
    if nominal <= 0:
        raise ValueError("Background leaves no positive digital probe headroom.")
    xb, yb, base = base_frame
    xf, yf, full = full_frame
    if (xb, yb) != (xf, yf) or base.shape != full.shape:
        raise ValueError("Probe-strength change altered the presented raster geometry.")
    if (not np.isfinite(base).all() or base.min() < -1e-12
            or base.max() > 1 + 1e-12):
        raise ValueError(
            f"Presented composition without probe exceeds digital gamut: "
            f"min={base.min():g}, max={base.max():g}; no clipping."
        )
    slope = (full - base) / nominal
    if not np.isfinite(slope).all() or slope.min() < -1e-10:
        raise ValueError("Probe must make a nonnegative affine digital increment.")
    active = slope > 1e-10
    if not np.any(active):
        raise ValueError("Presented probe has no visible positive pixel coverage.")
    indices = np.argwhere(active)
    allowed = (1 - base[active]) / slope[active]
    smallest = int(np.argmin(allowed))
    row, col = map(int, indices[smallest])
    maximum = min(nominal, float(allowed[smallest]))
    if maximum < nominal:
        maximum = float(np.nextafter(maximum, 0.0))
    return maximum, (row, col)


def _limiting_degrees(run, frame, sample_coordinates, index):
    from psychophysics_lab.core.presentation import display_degree_coordinates
    from psychophysics_lab.core.timeline import Stimulus
    row, col = index
    if sample_coordinates is not None:
        xx, yy = sample_coordinates
        return float(xx[row, col]), float(yy[row, col])
    x, y, _ = frame
    coordinates = display_degree_coordinates(
        run.display, run.display.expected_resolution_px, (1, 1),
        (x + col, y + row), Stimulus("probe")
    )
    return float(coordinates[0][0, 0]), float(coordinates[1][0, 0])


def resolve_probe_limits(run, conditions, prepare_stimuli, *, trial_events, stimuli):
    """Check both targets using the experiment's actual placements and layers.

    Identical scientific conditions reuse their limit across staircase repeats.
    The adaptive starter or highest fixed level must fit. Native presentation
    retains its independent strict gamut check at the chosen actual strength.
    """
    background = run.values["background_intensity"]
    nominal = 1.0 - background
    if stimuli.get("probe") != "probe_line":
        raise ValueError("Atomic headroom requires the independently declared ProbeLine.")
    cache = {}
    for condition in conditions:
        key = condition["value"]
        if key not in cache:
            maximum = nominal
            limiting_position = None
            for target in (0, 1):
                zero_condition = dict(condition, target=target, contrast=0.0)
                full_condition = dict(condition, target=target, contrast=nominal)
                zero_params = prepare_stimuli(run, zero_condition, {})
                full_params = prepare_stimuli(run, full_condition, {})
                phases = trial_events(run.values, zero_condition)
                full_phases = trial_events(run.values, full_condition)
                if len(phases) != len(full_phases) or any(
                    a.kind != b.kind or a.placements != b.placements
                    for a, b in zip(phases, full_phases)
                ):
                    raise ValueError(
                        "Probe-strength change altered scientific event placement; "
                        "a single affine headroom limit is not valid."
                    )
                probe_phases = [
                    p for p in phases
                    if p.kind == "show" and any(s.slot == "probe" for s in p.placements)
                ]
                if not probe_phases:
                    raise ValueError("Experiment target has no presented probe stage.")
                for phase in probe_phases:
                    base_frame, sample_coordinates = _phase_image(
                        run, phase, zero_params, stimuli, background,
                    )
                    full_frame, _ = _phase_image(
                        run, phase, full_params, stimuli, background,
                    )
                    bound, index = _limit_from_frames(base_frame, full_frame, nominal)
                    if bound < maximum:
                        maximum = bound
                        limiting_position = _limiting_degrees(
                            run, base_frame, sample_coordinates, index,
                        )
            cache[key] = (maximum, limiting_position)
        maximum, position = cache[key]
        condition["maximum_probe_increment"] = maximum
        start = run.values["starting_probe_intensity"] - background
        if maximum <= 0 or start > maximum:
            raise ValueError(
                f"Probe/ring/flanker overlap exceeds digital gamut for condition {key}: "
                f"starting intensity {run.values['starting_probe_intensity']:g}, background "
                f"{background:g}, increment {start:g}; allowed increment "
                f"[0, {maximum:.10g}], maximum nominal intensity "
                f"{background + maximum:.10g}; limiting pixel (degrees) {position}. "
                "Reduce probe intensity or the overlapping layer increment; no clipping."
            )
