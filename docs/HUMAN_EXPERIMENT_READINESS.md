# Preparing an experiment for human acquisition

> **Historical implementation audit:** this document includes baseline counts, prior PR/branch commands and past calibration/contrast descriptions. It is not a current qualification of any monitor or experimental protocol. For the current Windows software baseline and outstanding release requirements, consult [Windows release acceptance](WINDOWS_RELEASE_ACCEPTANCE_AND_STRESS_TEST_PLAN.md) and the [human experiment readiness checklist](HUMAN_EXPERIMENT_READINESS_CHECKLIST.md). Never copy historical monitor values into a new profile without measurement.

Open **Experiment → Configure Experiment → Review**. The **Human Experiment Readiness** panel shows the selected experiment and display requirements, their status, and a direct action for each. Human acquisition and simulation have separate statuses. Required failures block human acquisition; recommended setup records do not become physical certificates. Expand **Technical preflight details** for the full error.

## What the statuses mean

| Layer | What it records | What it does not establish |
|---|---|---|
| Calibration setup | Display, Geometry, Spatial, Luminance, Timing and Review workflow records | Independent physical verification |
| Saved evidence | Ruler observations, intensity/luminance pairs and compatible software reports | That every observation is genuine or meets laboratory tolerances |
| Physical verification | Explicit researcher declarations backed by independent measurements | Automatic certification by PsyCoLab |
| Experiment qualification | Explicit laboratory review for a registered experiment on a saved display | Permission to bypass current parameter or connected-display validation |
| Human readiness | Current configuration and experiment-specific preflight requirements | A guarantee that later adaptive commands or changed hardware will be safe |
| Simulation availability | Valid numerical configuration and a registered virtual observer | A measurement of the physical display |

Green calibration pages can coexist with unverified photometry and blocked human acquisition. Synthetic method labels such as `fake_photometer` remain test data. They must be replaced by genuine observations before physical photometry verification; changing a label is not evidence. Optional notes and dates do not prevent saving measurements. Declaring photometry Verified requires an actual instrument/method and deliberate acknowledgement of independent laboratory review.

## Chronological laboratory walkthrough

1. On **Calibrate → Display**, save a local display bound to the actual connected monitor and its expected pixel resolution. OS pixel mode and refresh reports cannot establish research-grade active dimensions or viewing distance.
2. Measure active width, height and eye distance. Record the compatible ruler observation on **Geometry**. Save and inspect **Spatial** and **Timing** software diagnostics as appropriate; these do not establish emitted luminance or photon timing.
3. On **Luminance**, enter genuine photometer observations and save their mapping. Optional metadata may be added later. Keep the instrument evidence under laboratory control.
4. Finish **Calibrate → Review** and open the experiment. Inspect the Human Experiment Readiness panel. Use **Review physical photometry/geometry/timing** for the focused declaration page. It shows the current declarations, saved pairs or diagnostic reports, and whether the selected experiment requires that evidence. Missing ruler observations and synthetic photometry instead lead directly to the relevant measurement stage.
5. Review independent ruler, photometer and photodiode (or equivalent) measurements against the laboratory's acceptance criteria. Change only justified declarations and acknowledge that review. Saving returns to the same Experiment Review, which reloads the profile and refreshes readiness.
6. Use **Edit contrast settings** to go directly to the relevant parameter. Live limits update when the background or starting intensity changes. Choose **Review** to apply validated values and return to the existing Review; returning to the original settings page also shows the applied values.
7. Use **Check experiment requirements**. The registered experiment and selected display are already chosen. Review the checks, explicitly acknowledge laboratory review, then qualify. Failed verification or an unsafe current CSF contrast prevents qualification. Saving returns to Review immediately.
8. If human acquisition is Ready, choose **Run human experiment**. Final preflight reloads the exact profile and still checks current parameters, qualification, spatial sampling and the actual connected display. Human participant identity is required. Choose **Run simulation** independently when available; its virtual observer and isolated synthetic output rules remain unchanged.

Direct calibration actions return to the same Review. Fullscreen diagnostics close and restart the TUI; their return restores the calibration page above the reviewed experiment, with **Return to Experiment Review**. The exact draft is retained locally. Verification-only revisions refresh after an explicit return if the physical arrangement is unchanged and configuration validation succeeds. Changed physical dimensions, eye distance, binding, resolution or refresh retain the stale-review guard: review the current configuration again. Ordinary application restarts retain the saved parameter draft; no acquisition starts automatically.

## Contrast limits and adaptive policy

The current CSF command convention remains `C_disp = (I_start - I_b) / (1 - I_b)`. The production `box=False` shader has conservative bounds `RGB = I_b ± C_disp / 2`, so `C_disp ≤ 2 min(I_b, 1 - I_b)`. The inverse existing convention gives the maximum starting intensity. At background 0.25, the maximum contrast is 0.5 and maximum starting intensity is 0.625; at background 0.5, the maximum starting intensity is 1.

The live message also reports whether the next upward step can exceed the limit. The legacy update multiplies contrast by `10 ** logUNIT_UP`; repeated upward steps can eventually exceed the range even when the first step is safe. Each human draw checks its planned contrast **before OpenGL**. An unsafe command raises an error and stops acquisition; accepted records are retained and the run records an error. There is no silent clamping or change to reversal rules. Synthetic numerical staircases remain unconstrained for diagnosis. A successful simulation cannot prove a human stimulus will stay within the display range.

The starting-intensity default, contrast convention, adaptive rules and shader are unchanged. A different ceiling, termination rule or scientific contrast definition needs an explicit protocol decision and separate validation. Qualification remains a saved display/registered-experiment declaration, not a permanent certificate for every parameter set: current settings are checked during qualification when a draft is available and again at each launch. Material physical profile changes invalidate existing declarations using the established persistence rules. The historical reference-profile compatibility policy is preserved and described as compatibility, not newly measured physical verification.

## Implementation and review audit

The confusing workflow came from presenting saved calibration records beside unrelated human blockers, directing qualification through a general editor, repeating full launch errors, and retaining old profile hashes after legitimate verification. The panel now uses the same structured `human_requirements` that produces authoritative human blockers; configuration and simulation use the existing `validate_setup` boundary. Contrast limits use the existing forward/inverse command helpers and production range guard, rather than a competing luminance or contrast formula.

Changed implementation: `config/human_readiness.py`, `config/preflight.py`, `stimuli/contrast_validation.py`, and the setup, calibration guide and focused verification/qualification screens. No raw participant records, actual local calibration files, defaults, shader code or adaptive update code are edited.

The added software regressions cover completed-but-unverified setup, five fake readings, qualification refusal and success, verification/hash refresh, dynamic bounds for five backgrounds, invalid numeric inputs, current unsafe qualification, later adaptive rejection before OpenGL, direct calibration returns, restart restoration, original-form synchronization, synthetic options, physical-change staleness and final connected-display checks. Existing no-op saving, canonical pipeline, recovery and synthetic-isolation tests remain in the full suite. All fixtures live in isolated test configuration/data roots. Mocked declarations do not establish real display calibration.

For local review, compare `main...feature/human-experiment-readiness`. Reproduce the checks from the repository:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/portability_check.py
.venv\Scripts\python.exe -m pip check
git diff --check main...feature/human-experiment-readiness
```

Baseline: 606 Windows tests passed before changes. Final validation and Windows/Linux Actions results are recorded in the pull request. The PR is for manual review; nothing merges automatically. After approval and passing checks, merge through GitHub or use `git switch main` followed by `git merge --ff-only feature/human-experiment-readiness` if main has not advanced and the working tree is clean; otherwise review and reconcile changes first.

Remaining laboratory validation: connected monitor selection and fullscreen framebuffer, measured geometry and viewing arrangement, actual photometer response and provenance, independent photon timing, shader presentation on the intended GPU/display, and protocol-specific acceptance tolerances. Software tests validate workflow and rejection logic, not those instruments or biological performance.
