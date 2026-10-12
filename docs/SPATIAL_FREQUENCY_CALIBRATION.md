# Spatial frequency and geometric display calibration

PsyCoLab's current CSF reference grating previously fed values such as `63`
and `252` directly into the GLSL sinusoid as **radians of phase across the
normalised grating quad**. They were **not cycles per degree**. Relabelling
those numbers would have made stimulus frequencies scientifically incorrect.

The new CSF workflow uses real spatial units on **one shared experiment
configuration screen**, then chooses human acquisition or a virtual observer
at final review.

## New researcher workflow

1. Open **Calibrate**. Select the monitor and choose **Edit / copy display
   profile**. Make a local profile and explicitly bind the physical display.
   Measure its **active image area** (width and height in metres) and the
   observer's **eye-to-screen distance** with a ruler or tape. Detect or enter
   the actual framebuffer resolution. Save the profile, noting measurement
   provenance. A Windows DPI-scaled logical resolution is not necessarily the
   physical framebuffer resolution.
2. In Calibrate, inspect **pixel pitch (mm)**, **pixels per degree at gaze
   centre** on both axes and the **spatial Nyquist limit**. Run a fullscreen
   ruler/geometry diagnostic, record the measured bar width and try the spatial
   grating diagnostic. Repeat whenever the monitor, resolution, eye distance,
   or image scaling changes.
3. Open **Experiment → Configure Experiment** and choose **Stimulus
   conditions**. Enter the number of conditions, a unit and the values. For
   example `cycles_per_degree` with `2,4,8`, or `degrees_per_cycle` with
   `0.5,0.25,0.125`. Both specify the same physical spatial frequencies.
4. Adjust staircase count, n-down/n-up, step sizes, initial 1-down and stopping
   rules once. The **Review** page shows the canonical cpd frequencies,
   selected display geometry, Nyquist bounds and the verification status.
5. Choose **Run human experiment** to launch the fullscreen renderer, or
   **Run simulation** to supply observer thresholds/slope/preference/seeds.
   Both use exactly the same condition and adaptive configuration. A separate
   *Scenarios* screen remains for older direct scenario tests.

## Mathematical basis

For an active display of physical width `W` m and `N_x` actual pixels,
and physical height `H` m and `N_y` pixels, the local pitches are

```text
p_x = W / N_x               p_y = H / N_y            [metres/pixel]
```

At an eye distance `d` m, the one-pixel visual angles at the fixation
centre are

```text
delta_x = (180/pi) atan(p_x/d)     delta_y = (180/pi) atan(p_y/d)
pixels_per_degree_x = 1/delta_x   pixels_per_degree_y = 1/delta_y
```

For input frequency `f` in **cycles/degree**, the grating's phase is
computed *per fragment* using the actual visual angle corresponding to its
physical pixel coordinate. In the screen axes:

```text
theta_x(px) = (180/pi) atan((px - cx) p_x / d)
theta_y(py) = (180/pi) atan((py - cy) p_y / d)
phase = 2*pi*f*( (theta_x-theta_x_at_stimulus_centre)*cos(orientation)
                +(theta_y-theta_y_at_stimulus_centre)*sin(orientation) )
```

This avoids using the average whole-screen field-of-view/pixel ratio, which
is not the correct *local* angular derivative, especially away from fixation.
The x and y pitches are independent, so a non-square pixel geometry is
not incorrectly treated as isotropic.

**Sampling warning:** no requested spatial frequency should exceed the pixel
grid's Nyquist limit along the direction it varies. The program rejects
unrenderable physical frequencies if a profile resolution is available at
review, and checks again against the actual fullscreen resolution at launch.
This does not correct aliasing from imperfect hardware optics or scaling.

## Three distinct notions of calibration

- **Geometric**: screen active size, actual pixels, eye distance, position,
  pixel pitch and visual angle. These can be measured with rulers and checked
  using full-screen patterns. Saving a profile alone is not evidence that the
  physical dimensions were measured or that the display is 1:1 mapped.
- **Photometric**: luminance (cd/m²), gamma/transfer function and background
  command-to-light conversion. Requires a photometer or equivalent measured
  table, and is NOT inferred from resolution, pixel pitch or gamma defaults.
- **Temporal**: actual image display/onset, dropped frames and photon timing.
  Requires dedicated timing measurements (e.g. photodiode) for strong timing
  claims. OS refresh numbers are not photon-onset evidence.

The reference profile still has **unverified physical/luminance provenance**.
For a new physical display, create and measure a local profile. Current CI
tests verify the mathematics and configuration/virtual pipeline, **not** that
a real GPU compiled the legacy Pyglet GLSL shader or that a photodiode saw the
planned grating. A Windows hardware-acceptance run remains necessary.

## Historical reproduction and safety

The explicit `legacy_shader_radians` mode preserves the old reference
phase coefficients without pretending they are cpd. Older saved
`condition_values` that have no `condition_unit` are classified as
legacy when reused, rather than silently reinterpreted. The older
standalone seeded reference virtual-observer scenarios also retain their
legacy defaults until deliberately changed.

For a new experiment on a calibrated display choose **cycles_per_degree**
(the new shared experiment default), or **degrees_per_cycle** (period, converted
to cpd). Only those two modes can be interpreted as physical frequency, and
their correctness is conditional on the physical geometry you enter.

All raw trials remain untouched by calibration changes to subsequent runs.
The run's configuration, runtime display record and resolved experiment
retain the selected units and geometry. Reanalyse and report old datasets in
the units and calibration assumptions actually used at acquisition.
