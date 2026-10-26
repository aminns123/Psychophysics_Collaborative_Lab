"""Visible-pixel planning for the existing flat-display angular coordinates.

The requested aperture is not resized to the monitor. Only its intersection
is sampled. No texture or coordinate mesh is allocated for off-screen pixels.
"""
import math
import numpy as np
from ..stimuli.spatial_calibration import resolve_spatial_geometry


def stimulus_geometry(stimulus, parameters):
    """Scientific support may enlarge a minimum software raster, never shrink it."""
    selected = float(parameters[stimulus.extent_parameter])
    geometry = getattr(stimulus, "geometry", None)
    result = dict(geometry(parameters)) if geometry else {}
    extent = max(selected, float(result.get("raster_extent_deg", selected)))
    if not math.isfinite(extent) or not 0 < extent < 180:
        raise ValueError("Stimulus raster extent must be finite and between 0 and 180 degrees.")
    return result | {"requested_extent_deg": selected, "raster_extent_deg": extent}


def angular_viewport(profile, resolution, extent_deg, placement):
    """Preserve the old rounded angular edges, intersected with physical pixels."""
    geometry = resolve_spatial_geometry(profile, resolution)
    extent = float(extent_deg)
    centres = (float(placement.x_deg), float(placement.y_deg))
    if not math.isfinite(extent) or not 0 < extent < 180 or not all(map(math.isfinite, centres)):
        raise ValueError("Stimulus extent and position must be finite; extent must be between 0 and 180 degrees.")
    origins, sizes, requested, displayed, raw_pixels, clipped = [], [], [], [], [], []
    for axis, (centre, pitch, limit) in enumerate(zip(centres, geometry.pixel_pitch_m, resolution)):
        low, high = centre - extent/2, centre + extent/2
        field = math.degrees(math.atan(limit/2 * pitch / geometry.viewing_distance_m))
        if high <= -field or low >= field:
            raise ValueError("Stimulus is wholly outside the display viewport. Change its position or display geometry.")
        def pixel(angle):
            return round(limit/2 + geometry.viewing_distance_m * math.tan(math.radians(angle)) / pitch)
        raw_low = pixel(low) if -90 < low < 90 else None
        raw_high = pixel(high) if -90 < high < 90 else None
        if raw_low is not None and raw_high is not None and raw_high - raw_low < 2:
            raise ValueError("Requested stimulus aperture is smaller than two display pixels.")
        start = max(0, min(limit, pixel(max(low, -field))))
        end = max(0, min(limit, pixel(min(high, field))))
        if end <= start:
            raise ValueError("Stimulus has no visible display pixels. Change its position or size.")
        origins.append(start)
        sizes.append(end-start)
        requested.append([low, high])
        raw_pixels.append([raw_low, raw_high])
        displayed.append([math.degrees(math.atan((p-limit/2)*pitch/geometry.viewing_distance_m))
                          for p in (start, end)])
        if low < -field:
            clipped.append(("left", "bottom")[axis])
        if high > field:
            clipped.append(("right", "top")[axis])
    return {"origin_px": origins, "raster_px": sizes,
            "requested_centre_deg": list(centres), "requested_bounds_deg": requested,
            "requested_pixel_bounds": raw_pixels, "displayed_bounds_deg": displayed,
            "clipped": bool(clipped), "clipped_edges": clipped,
            "geometry_basis": "per-pixel flat-screen angular coordinates",
            "viewport_policy": "intersection only; no rescaling or recentring"}


def clipped_pixel_steps(profile, resolution, viewport, placement):
    """Keep probe coverage identical to cropping the intended full raster.

    Only neighbour ANGLES are calculated (one-dimensional vectors). No
    off-screen intensities are evaluated. At original raster edges retain the
    previous one-sided gradient; elsewhere retain its central difference.
    """
    geometry = resolve_spatial_geometry(profile, resolution)
    steps = []
    for axis, (pitch, limit, centre) in enumerate(zip(
            geometry.pixel_pitch_m, resolution, (placement.x_deg, placement.y_deg))):
        start, count = viewport["origin_px"][axis], viewport["raster_px"][axis]
        index = start + np.arange(count)
        def angle(indices):
            return np.degrees(np.arctan((indices + .5-limit/2)*pitch/geometry.viewing_distance_m))-centre
        before, current, after = angle(index-1), angle(index), angle(index+1)
        delta = (after-before)/2
        low, high = viewport["requested_pixel_bounds"][axis]
        if low is not None:
            delta = np.where(index == low, after-current, delta)
        if high is not None:
            delta = np.where(index == high-1, current-before, delta)
        steps.append(delta)
    return np.meshgrid(*steps)
