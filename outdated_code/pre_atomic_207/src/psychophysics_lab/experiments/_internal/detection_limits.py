"""Local digital headroom for the existing DetectionScene renderer.

No alternate composition: evaluate the same affine renderer on the presentation
grid, including rectangular pixel coverage and the fixation blend.
"""
import numpy as np


def probe_limit(parameters, coordinates, pixel_steps=None):
    from psychophysics_lab.stimulus_library import DetectionScene
    x, y = coordinates
    base = DetectionScene.render(parameters | {"contrast": 0.0}, x, y, pixel_steps=pixel_steps)
    unit = DetectionScene.render(parameters | {"contrast": 1.0}, x, y, pixel_steps=pixel_steps) - base
    if not np.isfinite(base).all() or base.min() < 0 or base.max() > 1:
        raise ValueError(f"Scene without probe exceeds digital gamut: min={base.min():g}, max={base.max():g}; allowed [0, 1].")
    active = unit > 0
    # Absolute nominal probe intensity still lies in [background,1]. Sampling
    # attenuation is not permission to request a nominal intensity above white.
    nominal = 1 - parameters["background"]
    limits = np.full_like(base, np.inf)
    limits[active] = (1-base[active])/unit[active]
    index = np.unravel_index(np.argmin(limits), limits.shape)
    maximum = min(nominal, float(limits[index]))
    # Make the mathematical bound representably safe without clipping pixels.
    if maximum < nominal:
        maximum = float(np.nextafter(maximum, 0.0))
    return maximum, (float(x[index]), float(y[index]))


def resolve_probe_limits(run, conditions, prepare_stimuli):
    """Resolve both targets and all selected probe slots once per condition.

    Repeated staircases reuse identical geometry. Human presentation checks its
    actual resolution against the profile; its final pixel check remains active.
    """
    from psychophysics_lab.core.presentation import (
        plan_visible_stimulus, stimulus_geometry,
    )
    from psychophysics_lab.core.timeline import Stimulus
    from psychophysics_lab.stimuli.registry import get_stimulus
    cache, grids = {}, {}
    for condition in conditions:
        key = condition["value"]
        if key not in cache:
            maximum = 1-run.values["background_intensity"]
            limiting_position = None
            for target in (0, 1):
                parameters = prepare_stimuli(run, dict(condition, target=target, contrast=0.0), {})
                for slot, p in parameters.items():
                    if not p["probe_present"]:
                        continue
                    stimulus = get_stimulus("detection_scene")
                    extent = stimulus_geometry(stimulus, p)["raster_extent_deg"]
                    if extent not in grids:
                        profile = run.display
                        resolution = getattr(profile, "expected_resolution_px", None)
                        if resolution:
                            placement = Stimulus(slot)
                            _, coordinates, steps = plan_visible_stimulus(profile, resolution, stimulus, p, placement)
                            grids[extent] = (coordinates, steps)
                        else:
                            if not run.synthetic:
                                raise ValueError("Probe headroom requires the selected display resolution.")
                            axis = (np.arange(256)+.5-128)*extent/256
                            grids[extent] = (np.meshgrid(axis, axis), None)
                    bound, position = probe_limit(p, *grids[extent])
                    if bound < maximum:
                        maximum, limiting_position = bound, position
            cache[key] = (maximum, limiting_position)
        maximum, position = cache[key]
        condition["maximum_probe_increment"] = maximum
        start = run.values["starting_probe_intensity"]-run.values["background_intensity"]
        if maximum <= 0 or start > maximum:
            raise ValueError(
                f"Probe/ring/flanker overlap exceeds digital gamut for condition {key}: "
                f"starting intensity {run.values['starting_probe_intensity']:g}, background "
                f"{run.values['background_intensity']:g}, increment {start:g}; allowed increment "
                f"[0, {maximum:.10g}], maximum nominal intensity "
                f"{run.values['background_intensity']+maximum:.10g}; limiting pixel (degrees) {position}. "
                "Reduce probe intensity or the overlapping layer increment; no clipping."
            )
