# TUI control audit — 13 October 2026

The declaration inventory below covers every Button/Select/Input call in the four screen modules. Dynamic declarations generate multiple controls from experiment/scenario specifications; their actual fields are enumerated after the table. `editor.py` and `plots.py` provide OS launch functions rather than widgets.

## Interaction contracts (intent → validation → effect → persistence → failure)

| Screen/interaction | Complete-state validation and consequence | Storage/readback/navigation/restart | Cancel/failure and scientific units |
|---|---|---|---|
| Global navigation | switch page; preserve experiment draft in memory | no acquisition; session only except explicit calibration draft | no file write from ordinary navigation; controls stay docked |
| Experiment workspace/participant/settings | Load validates source/config/data separation; Configure checks identity/settings and restores selected experiment fields | workspace preference in ignored local checkout file; previous human setup in external data config; each new run snapshots settings | invalid data path rejected; synthetic IDs reserved; reuse never resumes staircase |
| Display selector/root | all valid profiles, active preference; missing requested ID visibly blocked | selection is root draft; saved profile active after calibration/Apply or human run | no qualification automatically; summary has source, revision and readiness |
| Configure fields and Review | coercion/experiment validation, calibration pairs and known-resolution Nyquist | in-memory draft; dedicated Change display persists local draft; Review owns hash | invalid fields preserve input; count/list and mode-specific units explained |
| Change display / Calibrate | Apply validates availability and revalidates on next Review; Refresh loads disk | selected ID and raw draft in machine-local preferences; geometry stays in profile | Cancel retains prior ID; independently saved calibration revisions persist |
| Paired step buttons | only supported 2AFC/log10 settings; validates requested destination | changes one draft field; no automatic count-triggered changes | unsupported rule leaves both steps unchanged; response counts are not step-size ratios |
| Preset Save/Update/Load | complete configuration validity; existing Save name rejected; Update archives prior JSON; Load validates before replacing widgets | local config presets and .history; verified readback; survives restart | invalid proposal leaves saved state; permissions failure is visible; geometry not duplicated in preset |
| Human Review/Run | reread profile hash; human blockers; OS binding preflight; renderer actual dimensions/range guard | allocates new external run only after preflight; canonical snapshots | unqualified/unbound/stale/range mismatch is actionable; no fallback/clamp |
| Unified simulation | adds only observer/seeds to reviewed experiment; typed model validation and disk hash | handoff closes TUI; shared data root, reserved synthetic IDs, per-run markers/seeds/model/virtual clock | no hardware/qualification claim; scenario results shown after return |
| Advanced scenario panel | experiment-owned fields, observer/seeds, all available profiles; shared simulation preflight | temporary scenario draft, then explicit Review/Run; no blanket restart persistence of arbitrary edits | selection changes panel; adaptive editor Cancel has no effect; errors do not rewrite real records |
| Adaptive scenario editor | apply combines proposed adaptive fields with whole scenario then normalizes | writes source-panel draft only; Review freezes proposed values | Cancel discards editor edits; calculators validate log-step semantics |
| Profile editor Save | profile model, binding choice, sources, ID uniqueness, expected revision; changes downgrade relevant status/qualification | append-only numbered local revision; loader equality/readback and active preference | Back doesn't save; explicit saved revisions survive; physical dimensions/distance remain manual |
| Detect / Use detected | Detect enumerates only; Use copies OS resolution/rate explicitly | draft until Save; unknown rate unchanged | no fabricated geometry/refresh; detection failure visible |
| Calibration inputs/launch | pure geometry/test plan, bounds/Nyquist/duration; binding preflight; actual fullscreen check | local-config diagnostic JSON carries exact profile/hash, request, realized bar and software flip intervals | failure reopens hub; this path never writes human trial records |
| Record ruler measurement | positive finite ruler entry and current diagnostic hash | revision-specific diagnostic with measurement history; readback on page | stale check rejected; no auto verification; mm/error% and uncertainty reviewed by researcher |
| Data run/inspect controls | owned external paths and run manifest; readers only | inspect run-owned manifest, canonical TSV, adaptive state and scenario report | absent artifact explicit; inspection never repairs raw data |
| Data derive figures/analysis | finished source run, real recorded values, valid retention/column | new analysis version, latest derived aliases; source hashes and units | no reversals produces no estimate; exported plots warn synthetic/censored; raw trials untouched |
| Image/folder launch | owned real PNG/manifest directory; no shell interpolation | system viewer, no scientific data mutation | unsafe/missing path rejected; plots are exploratory |
| Source inspection/Developer | real project file/editor executable; explicit scaffold/registration/docs | opens actual project in external editor; no source edits from navigation | missing editor visible; scaffold refuses overwrite; no builder added |

User-facing error feedback is provided through docked status cards or notifications. OS viewer/editor startup is an external process action; it does not verify scientific values. Profile/preset saves are explicit; ordinary unsaved drafts do not silently become acquisition settings after a restart. The dedicated calibration draft is described above.

## Source control declarations

| Source:line | Screen/handler owner | Type | ID expression | Button intention |
|---|---|---|---|---|
| `profiles.py:26` | `ProfileScreen` | Button | `'profile-back'` | 'Back' |
| `profiles.py:27` | `ProfileScreen` | Button | `'profile-save'` | 'Save local revision' |
| `profiles.py:48` | `ProfileScreen` | Button | `'profile-detect'` | 'Detect connected displays' |
| `profiles.py:50` | `ProfileScreen` | Select | `'profile-binding'` | See field/choice declaration |
| `profiles.py:51` | `ProfileScreen` | Button | `'profile-use-detected'` | 'Use detected resolution and refresh' |
| `profiles.py:76` | `ProfileScreen` | Input | `'profile-' + key` | See field/choice declaration |
| `profiles.py:78` | `ProfileScreen` | Input | `'profile-pixel-width'` | See field/choice declaration |
| `profiles.py:79` | `ProfileScreen` | Input | `'profile-pixel-height'` | See field/choice declaration |
| `profiles.py:83` | `ProfileScreen` | Select | `'profile-' + name` | See field/choice declaration |
| `profiles.py:85` | `ProfileScreen` | Input | `'profile-luminance'` | See field/choice declaration |
| `setup.py:164` | `shared composition` | Button | `f'nav-{key}'` | label |
| `setup.py:189` | `CodeViewScreen` | Button | `'back'` | 'Back' |
| `setup.py:229` | `ExperimentsScreen` | Select | `'inspect-experiment'` | See field/choice declaration |
| `setup.py:232` | `ExperimentsScreen` | Button | `'view-exp-definition'` | 'Inspect definition' |
| `setup.py:233` | `ExperimentsScreen` | Button | `'view-exp-runtime'` | 'Inspect runtime' |
| `setup.py:295` | `StimuliScreen` | Select | `'inspect-stimulus'` | See field/choice declaration |
| `setup.py:297` | `StimuliScreen` | Button | `'view-stimulus-source'` | 'Inspect stimulus code' |
| `setup.py:357` | `DisplayCheckScreen` | Button | `'calibration-return'` | 'Return to display choice' |
| `setup.py:358` | `DisplayCheckScreen` | Button | `'edit-profile'` | 'Bind / edit monitor profile' |
| `setup.py:359` | `DisplayCheckScreen` | Button | `'launch-geometry'` | 'Launch fullscreen calibration' |
| `setup.py:384` | `DisplayCheckScreen` | Select | `'geometry-monitor'` | See field/choice declaration |
| `setup.py:386` | `DisplayCheckScreen` | Select | `'geometry-test'` | See field/choice declaration |
| `setup.py:388` | `DisplayCheckScreen` | Select | `'geometry-mode'` | See field/choice declaration |
| `setup.py:395` | `DisplayCheckScreen` | Input | `'geometry-value'` | See field/choice declaration |
| `setup.py:397` | `DisplayCheckScreen` | Select | `'geometry-orientation'` | See field/choice declaration |
| `setup.py:404` | `DisplayCheckScreen` | Input | `'geometry-thickness'` | See field/choice declaration |
| `setup.py:406` | `DisplayCheckScreen` | Select | `'geometry-position-units'` | See field/choice declaration |
| `setup.py:409` | `DisplayCheckScreen` | Input | `'geometry-' + key` | See field/choice declaration |
| `setup.py:419` | `DisplayCheckScreen` | Input | `'geometry-measured'` | See field/choice declaration |
| `setup.py:420` | `DisplayCheckScreen` | Button | `'record-geometry-measurement'` | 'Record Measurement in Latest Diagnostic' |
| `setup.py:637` | `DataScreen` | Select | `'data-run'` | See field/choice declaration |
| `setup.py:640` | `DataScreen` | Button | `'inspect-manifest'` | 'Manifest' |
| `setup.py:641` | `DataScreen` | Button | `'inspect-trials'` | 'Trials' |
| `setup.py:642` | `DataScreen` | Button | `'inspect-adaptive'` | 'Staircase state' |
| `setup.py:644` | `DataScreen` | Button | `'inspect-scenario'` | 'Scenario report' |
| `setup.py:645` | `DataScreen` | Button | `'open-run-folder'` | 'Open run folder' |
| `setup.py:648` | `DataScreen` | Select | `'threshold-retention-mode'` | See field/choice declaration |
| `setup.py:653` | `DataScreen` | Input | `'threshold-fraction'` | See field/choice declaration |
| `setup.py:655` | `DataScreen` | Input | `'threshold-last-n'` | See field/choice declaration |
| `setup.py:657` | `DataScreen` | Select | `'threshold-column'` | See field/choice declaration |
| `setup.py:666` | `DataScreen` | Button | `'analyse-threshold'` | 'Generate Threshold Table + Plot' |
| `setup.py:669` | `DataScreen` | Button | `'preview-figures'` | 'Generate staircase + THC previews' |
| `setup.py:670` | `DataScreen` | Button | `'open-staircase-image'` | 'Open staircase image' |
| `setup.py:671` | `DataScreen` | Button | `'open-threshold-image'` | 'Open THC image' |
| `setup.py:843` | `HelpScreen` | Button | `'edit-contributions'` | 'Open researcher registration in editor' |
| `setup.py:844` | `HelpScreen` | Button | `'view-extension-guide'` | 'Open Extension Guide' |
| `setup.py:891` | `ExperimentConfigScreen` | Button | `'back'` | 'Back' |
| `setup.py:892` | `ExperimentConfigScreen` | Button | `'change-display'` | 'Change display / Calibrate' |
| `setup.py:893` | `ExperimentConfigScreen` | Button | `'review'` | 'Review' |
| `setup.py:925` | `ExperimentConfigScreen` | Select | `'config-preset'` | See field/choice declaration |
| `setup.py:926` | `ExperimentConfigScreen` | Button | `'load-preset'` | 'Load preset' |
| `setup.py:927` | `ExperimentConfigScreen` | Input | `'preset-name'` | See field/choice declaration |
| `setup.py:928` | `ExperimentConfigScreen` | Button | `'save-preset'` | 'Save new preset' |
| `setup.py:929` | `ExperimentConfigScreen` | Button | `'update-preset'` | 'Update selected preset' |
| `setup.py:980` | `ExperimentConfigScreen` | Select | `dynamic/generated` | See field/choice declaration |
| `setup.py:983` | `ExperimentConfigScreen` | Input | `widget_id` | See field/choice declaration |
| `setup.py:986` | `ExperimentConfigScreen` | Button | `'calculate-up'` | 'From down' |
| `setup.py:988` | `ExperimentConfigScreen` | Button | `'calculate-down'` | 'From up' |
| `setup.py:1161` | `ChangeDisplayScreen` | Button | `'display-cancel'` | 'Cancel' |
| `setup.py:1162` | `ChangeDisplayScreen` | Button | `'display-refresh'` | 'Refresh profiles' |
| `setup.py:1163` | `ChangeDisplayScreen` | Button | `'display-calibrate'` | 'Calibrate' |
| `setup.py:1164` | `ChangeDisplayScreen` | Button | `'display-apply'` | 'Apply display' |
| `setup.py:1168` | `ChangeDisplayScreen` | Select | `'display-choice'` | See field/choice declaration |
| `setup.py:1324` | `ReviewScreen` | Button | `'back'` | 'Back' |
| `setup.py:1325` | `ReviewScreen` | Button | `'run'` | 'Run human experiment' |
| `setup.py:1326` | `ReviewScreen` | Button | `'run-simulation'` | 'Run simulation' |
| `setup.py:1543` | `PsyCoLabSetupApp` | Button | `'exit'` | 'Exit' |
| `setup.py:1544` | `PsyCoLabSetupApp` | Button | `'configure'` | 'Configure Experiment' |
| `setup.py:1557` | `PsyCoLabSetupApp` | Input | `'data-root'` | See field/choice declaration |
| `setup.py:1563` | `PsyCoLabSetupApp` | Button | `'load-data-root'` | 'Load Data Workspace' |
| `setup.py:1567` | `PsyCoLabSetupApp` | Select | `'participant-select'` | See field/choice declaration |
| `setup.py:1569` | `PsyCoLabSetupApp` | Input | `'participant'` | See field/choice declaration |
| `setup.py:1581` | `PsyCoLabSetupApp` | Select | `'session-mode'` | See field/choice declaration |
| `setup.py:1592` | `PsyCoLabSetupApp` | Select | `'experiment'` | See field/choice declaration |
| `setup.py:1596` | `PsyCoLabSetupApp` | Select | `'monitor-profile'` | See field/choice declaration |
| `simulations.py:52` | `SimulationsScreen` | Select | `widget_id` | See field/choice declaration |
| `simulations.py:60` | `SimulationsScreen` | Input | `widget_id` | See field/choice declaration |
| `simulations.py:74` | `SimulationsScreen` | Button | `'sim-edit-adaptive'` | 'Adaptive algorithm' |
| `simulations.py:76` | `SimulationsScreen` | Button | `'sim-review'` | 'Review Simulation' |
| `simulations.py:92` | `SimulationsScreen` | Input | `'sim-data-root'` | See field/choice declaration |
| `simulations.py:94` | `SimulationsScreen` | Select | `'sim-experiment'` | See field/choice declaration |
| `simulations.py:106` | `SimulationsScreen` | Select | `'sim-profile'` | See field/choice declaration |
| `simulations.py:112` | `SimulationsScreen` | Select | `'sim-scenario'` | See field/choice declaration |
| `simulations.py:121` | `SimulationsScreen` | Input | `f'sim-seeds-{index}'` | See field/choice declaration |
| `simulations.py:166` | `SimulationsScreen` | Button | `f'sim-calculate-down-{index}'` | 'Calculate down from up' |
| `simulations.py:167` | `SimulationsScreen` | Button | `f'sim-calculate-up-{index}'` | 'Calculate up from down' |
| `simulations.py:181` | `SimulationsScreen` | Input | `f'sim-observer-{index}-{number}'` | See field/choice declaration |
| `simulations.py:412` | `AdaptiveAlgorithmScreen` | Button | `'adaptive-cancel'` | 'Cancel' |
| `simulations.py:413` | `AdaptiveAlgorithmScreen` | Button | `'adaptive-apply'` | 'Apply adaptive settings' |
| `simulations.py:432` | `AdaptiveAlgorithmScreen` | Select | `f'adaptive-value-{number}'` | See field/choice declaration |
| `simulations.py:440` | `AdaptiveAlgorithmScreen` | Input | `f'adaptive-value-{number}'` | See field/choice declaration |
| `simulations.py:450` | `AdaptiveAlgorithmScreen` | Button | `'adaptive-calculate-down'` | 'Calculate down from up' |
| `simulations.py:451` | `AdaptiveAlgorithmScreen` | Button | `'adaptive-calculate-up'` | 'Calculate up from down' |
| `simulations.py:540` | `SimulationReviewScreen` | Button | `'sim-back'` | 'Back' |
| `simulations.py:541` | `SimulationReviewScreen` | Button | `'sim-run'` | 'Run Virtual Experiment' |
| `unified_run.py:56` | `VirtualObserverOptionsScreen` | Button | `'virtual-back'` | 'Back' |
| `unified_run.py:57` | `VirtualObserverOptionsScreen` | Button | `'virtual-run'` | 'Run virtual experiment' |
| `unified_run.py:70` | `VirtualObserverOptionsScreen` | Select | `'virtual-scenario'` | See field/choice declaration |
| `unified_run.py:79` | `VirtualObserverOptionsScreen` | Input | `f'virtual-seeds-{i}'` | See field/choice declaration |
| `unified_run.py:84` | `VirtualObserverOptionsScreen` | Input | `f'virtual-observer-{i}-{j}'` | See field/choice declaration |

## Generated registered CSF fields

- `Max_monitor_Luminance` — Maximum monitor luminance (cd/mÂ²); configure ID `field-Max-monitor-Luminance`; scenario field ID follows registered field index.
- `Background_Luminance` — Background luminance (cd/mÂ²); configure ID `field-Background-Luminance`; scenario field ID follows registered field index.
- `Background_Screen_intensity` — Background digital screen intensity; configure ID `field-Background-Screen-intensity`; scenario field ID follows registered field index.
- `number_conditions` — Number of stimulus conditions; configure ID `field-number-conditions`; scenario field ID follows registered field index.
- `condition_unit` — Spatial-frequency units; configure ID `field-condition-unit`; scenario field ID follows registered field index.
- `condition_values` — Condition values (comma-separated, in selected units); configure ID `field-condition-values`; scenario field ID follows registered field index.
- `n_down` — Correct responses required for a downward step; configure ID `field-n-down`; scenario field ID follows registered field index.
- `n_up` — Incorrect responses required for an upward step; configure ID `field-n-up`; scenario field ID follows registered field index.
- `logUNIT_UP` — Up-step size (legacy log units); configure ID `field-logUNIT-UP`; scenario field ID follows registered field index.
- `logUNIT_DW` — Down-step size (legacy log units); configure ID `field-logUNIT-DW`; scenario field ID follows registered field index.
- `initial_one_down_limit` — Initial 1-down maximum accepted responses per staircase (0 = disabled); configure ID `field-initial-one-down-limit`; scenario field ID follows registered field index.
- `staircases_per_condition` — Independent staircases per condition; configure ID `field-staircases-per-condition`; scenario field ID follows registered field index.
- `reversal_termination` — Reversals required per staircase; configure ID `field-reversal-termination`; scenario field ID follows registered field index.
- `max_trials` — Maximum accepted responses (safety ceiling); configure ID `field-max-trials`; scenario field ID follows registered field index.
- `timeFixate` — Fixation duration (ms); configure ID `field-timeFixate`; scenario field ID follows registered field index.
- `timeInterval` — Interval duration (ms); configure ID `field-timeInterval`; scenario field ID follows registered field index.
- `timeAB` — Stimulus duration (ms); configure ID `field-timeAB`; scenario field ID follows registered field index.
- `timeT` — Response timeout (ms; 0 = self-paced legacy behaviour); configure ID `field-timeT`; scenario field ID follows registered field index.
- `starting_probe_intensity` — Starting probe digital intensity; configure ID `field-starting-probe-intensity`; scenario field ID follows registered field index.

Observer controls: threshold, preferred_condition, tuning_width_octaves, slope and lapse; seeds are separate. Condition units follow the configured experiment: canonical cpd for cpd/period modes, explicit historical units for legacy scenarios. No generic CSF observer is imposed on another experiment.
