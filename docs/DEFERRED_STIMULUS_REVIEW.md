# Deferred stimulus review

This file records stimulus-specific questions that are deliberately **not**
changed during the public-v1 framework/TUI/launcher work.

## CSF shader contrast expression

The current CSF grating renderer uses the existing expression equivalent to:

```text
background + C_disp * envelope * sine / 2
```

This behaviour is preserved for now.

A separate possible interpretation is that a peak increment might instead be
constructed from the remaining digital display range:

```text
background + C_disp * (maximum - background)
```

Those expressions are not assumed to be interchangeable. Changing between them
would change the displayed stimulus and therefore requires an explicit
scientific/rendering review.

## Normalised display contrast

The adaptive quantity is **normalised display contrast**,

```text
C_disp = (I_n - I_b) / (I_M - I_b)
```

not conventional Weber contrast. Legacy saved field names containing `weber`
are retained for compatibility while the code is migrated.

## Legacy spatial condition scaling

`Interface/config.py` retains the legacy `31.5` scaling used to create current
CSF conditions. It is not silently replaced with measured pixels-per-degree.
The relationship between this value, the shader's radians/width convention,
and the intended cycles/degree must be verified during the later stimulus
review.

## Rule for public-v1

Framework, packaging, TUI, session recording and launcher work may proceed, but
a change that alters rendered stimulus behaviour must be reviewed separately.
