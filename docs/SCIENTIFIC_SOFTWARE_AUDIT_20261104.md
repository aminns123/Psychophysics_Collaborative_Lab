# Scientific and software audit — 4 November 2026

## Baseline and scope

GitHub was checked before implementation. PR #207 merged into `develop` on
2 November 2026 as `21e103aad08804213936a9e6c6b3d22e8dbd4145`; PR #208 merged
develop into `main` as `c739f815c309ed35e1dc102b1ea2b7b87627648d`. Both resolve
to tree `8589249b52e748be0cee5254070361c5ae786906`. There were no open PRs at
that check. Work starts from develop on an isolated feature branch. Neither
protected branch was edited directly. The baseline Windows workflow
[41386436579](https://github.com/aminns123/Psychophysics_Collaborative_Lab/actions/runs/41386436579)
passed; this is baseline evidence, not CI evidence for these changes.

The [source inventory](audits/20261104_inventory.json) records LF-normalized hashes
and AST counts for 155 live Python modules in `src`, `simulations` and `scripts`,
11 registered experiments and 23 registered stimuli. No duplicate top-level
function/class definition was detected. This inventory establishes inspected
scope and traceability; an AST scan is not a proof of scientific validity.

The review traced each official experiment's condition construction, target
assignment, stimulus overrides, chronological events, response interpretation,
method selection, updates, termination and recorded estimator. Shared rendering,
geometry, layer composition, digital gamut, staircase state, canonical recording,
analysis, configuration, Review, calibration, local-extension discovery and refresh
were inspected alongside their regressions. The existing suite is a baseline;
the concrete counterexamples below were sought independently of passing tests.
This is a software audit, not an optical apparatus qualification.

## Implemented defects

| Priority | Reproduction and consequence | Correction and regression evidence |
| --- | --- | --- |
| P1 usability | Acquisition ends in an unconditional `return` in `app._main`, so a successful run deliberately closes the laboratory application. | Acquisition now returns to a result page after finalisation; workspace/drafts and original loaded-source identities survive. Two real UI mount/teardown cycles plus real recorded pipelines are tested, including repeated official experiments with virtual observers. |
| P1 scientific condition assignment | Modular ellipse ratios `0.70000001` and `0.70000002` both format as `ratio=0.7` under default `:g`. `unique_probe_conditions` deduplicates the two scientific cells. Two ratios × two strengths × two repetitions produces **four** trials instead of eight. Adaptive identities remain separate but primary condition grouping can combine their thresholds under one label. | Use round-trip float identity for the ratio while retaining historical integral labels such as `ratio=1`. Protocol version advances from `ellipse_modular_centre-2` to `-3`. An actual synthetic run now records eight responses with two distinct canonical condition labels and passes saved-run validation. Existing saved runs and fixtures are not rewritten. |
| P2 Windows process handling | A batch console waits while the GUI-subsystem .NET host launches console Python without being attached to it. Python allocates a second window. | Native host attaches to the parent console and retains its existing observer. Actual Windows batch/native tests assert that the external script and its console-owning ancestor are members of the same console. Direct GUI launch still permits one required Python console. |
| P2 report truthfulness | `software_check_payload` ignores its supplied `data_checks` when deciding overall pass/fail. A failing canonical-data check can coexist with report `result=pass` when the other checks pass. | All supplied saved-data checks contribute to the report result; generators are materialized once so serialized evidence is retained. Current development/Ready callers already check their own failures, so this was a reusable report defect, **not evidence that the current Ready workflow bypassed its checks**. |
| P2 scientific presentation | The shared threshold plotting function labels all values `Threshold C_disp`, including CSF digital peak-to-peak values and raw probe increments. At background 0.5, raw increment 0.1 is headroom-normalized C_disp 0.2, so the label implies a quantity differing by a factor of two. | Plot axis says `recorded digital units; not optical contrast`. Exact experiment-specific units remain in the existing primary rule and run dictionary. No estimate, saved numeric value or historical data format is changed. A rendered-plot regression inspects the actual axis label. |

`tests/test_persistent_session.py`, `test_single_console.py` and
`test_audit_20261104.py` contain the new reproductions. The plot cleanup also
removes unused local path/axis variables, after checking they have no reads.
No public scientific API or historical adapter was removed.

## Mathematical and scientific findings requiring interpretation

### Staircase accuracy metadata is a nominal approximation

Several procedures save `asymptotic_accuracy_target =
(up/(up+down))**(1/n_down)` for n-up=1. This is the local constant-probability
step-balance relation. It is not a general proof of the asymptotic proportion
correct for a finite-step staircase moving across a psychometric function.

For equal up/down steps and n-down=2 it reports sqrt(0.5), approximately 0.7071.
Changing the step ratio to the optional García-Pérez two-down setting 0.5488
makes the same formula approximately 0.8035. Those arithmetic values do not
establish that an arbitrary real observer, lapse rate, finite reversal count,
starting level and chosen step size will achieve those targets.

An [independent illustrative reproduction](audits/20261104_reproductions.json)
uses p(correct)=0.5+0.5×logistic(log-strength), a two-down/one-up rule,
100,000 burn-in responses and 1,000,000 retained virtual responses (seed 821).
All equal-step cases have nominal target 0.7071. Model probability evaluated at
the median presented reversal is approximately 0.7067 with step 0.05, 0.6888 with
step 0.5, and 0.7500 with step 2 in the logistic coordinate. This finite, unbounded
model illustrates step-size/estimator dependence; it is neither a formal
asymptotic proof nor a simulation of calibrated apparatus or every study's bounds.

García-Pérez's [1998 original study](https://pubmed.ncbi.nlm.nih.gov/9797963/)
demonstrates dependence on step magnitudes and psychometric-function properties,
and bias/limited precision for short fixed-step staircases. The code's optional
ratios match that paper, but its recommendations have a restricted setting.
[Levitt's original paper](https://pubmed.ncbi.nlm.nih.gov/5541744/) supplies the
transformed up/down context; it is not a blanket finite-step validation.

Review now explicitly calls the saved accuracy metadata a nominal local
approximation and warns that accuracy is not guaranteed. The frozen scientific
procedure, formula, saved metadata keys, observations and fixtures remain intact.
A future scientific revision can rename/version the metadata after protocol
review; old runs must retain their original meaning. No numerical rule was
changed merely to simplify its implementation.

### Contrast conventions must stay distinct

| Quantity | Definition / example | Scope |
| --- | --- | --- |
| Raw probe increment | d = I_probe − B. B=0.8, d=0.1 means nominal I_probe=0.9. | Existing line-position and non-modular ellipse staircase/result units. |
| Bright digital headroom fraction | C = d/(1−B). The same B=0.8, d=0.1 gives C=0.5. | ProbeLine input and the opt-in modular ellipse's saved strength. |
| CSF digital peak-to-peak modulation | I=B+(C/2)×envelope×sin(phase). At B=0.5, C=0.2 gives nominal unwindowed extrema 0.4 and 0.6. | CSF saved strength. Gaussian/taper and pixel sampling can reduce the actually sampled extrema. |
| Teaching Gabor modulation | I=0.5+0.5×C×envelope×cos(phase). | Digital normalized modulation; not a photometer reading. |
| Optical Weber contrast | (L_probe−L_background)/L_background. | Requires measured luminance transfer at the actual display/settings. Digital C_disp cannot substitute for it. |

The four migrated detection studies deliberately convert raw increment to
ProbeLine's headroom fraction at the rendering input, and record the raw quantity.
The modular study deliberately uses normalized headroom strength end to end.
Do not pool these thresholds just because both use the same TSV column name.
The per-run dictionary and scientific protocol determine its meaning.

GaussianFixation and GaussianSceneFixation intentionally preserve the historical
`min(1, background + increment)` convention. At B=0.95 and increment 0.09, the
realized peak increment is 0.05, not 0.09. This is an explicit historical design
choice, not a reason to silently replace its mathematics with GaussianFixationSpot's
normalized convention. Researchers changing background must inspect the resulting
marker and any overlap. No historical fixation equation was changed.

### Degenerate alternatives and physical precision

Setting TeachingGabor orientation to zero yields identical positive/negative-tilt
images, despite different target labels. This is reproduced directly from its
renderer. Such a condition can be an intentional catch/chance condition, so this
audit does not invent a prohibition or reinterpret its responses. Researchers
must avoid treating it as an informative tilt-discrimination threshold. Likewise,
zero digital contrast intentionally makes a target optically absent.

The staircase's positive Python-float floor prevents an absorbing numerical zero;
it is not the minimum contrast the framebuffer or panel can show. At sufficiently
small modulation, even double-precision addition around background 0.5 yields
identical commands, and float-texture/framebuffer/panel quantization can dominate
at much larger contrasts. Software-visible positive strength is not proof of
physical detectability. Boundary flags alone cannot calibrate output precision.

## Official experiment review

All 11 retain one STIMULI mapping and scientist-owned experiment procedures.
The complete parameter inventory is in the accompanying JSON.

| Experiment | Conditions, response and method observations |
| --- | --- |
| `example_experiment` | Alternating left/right targets, original finite accepted count; optional teaching adaptation or fixed strength. Its alternating original order is deliberate and predictable, not randomized by this audit. Strength is line increment above 0.5. |
| `probe_above_below` | Seeded balanced target order, positive y=above, negative y=below; original finite count and optional teaching/fixed methods preserve alternative equality scoring. |
| `orientation_task` | Seeded negative/positive tilt; signed selected magnitude, Gabor digital modulation. Original/fixed/finite adaptive methods do not establish a threshold merely by completing the response count. Zero tilt can be degenerate. |
| `orientation_adaptive` | Consecutive n-down/n-up multiplicative rule with explicit factors and accepted-response goal. Completion is a teaching task, not proof of reversal convergence. Fixed mode is nonadaptive. |
| `contrast_sensitivity` | Frequency × independent staircase replicate; equiprobable target side, fixation→grating→response. Digital peak-to-peak modulation; median final presented reversals per complete track, arithmetic mean over all configured repeats of a frequency. Nominal accuracy warning applies. |
| `contrast_sensitivity_windowed` | Inherits the same selection/update/response rules, with its own circular flat-interior/edge-only-fade renderer and aperture-aware Review. It does not silently inherit Gaussian-only fields. Hard edges introduce spatial energy beyond the carrier. |
| `line_position_baseline` | Horizontal condition positions, above/below probe target, additive probe followed by historical fixation. Raw probe increment, geometric mean of retained presented reversals per track; condition mean only when all repeats complete. |
| `line_position_flanker` | Same probe task, with independent flanker at x=−3 degrees; signed flanker modulation, additive probe, fixation last. Local headroom must account for sampled overlap, not simply nominal background. |
| `ellipse_centre` | Aspect ratio cells, ring present, centred line, exactly one target interval; interval 1→ISI→interval 2→first/second answer. Raw probe increment, median presented reversals; preserved additive composition. |
| `ellipse_major_axis` | Position × ratio × selected ring/base cells, independent track repeats. Exactly one probe interval; same raw-increment convention and median estimator. Baseline and ring conditions remain scientifically distinct. |
| `ellipse_modular_centre` | Independently located/rotated ring, probe and Gaussian spot; over-composition rather than historical additive probe. Normalized bright headroom strength. Close-ratio identity collision repaired with protocol version 3; existing recordings remain unchanged. |

Adaptive and fixed methods share event/recording paths but not staircase state.
Fixed schedules count scientific condition × strength × repetitions, deduplicating
track replicas only. Targets are balanced per condition/strength for even repeat
counts; odd counts differ by one. Fixed mode records counts/accuracy and does not
invent reversal thresholds. Modern reversal direction starts at the actual
starting presentation; zero-motion boundary holds do not create reversals.

## Stimulus and rendering review

All 23 registered stimuli were inventoried: 22 library classes and the
`geometry_bar` calibration diagnostic. Their equations were reviewed:

| Group | Classes and findings |
| --- | --- |
| Direct geometry | LinePatch, SquarePatch, RectanglePatch, EllipsePatch, AnnulusPatch: explicit degree geometry, ellipse semi-axes distinguished from diameter, annulus inner ratio squared in the radius test. Enlarged raster support is implementation extent, not a rescaling of scientific size. |
| Teaching/legacy marks | FixationCross, VerticalLineProbe, ExampleWhiteLine, ResearcherVerticalLine: binary mark masks and digital commands. Legacy finite apertures/strict versus inclusive edges are preserved. Existing alias classes are not removed because public scripts and saved presets can reference their IDs. |
| Gaussian/periodic patches | GaussianDot, SinusoidalGrating, GaborPatch, TeachingGabor: Gaussian SD, cycle/degree phase and carrier amplitude inspected. Legacy Gaussian and optional square hard/faded apertures remain separate designs. |
| CSF | ContrastSensitivityGrating: compact Gaussian support, outer-sigma cosine taper. CircularWindowedSinusoidalGrating: full central amplitude, radial edge-only taper. Their envelopes are scientifically different; parity is not claimed between them. |
| Independent detection objects | EllipseRing uses an axial inset on both semi-axes, not constant normal ring thickness. ProbeLine uses fractional pixel-area coverage. FlankerGrating uses signed amplitude. GaussianSceneFixation preserves raw, untruncated historical blend; GaussianFixationSpot uses truncated normalized headroom; GaussianFixation preserves its existing capped peak. |
| Composition | ComposedScene remains a public recipe adapter; Scene/Drawing are still used by public classes and compatibility scripts. Their infrastructure is not an obsolete second stimulus library to delete. |
| Calibration diagnostic | `geometry_bar` resolves requested millimetres or visual angle to independently calibrated x/y pixel pitch, rounds to a realizable bar length and records the realized size/angle. It requires a real ruler measurement to establish physical agreement. |

Ordered `over` composition removes each layer's own premixed background once;
it does not multiply pixel coverage twice. Explicit `add` adds the deviation
from background once. At B=0.5, an underlying command 0.8 plus probe increment
0.3 would reach 1.1 and must fail gamut validation; over-composition has a
different scientific meaning and must not be substituted as a cleanup.

Physical presentation samples actual pixel centres with independent x/y pitch
and flat-display atan angular coordinates. Viewport clipping takes the visible
intersection and does not recenter/resize the aperture. Probe coverage preserves
neighbour-step calculations across clipped boundaries. Geometry assumes a centred
eye normal to a flat display; it does not measure eye position or retinal optics.
Carrier Nyquist checks alone cannot qualify hard-edge bandwidth or all off-axis
sampling effects. Synthetic fallback headroom grids are explicitly unqualified;
actual display-grid preflight and strict final gamut checks remain required.

## Recording, analysis and application reliability

The frozen runner and RunContext files are byte-identical to the baseline after
the lifecycle fix was moved into the coordinator. Their original finalisation
continues to preserve primary/cleanup errors, partial journals, snapshots,
accepted counts, and the final manifest. Only `completed` is presented as a
successful experiment. Participant abort, safety ceiling, timeout/exception,
recording failure and incomplete return remain separate outcomes. Recovery uses
the exact failed runner allocation, not a global latest-run guess. Asynchronous
tones are drained outside timed presentation before navigation permits another run.

Trial schema remains 1 (20 canonical columns), manifest schema remains 3.
Readers keep historical text columns and reject unknown newer schemas; no
historical recording is migrated in place. Append-only trial/journal writes and
atomic JSON replacement retain their original integrity mechanisms. Run index
and workspace state are convenience projections, not substitutes for canonical
records. Scientific post-hoc primary estimates still use the declared estimator;
generic exploratory summaries retain their separate warning and reversal basis.
Completed tracks can remain eligible in an aborted/ceiling run under the existing
primary rule, but incomplete conditions are excluded and run status remains visible.

Review still resolves the actual selected method, stimulus overrides, source
ownership and files. Repeat configuration never reuses a previous override.
Monitor binding, resolution, profile-revision hashes, synthetic/physical record
separation and nonwaivable operational constraints remain in force. Geometry,
photometry and timing verification flags remain explicit human declarations
with recorded evidence; software cannot independently certify them. Refresh
uses a clean interpreter and parameter/source checks. Local extension trust,
fingerprints and Draft/Test/Ready status remain distinct from apparatus qualification.

No broad adapter removal is justified: archived #207 implementations are frozen
test oracles; parameter compatibility supports historical presets; Scene helpers
have active consumers; documented script/module entry points can have external
users. The old setup/recovery paths are retained until independent clean-Windows
acceptance. See [Windows launcher inventory](WINDOWS_LAUNCHERS.md).

## Validation and remaining limits

Focused native Windows checks passed for lifecycle, acquisition finalisation,
calibration returns, refresh, existing setup/qualification, compiled startup,
console ownership, external script arguments/exit codes and setup failure.
An actual first-time source environment was installed through Run_PsyCoLab.bat
on the available Windows host with an already installed CPython 3.11.9. This is
not a fresh operating-system image with no Python. Independent zero-Python
Windows installation acceptance remains outstanding; the known-working explicit
setup route therefore remains available.

The new audit regressions plus affected Review/analysis/frozen-source tests passed
(68 tests in their focused run). The exhaustive local Windows partition completed with **2,982 passed and 3
platform-specific skips** (2,985 collected tests). A compact-screen test initially
raced a focus-triggered scroll animation; its driver now settles focus scrolling
before positioning/clicking, and the entire affected group passed on rerun. The
latest strengthened session and native-launcher regressions were also rerun.
Proposed-change GitHub Windows CI is recorded separately in the delivery evidence;
a passing baseline workflow is not a passing workflow for new commits.

Required laboratory checks remain: independent photometer transfer/gamut and
precision measurements; photodiode photon timing; actual refresh/vsync/mode
verification; display scaling and geometry/ruler checks at chosen locations;
input-device latency and held-key behaviour; acoustic onset/latency if tones are
used; physical two-consecutive-run testing on the intended apparatus. The Windows
speaker request remains asynchronous and is not an acoustically calibrated cue.
No simulation, PNG preview, floating texture, package installation or software
test result is a substitute for these measurements.
