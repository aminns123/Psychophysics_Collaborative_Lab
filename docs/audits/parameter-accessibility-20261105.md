# Scientific parameter accessibility — 5 November 2026

## Initial inspection

Integration baseline: `develop` e81c4cfa9779b2c41e28f4e34ff6a497391d5be4;
`main` 340889c5d284e1a28ea75d97422aed75ec54b3ae. This change targets
develop only, without merging or releasing.

The ten official experiments already declare their inputs as ConfigFields and
their selected stimulus parameters as StimulusSpecs. Configure intentionally
shows universal setup; Review's input editor exposes scientific inputs and each
compatible stimulus slot. The real prepare_stimuli path resolves overrides for
Review and acquisition; selected snapshots feed RunContext and saved provenance.
No missing second configuration registry is needed.

The practical gaps were: stimulus edits required a named preset; derived ellipse
axes were not explicit; declared ranges were absent from Review descriptions;
fixed scientific definitions were easier to find in Python than in Review; and
wide tables/source columns made complete descriptions awkward on small screens.
Existing parameter precedence, validators, readiness and source-change checks
are necessary and are retained. See the accompanying [per-parameter inventory](parameter-coverage-20261105.md).

## Focused changes and use

Select an experiment → Configure → Review. Use **Edit selected value** for the
controlling experiment input or selected stimulus base. In a stimulus editor,
**Apply for this run** retains a validated snapshot without creating a preset;
then **Apply to Review** applies the complete configuration. Named presets and
advanced JSON remain optional. Test/Run consume that same reviewed selection.

Review's group selector reduces the list to one existing logical group. **All
parameter groups** restores it. Full details / **F2** opens a read-only,
soft-wrapped, scrollable text view with the exact selected value, definition,
units, declared limits, authority, source and edit route. Escape returns.
Hovering a parameter shows its full explanation. Configure and stimulus fields
have constraint tooltips; F2 on a focused control shows its full explanation and
current value. Elsewhere in Configure/Author/experiment information, F2 exposes
the focused control's explanation or the screen's complete explanatory text.
Source navigation and the expanded table retain their existing actions.

## Ellipse-centre before and after

| Quantity | Before | After |
| --- | --- | --- |
| Outer horizontal radius | Existing `ring_radius_deg` input | Same authoritative input, with range and edit route |
| Horizontal diameter | Implicit `2a` | Explicit read-only result |
| Aspect ratios | Existing comma-separated input | Same input; all configured ratios and derived vertical axes shown |
| Vertical radius/diameter | Implicit `a*r`, `2*a*r` | Explicit read-only values for every configured ratio |
| Centre position | Selected common y; x=0 fixed in trial layout | Existing y editable; actual phase placements and fixed definition visible |
| Inner outline | Existing selected stimulus `inner_inset_deg` | Editable without a preset; inner semi-axes and axial-inset explanation shown |
| Probe height/width | Existing selected stimulus `length_deg`, `width_deg`, named-save route | Apply for current run; same renderer and recorded snapshot |
| Probe position/displacement | Set by trial layout and selected centre y | Actual resolved phase placements, read-only when protocol-controlled |
| Probe start/adaptation | Existing absolute starting intensity and log rule | Same inputs and arithmetic; increment and headroom conversion explained |
| Ring strength | Required `ring_increment`, no default | Same required input; effective renderer contrast remains visible |

The renderer uses local unrotated semi-axes `a` and `b=a*r`. Changing `r` with
fixed `a` preserves local horizontal width `2a`; orientation rotates those axes.
The ring is the outer ellipse minus an inner ellipse with semi-axes
`a-inner_inset_deg`, `b-inner_inset_deg`. This is an **axial inset**, not constant
perpendicular outline thickness. No geometry or default was changed.

## Intensity definitions and scientific decisions

The five software-validation probe studies (line baseline/flanker, ellipse
centre/major-axis, and the separately developed modular ellipse) do not all use
the same recorded strength convention. The four established line/ellipse probe
studies adjust and record digital increment `ΔI=I_probe-B`; their bright probe
and ring renderers use `C_disp=ΔI/(1-B)`, producing `I=B+alpha*C_disp*(1-B)`.
Alpha includes coverage; overlapping layers still obey the existing headroom
validation. The modular ellipse retains its own C_disp convention. The two CSF
studies adjust digital peak-to-peak modulation; the sinusoidal carrier amplitude
is half that before its existing envelope. The four teaching studies retain
their own declared strength mapping and original/adaptive/fixed-mode meanings.
Review shows each experiment's existing scientific declaration and actual
selected method resolution. A starting value is not an estimated threshold.
Relative `(I-B)/B` is explicitly digital and is not luminance Weber contrast.
No global contrast conversion, adaptive step, reversal, stopping rule, threshold,
data column or scientific version was changed.

| Official experiment | Adaptive/selected strength and renderer relationship | Result meaning |
| --- | --- | --- |
| contrast_sensitivity | Digital peak-to-peak C; carrier amplitude C/2 before Gaussian envelope | Existing retained-reversal threshold rule |
| contrast_sensitivity_windowed | Digital peak-to-peak C; carrier amplitude C/2 before circular window/fade | Existing retained-reversal threshold rule |
| line_position_baseline | ΔI above selected B; probe renderer C=ΔI/(1−B) | Recorded increments and existing reversal estimator |
| line_position_flanker | Same probe ΔI; flanker/layer headroom constraints retained | Recorded increments and existing reversal estimator |
| ellipse_centre | Same probe ΔI; ring uses separately selected ring_increment/(1−B) | Recorded increments and existing reversal estimator |
| ellipse_major_axis | Same probe ΔI; selected ellipse conditions/placements retained | Recorded increments and existing reversal estimator |
| orientation_adaptive | Gabor C, starting from selected stimulus contrast; I=0.5+0.5*C*envelope*cos(phase); original multiplicative up/down factors | Finite teaching demonstration, no scientific threshold claim |
| orientation_task | Optional adaptive/fixed Gabor C with same Gabor mapping; original uses selected stimulus contrast | Teaching responses/accuracy, no scientific threshold claim |
| probe_above_below | Optional adaptive/fixed digital increment above 0.5; I_line=0.5+increment; original uses selected stimulus base | Teaching responses/accuracy, no scientific threshold claim |
| example_experiment | Optional adaptive/fixed digital increment above 0.5; I_line=0.5+increment; original uses selected stimulus base | Teaching responses/accuracy, no scientific threshold claim |

Decisions left to the researcher:

- Ellipse-centre's existing experiment validator requires every minor semi-axis
  to exceed **0.16 degrees**, independently of the stimulus's editable inset.
  Actual rendering also validates the selected inset against both axes. A
  smaller selected inset does not relax that conservative protocol guard.
  Whether to relax it is a separate scientific decision.
- Fixed x=0 and the probe's shared centre/interval placement remain protocol
  definitions. Independent probe displacement or x-centre controls would change
  the scientific design and have not been introduced.
- A constant perpendicular outline, an alternative contrast convention, and
  equivalence to the thesis require manual scientific/physical validation.
  Software Test and mathematical agreement do not establish optical luminance,
  display timing, apparatus qualification or thesis equivalence.

Some teaching SCIENTIFIC_SPEC text describes the original fixed demonstration,
while optional methods have their own live resolution. Review explicitly labels
this as original protocol text; selected Run plan/estimator metadata determines
the current method. The original declarations and acquisition remain unchanged.

## Verification

Focused tests exercise all ten official studies' complete ConfigField and slot
coverage, derived read-only definitions, small-terminal F2 details, grouped
editing/source navigation, invalid edits, and ellipse edits through the actual
TUI into rendering, adaptive execution and saved provenance. Existing frozen
scientific regression tests remain unchanged. Final native and CI results are
recorded in the pull request. All test runs use disposable configuration/data;
no original research installation, calibration or data is modified.
