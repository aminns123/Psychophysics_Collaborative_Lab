# Display geometry ruler check

The display geometry check is framework/display infrastructure, not a
participant experiment. It writes to:

```text
<external data workspace>/
└── diagnostics/
    └── display_geometry/
        └── <monitor_profile>/
            └── YYYY-MM-DD/
                └── check_NNN/
                    └── geometry_check.json
```

No participant acquisition folder or canonical trial file is changed.

## Visual angle

For a centred line of physical length `L` at viewing distance `d`, the visual
angle is

```text
theta = 2 atan(L / (2d))
```

and the length required for a requested visual angle is

```text
L = 2 d tan(theta / 2)
```

The monitor profile and actual fullscreen resolution then convert physical
length to pixels. Pixel rounding is recorded explicitly, including the realised
physical length and realised visual angle.

## Laboratory procedure

1. Measure the actual active display width/height and viewing distance.
2. Select the corresponding monitor profile.
3. Start with a convenient physical check such as 100 mm, or an angular check
   such as 5 degrees.
4. Measure the white bar on the screen with a ruler.
5. Return to the Display Check page and record the measured length.
6. Investigate discrepancies before using geometry-sensitive experiments.

Automated tests can validate only the calculation. They cannot prove that the
physical screen dimensions, viewing distance, fullscreen rendering, timing or
photometric calibration are correct.

The legacy CSF `31.5` spatial scaling is not changed or reinterpreted by this
diagnostic.
