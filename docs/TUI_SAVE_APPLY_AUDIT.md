# PsyCoLab TUI: Save, Apply, Review and data persistence

This audit follows each user-facing mutating TUI action to its source of truth.
**No click is allowed to claim a successful save without successful validation
and, for durable settings, a reread from the filesystem.** Errors and success
are displayed close to the fixed top controls, not only below a long form.

## Action and persistence contract

| Page / action | Outcome and source of truth | Failure/success feedback |
|---|---|---|
| **Calibrate → Edit/copy profile → Save local revision** | Writes a **new local ID** for reference profiles and an **append-only revision** for existing local profiles under machine-local `profiles/<id>/revision_*.json`. Verifies the saved revision with the same profile loader used on restart. Never edits shared `configs/monitors/`. Immediately returns to Calibrate, selects the saved ID and refreshes the displayed values and cpd geometry. | Success notification names saved ID/revision and binding status; errors appear at the top of the editor and in a notification. |
| **Profile → Detect connected displays** | Enumerates OS display descriptors into *transient screen state*. No file is saved. | Visible selection instructions or detailed failure at the top. |
| **Profile → Use detected resolution and refresh** | Copies detected pixel mode/refresh into **editable draft fields**, not the physical screen dimensions. Only subsequent Save persists. | Visible confirmation, with explicit warning that active width/height and viewing distance need measuring. |
| **Save an unbound local profile** | Permitted as a **geometry draft**, with an explicit UNBOUND marker, without claiming it can be used to acquire human data. | Clear saved-draft message. **Human Run** rejects unbound local profiles until a bound display is saved. |
| **Calibrate → Run fullscreen check** | Validated `GeometryCheckRequest` exits the TUI and runs the physical diagnostic, which saves its own diagnostic record in local configuration. Does not rewrite monitor physical dimensions. | Visible validation errors; hardware errors go to run diagnostics. |
| **Calibrate → Record ruler measurement** | Appends a physical ruler result to the latest diagnostic JSON, retaining measurement history. Does *not* claim gamma or luminance calibration. | Immediate visible saved confirmation or failure. |
| **Experiment → Configure → Review** | Validates all entered fields against registered experiment and monitor; stores an ephemeral TUI draft, then builds an immutable reviewed request. Does not mutate previously collected participant trials. | Review blocked with a visible error and notification on invalid inputs. |
| **Experiment → Save new preset** | Validates the *entire experiment parameter set*, writes a new machine-local preset, then reads it back. Refuses an existing name. | Names the saved preset or explains why it was not saved. |
| **Experiment → Update selected preset** | Explicit user action to replace an existing preset. Writes previous JSON to `presets/<experiment>/.history/`, updates the current preset atomically, and verifies by reloading. | Names the updated preset or explains why it was not updated. |
| **Experiment → Load preset** | Loads and validates the selected preset, then populates *all* form controls and its navigation draft. The user must Review before an experiment launches. | Explicit loaded confirmation or failure, no silent partial application. |
| **Experiment → paired adaptive step calculator** | Changes only the requested step input/draft, not a saved preset or human run; user must Review. | Visible value/status, including any unsupported combination. |
| **Advanced Scenarios → Adaptive algorithm → Apply** | Validates a full proposed parameter set and copies it into the currently selected scenario form. Cancel discards changes; only Review and Run trigger synthetic data writes. | Top-of-screen success/failure and notification. |
| **Run → Review → Human / Simulation** | Uses one reviewed experiment specification, with distinct acquisition modes. Does not claim to have launched on invalid setup; human runs require bound local displays and physical-cpd resolution. | Errors above the review and virtual observer screen; launch creates canonical run data in the separate external data repository. |
| **Data → Generate plots/threshold analysis** | Creates only derived data under the original run's `analysis/` folder; raw accepted trials remain unchanged. | Action feedback above the Data form, with file paths. |
| **Data → Open image/run folder/report** | Opens existing, validated paths within selected external workspace. Does not modify recordings. | Visible failure if missing/not accessible. |
| **Top-level → Load Data Workspace** | Resolves and selects the external data directory, refreshes indexed participants/latest run. | Status visible at the top of the main setup form. |
| **Experiments / Stimuli / Help inspectors** | Read-only selection or opener; no silent persistence of edited scientific fields. | Notify on external editor-launch failure. |

## Display-geometry troubleshooting

To use a different monitor:

1. Open **Calibrate → Edit / copy display profile**.
2. Enter **active screen dimensions in metres**, e.g. `0.530` for 530 mm width, as well as the eye-to-screen distance. Enter pixel width/height for the current fullscreen mode.
3. Choose **Save local revision**. If there is no physical display binding yet, the file is saved as a **draft**. You do not have to perform detection before saving.
4. You should return to **Calibrate**, see the new **profile ID and revision**, and see recalculated pixel pitch and PPD values. If you reopen PsyCoLab, they should still be present.
5. To run a human experiment, **Detect connected displays**, select the correct display and save another revision. Make the required laboratory checks and explicitly qualify it for the experiment. No button claims to have verified physical dimensions or luminance automatically.

**Note:** reference profiles in Git are not modified by local Save. Lab
measurements and revisions belong to machine-local configuration, outside the
source repository and the participant acquisition data repository.

## Test levels and remaining laboratory acceptance

GitHub Actions exercises headless Textual button events and typed forms at
small terminals. New regression tests cover Save and reload after app restart,
error feedback for invalid dimensions, versioned profile updates, preset new/
update/load with backed-up history, and continued experiment Review with the
chosen values. Pre-existing tests cover adaptive Apply/Cancel, simulation
request fields, canonical runs, plots and geometry computations.

This does **not** certify real physical monitor binding, fullscreen framebuffer
size, luminance transfer function, Pyglet GLSL compilation, photodiode timing
or stimulus perception. Validate those on the actual Windows workstation before
collecting human data.
