"""Normalized display contrast for digital intensities (not Weber contrast).

C_disp = (I_n - I_b) / (I_M - I_b).
This mapping does not calibrate physical luminance or define a grating shader's
modulation. Bounds/clipping policies belong to the configured experiment/display.
"""


def normalized_display_contrast(intensity, *, background_intensity, maximum_intensity):
    span = maximum_intensity - background_intensity
    if span == 0:
        raise ValueError("Maximum and background intensities must be different")
    return (intensity - background_intensity) / span


def display_contrast_to_screen_intensity(contrast, *, background_intensity, maximum_intensity):
    return background_intensity + contrast * (maximum_intensity - background_intensity)
