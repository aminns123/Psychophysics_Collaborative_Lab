# Output precision calibration — researcher guide

This stage is adjacent to **Luminance** in Calibrate. It investigates whether digital-command differences survive the presentation chain. It does **not** certify the monitor's native panel bit depth.

## Keep three answers separate

1. **Windows reports:** current active signal depth per colour channel for the *selected display*. This is a software/driver report, not a photometer measurement and not necessarily the panel's intrinsic depth.
2. **Application obtained:** the actual OpenGL framebuffer storage inspected after context creation. PsyCoLab requests at least 10-bit internal precision (or the higher reported signal depth) by default; when unavailable it visibly reports a fallback. An 8-bit Windows signal report does not cap the application's internal buffer request, but the outgoing signal can still be 8-bit. A 16-bit floating-point channel does *not* contain 16 uniformly spaced bits in [0, 1].
3. **Measurements demonstrate:** your saved photometer readings at specified normalized commands, with means, standard deviations, differences and your explicit assessment. Even distinguishable time-averaged luminances cannot by themselves distinguish native 10-bit hardware from temporal/spatial dithering or FRC.

The manufacturer's advertised specification is a **fourth, optional note**; keep it independent of the three observations above. A claimed or reported “10-bit” signal is not an automatic experimental pass.

## Procedure

1. Bind the physical monitor and finish Geometry. Check Windows resolution, refresh rate, output mode, LUT/gamma, HDR and any display processing. Allow the display and photometer to stabilize. Keep these settings fixed and record them in **Instrument notes**.
2. Open **Calibrate → Output precision → Inspect selected output format**. No photometer is required for this step. The software checks the selected output's reported signal depth and the buffer actually obtained. If higher precision is unavailable, it shows a fallback but does not prevent ordinary presentation testing.
3. For the **near-black diagnostic**, choose **Halving**. With the same centered 6° square and dark surround, measure command 1, 1/2, 1/4, …, 1/65536 and finally 0. Record repeated readings and allow settling; use repeated black-reference measurements to assess drift. The point where differences disappear can reflect photometer limitations, noise or the display black floor. It does **not** reveal a count of all output codes.
4. For **fine-step precision**, choose **Fine** and a reference depth such as 8 or 10. PsyCoLab tests nine neighbouring digital commands around each chosen centre (default 0.1, 0.5 and 0.9), in a reproducibly shuffled order. Include the background level of your actual experiment. At each command, enter multiple real luminance values in cd/m² (aim for at least five). The values are saved immediately and never silently promoted into the main luminance/gamma map.
5. Review the raw measurements, sample variation, response drift and photometer uncertainty. Use **Save my measurement assessment** to record what is actually distinguishable, *not* to declare native panel bit depth. If the result is inadequate, choose **Inconclusive** and explain why. The assessment of fine increments requires a fine sweep, rather than the halving test alone.
6. If output depth, driver settings, refresh mode, monitor binding or graphics path change, repeat the relevant checks. PsyCoLab warns when a newer inspection differs from a saved measurement; it preserves both records.

For normalized commands, a nominal single-code spacing is
\(1/(2^8-1) \approx 0.00392157\) for 8-bit and
\(1/(2^{10}-1) \approx 0.000977517\) for 10-bit.
These are **command spacings**, not expected equal luminance increments: real luminance follows the display transfer function and may be affected by colour management, dithering or other processing.

## Graphics path and precision limits

Scientific static stimuli and the photometer patch now share the same floating-point texture upload and nearest-neighbour sampling implementation (`FloatingTexture`, `GL_LUMINANCE32F_ARB`). The one-texel photometer patch is enlarged to the calibrated square. The obtained framebuffer, subsequent GPU/display signal processing and the physical light output are still separate precision limits. A float texture alone cannot make an 8-bit framebuffer or 8-bit output signal behave as 10-bit.

Output records and measurement sessions are stored under the local configuration root in `diagnostics/output_precision/<profile-id>/...`, not participant trial data. The newest inspection and the last photometer measurement are tracked independently; running another inspection does not erase earlier measurements or their notes.

## What software tests cannot establish

The automated headless tests exercise command generation, persistence, window-format negotiation, calibration navigation and simulated rendering calls. They **cannot verify** the particular laboratory's 8/10-bit output, physical luminance steps, the meter's resolution, signal dithering/FRC or that Windows/GPU output settings match the laboratory claim. These require a real selected monitor and appropriate measurement equipment.
