# Original stimulus class inventory

Source: `stimuliC.py` at commit `1c3177594e00f0b26fa361238db0f4db5de403fa`. All 59 class definitions were inspected, including shadowed names. This table records translation boundaries, not pixel equivalence.

| Original class (line) | Drawing/reuse boundary |
|---|---|
| `Grating` (5) | Gaussian-windowed sinusoid → gabor geometry; retain anisotropic/dynamic/RGB shader and adaptive I/O separately; no CSF replacement |
| `Rectangle` (98) | Shadowed shader-backed textured rectangle (first definition) |
| `RectangleT` (161) | Textured Gaussian-alpha rectangle, not a plain rectangle; deferred texture parity |
| `Line` (223) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Movie` (262) | Stateful media/motion renderer; explicitly retained/deferred, not replaced by a static recipe |
| `MovieGrid` (313) | Stateful media/motion renderer; explicitly retained/deferred, not replaced by a static recipe |
| `MaskNumpy` (478) | Inverse generalized-Gaussian alpha aperture; not equivalent to gaussian_dot; deferred |
| `Mask` (499) | Inverse generalized-Gaussian alpha aperture; not equivalent to gaussian_dot; deferred |
| `DotLattice` (555) | Repeated dot/Gabor composition possible; lattice placement/mask/stochastic parity deferred |
| `Lattice` (613) | Repeated dot/Gabor composition possible; lattice placement/mask/stochastic parity deferred |
| `Pill` (665) | Orientation/circle/capsule-like mask; composite primitives available, shader-specific soft edge deferred |
| `OrientCircle` (689) | Orientation/circle/capsule-like mask; composite primitives available, shader-specific soft edge deferred |
| `Text` (753) | Presentation instructions/termination layer; no text raster copied into scientific library |
| `Dot` (774) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_Size` (793) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Line_staircase_LR_ADMs` (996) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_two_LR_ADMs` (1073) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Sound_Line` (1233) | Audio action/presentation service; deferred, not a static visual primitive |
| `RDK` (1319) | Stateful media/motion renderer; explicitly retained/deferred, not replaced by a static recipe |
| `RDKMod` (1376) | Stateful media/motion renderer; explicitly retained/deferred, not replaced by a static recipe |
| `Rectangle` (1467) | Wireframe/filled GL rectangle; rectangle/square primitive covers filled geometry only |
| `Cube` (1524) | 3-D/bit-depth display path; deferred, no equivalence to grayscale Scene |
| `RectangleBitDepth` (1595) | 3-D/bit-depth display path; deferred, no equivalence to grayscale Scene |
| `FileSave` (1717) | Persistence belongs to RunContext/canonical data; deliberately not a drawing |
| `Line_ADM` (1758) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_ADM_Termination` (1812) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_ADM_Flicker` (1876) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Grating_M` (1939) | grating: sine, flat square aperture, digital amplitude contr/2; explicit fs conversion |
| `Grating_Mnew` (2044) | Modified peak waveform; deferred (ordinary sine would change the stimulus) |
| `Grating_ADM` (2162) | Gaussian-windowed sinusoid → gabor geometry; retain anisotropic/dynamic/RGB shader and adaptive I/O separately; no CSF replacement |
| `Grating_ADM_new` (2318) | Gaussian-windowed sinusoid → gabor geometry; retain anisotropic/dynamic/RGB shader and adaptive I/O separately; no CSF replacement |
| `Line_MeasureCPD` (2553) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Sound_dot` (2652) | Audio action/presentation service; deferred, not a static visual primitive |
| `Dot_StairCase` (2695) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_Size_right` (2720) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_Size_left` (2773) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_staircase_right` (2828) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_staircase_left` (2949) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Text_termination` (3010) | Presentation instructions/termination layer; no text raster copied into scientific library |
| `Dot_stairCase_centre` (3031) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_stairCase_centre_beep` (3084) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Dot_Termination_criteria` (3142) | gaussian_dot drawing; legacy texture/size/alpha, response, termination and beep behaviour not copied into primitive |
| `Line_const_LR` (3174) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_staircase_LR` (3238) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `EllipseCircle2D` (3318) | annulus; normalized squared-radius ring for EllipseCircle2D; radius variant smoothstep/degree-width requires separate parity |
| `EllipseCircle2D_radius` (3404) | annulus; normalized squared-radius ring for EllipseCircle2D; radius variant smoothstep/degree-width requires separate parity |
| `two_lines_displacement` (3541) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `two_SOA_frequency_phase` (3664) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `two_flashing_frequency_phase` (3832) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `drifiting_grating` (4002) | Stateful media/motion renderer; explicitly retained/deferred, not replaced by a static recipe |
| `two_lines_displacement_baseFind` (4180) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_condition_phaseFrame` (4356) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_condition_timeFrame` (4497) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_ADM_phase` (4634) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `two_lines_phase_probe` (4744) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `two_lines_Apart` (4953) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `two_lines_Apart_old` (5096) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_ADM_Time` (5277) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |
| `Line_ADM_Time_main` (5349) | line/rectangle + Scene composition for static geometry; response, condition, flicker/frame/SOA state stays in procedure; temporal variants deferred |

The newer local `Events/stimuliC.py` has three classes: `Grating_ADM`, `Dot_stairCase_centre`, and `Text`. All remain unchanged and authoritative for existing CSF acquisition. Static generic functions do not stand in for their renderer, lifecycle or scientific state.

Plain file helper functions in the original library are not stimuli. They were not ported: the canonical runner owns persistence.
