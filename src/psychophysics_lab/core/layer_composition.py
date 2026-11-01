"""Opt-in ordered composition of independently rendered scientific patches.

Legacy opaque rendering is unchanged. Transparent layer renderers already draw
their foreground *over their declared background*, and their alpha callback
reports the actual coverage. We remove that layer's own background before
compositing, so later objects cover earlier objects only where they exist.

All operations are in floating point, in displayed pixel coordinates. No
clamping, resizing, automatic transparency, or presumed optical calibration.
"""
from __future__ import annotations

import math
import numpy as np


def compose_ordered_layers(layers, background):
    """Compose (x, y, grayscale, alpha_or_None, layer_background[, blend]) in list order.

    Each patch is indexed from its lower-left display pixel, and has shape
    (height, width). alpha=None means an explicitly opaque legacy patch.
    Otherwise: patch = layer_background*(1-alpha) + foreground*alpha.
    This includes partial pixel-area coverage of narrow probe lines.
    """
    if not math.isfinite(background) or not 0 <= background <= 1:
        raise ValueError("Composition background must be finite in [0,1].")
    if not layers:
        raise ValueError("Composition requires at least one stimulus placement.")
    checked = []
    for layer in layers:
        if len(layer) == 5:
            x, y, image, alpha, layer_background = layer
            blend = "over"
        elif len(layer) == 6:
            x, y, image, alpha, layer_background, blend = layer
        else:
            raise ValueError("Layer must declare origin, image, alpha, background and optional blend.")
        if blend not in {"over", "add"}:
            raise ValueError("Layer overlap must be 'over' or 'add'.")
        if blend == "add" and alpha is None:
            raise ValueError("Additive layers must declare their foreground coverage.")
        if type(x) is not int or type(y) is not int:
            raise ValueError("Layer origin must be in integer display pixels.")
        image = np.asarray(image, dtype=np.float64)
        if image.ndim != 2 or image.size == 0 or not np.isfinite(image).all():
            raise ValueError("Layer grayscale raster must be finite and nonempty.")
        if image.min() < 0 or image.max() > 1:
            raise ValueError("Layer grayscale commands are outside [0,1].")
        if alpha is not None:
            alpha = np.asarray(alpha, dtype=np.float64)
            if alpha.shape != image.shape or not np.isfinite(alpha).all():
                raise ValueError("Layer alpha must be a finite coverage raster of matching shape.")
            if alpha.min() < 0 or alpha.max() > 1:
                raise ValueError("Layer alpha must be in [0,1]; no implicit clipping.")
            if (not math.isfinite(layer_background)
                    or not math.isclose(layer_background, background, rel_tol=0, abs_tol=1e-12)):
                raise ValueError("Transparent layer background must match the scene background.")
        checked.append((x, y, image, alpha, layer_background, blend))
    left = min(item[0] for item in checked)
    bottom = min(item[1] for item in checked)
    right = max(item[0] + item[2].shape[1] for item in checked)
    top = max(item[1] + item[2].shape[0] for item in checked)
    canvas = np.full((top-bottom, right-left), background, dtype=np.float64)
    for x, y, image, alpha, layer_background, blend in checked:
        row, col = y-bottom, x-left
        target = canvas[row:row+image.shape[0], col:col+image.shape[1]]
        if blend == "add":
            # image is background plus already pixel-coverage-weighted
            # foreground deviation. Apply that increment once, without
            # changing the earlier ring/flanker values underneath.
            target[:] += image - layer_background
        elif alpha is None:
            target[:] = image
        else:
            # A transparent renderer's output is its foreground precomposed on
            # its own background. Remove only that background, not the pixel
            # area coverage. The last declared object is visually on top.
            target[:] = (1-alpha)*target + image - (1-alpha)*layer_background
    if not np.isfinite(canvas).all() or canvas.min() < -1e-12 or canvas.max() > 1+1e-12:
        raise ValueError("Composed stimulus exceeds digital gamut; no silent clipping.")
    return left, bottom, canvas
