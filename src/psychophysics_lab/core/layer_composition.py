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
    """Compose (x, y, grayscale, alpha_or_None, layer_background) in list order.

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
    for x, y, image, alpha, layer_background in layers:
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
        checked.append((x, y, image, alpha, layer_background))
    left = min(item[0] for item in checked)
    bottom = min(item[1] for item in checked)
    right = max(item[0] + item[2].shape[1] for item in checked)
    top = max(item[1] + item[2].shape[0] for item in checked)
    canvas = np.full((top-bottom, right-left), background, dtype=np.float64)
    for x, y, image, alpha, layer_background in checked:
        row, col = y-bottom, x-left
        target = canvas[row:row+image.shape[0], col:col+image.shape[1]]
        if alpha is None:
            target[:] = image
        else:
            # A transparent renderer's output is its foreground precomposed on
            # its own background. Remove only that background, not the pixel
            # area coverage. The last declared object is visually on top.
            target[:] = (1-alpha)*target + image - (1-alpha)*layer_background
    if not np.isfinite(canvas).all() or canvas.min() < -1e-12 or canvas.max() > 1+1e-12:
        raise ValueError("Composed stimulus exceeds digital gamut; no silent clipping.")
    return left, bottom, canvas
