# Researcher override for human acquisition

On **Review**, select **Collect participant data**, then **Researcher override…**.
Review the outstanding requirements, select the responsibility acknowledgement,
and press **Override and collect participant data**. Cancel or Escape returns to
Review without authorizing a run. The ordinary **Collect participant data**
button retains strict qualification checks.

This runs the selected experiment with its real display, keyboard responses,
trial count, adaptive rules and stopping criteria. Records use `data_kind: human`
and the existing participant/experiment/display/date/run hierarchy. The normal
run index, workspace settings, analysis and error/abort preservation apply.
There is no test response cap, synthetic observer, test directory, test marker,
override-specific folder suffix or participant-facing override banner.

The override can waive outstanding geometry, luminance and timing verification,
experiment/profile qualification, and protocol qualification. It does not mark
any calibration Verified, qualify an experiment, turn synthetic photometry into
measurements, or change stimulus/response mathematics. Existing scientific
metadata and legacy folder naming continue to describe the actual calibration.

## Checks that remain

- A valid human participant ID and a valid external human data workspace.
- Valid finite parameters, response keys and internally consistent profiles.
- The selected display binding, expected resolution, connected mode and actual
  framebuffer checks, with no silent monitor substitution.
- Stimulus geometry, sampling limits and digital command/range checks, including
  later adaptive draws. Invalid or undefined experiment configurations still fail.
- Current reviewed settings, selected stimulus snapshots and profile revision.
- Real accepted responses, normal completion rules and preservation on abort/error.

The same decision reaches Review, final runner preflight and procedure
initialization. Archived procedures use this boundary too; their missing or
invalid configuration checks remain. Future requirement types are blocking by
default until explicitly classified as overridable.

## Provenance and reuse

`manifest.json` contains a `researcher_override` record with the UTC confirmation
time, acknowledgement, waived requirement keys and details, and a hash binding
the decision to the normalized request, stimulus snapshots, exact display
profile and outstanding requirements. The original profile and its verification
flags remain in `monitor_profile.json` and the manifest. The decision is also
included in the run's request snapshot. Early configuration failures retain it
in the minimal manifest whenever a run has been allocated.

Changing the reviewed participant, values, stimuli, profile or outstanding
requirements invalidates the decision. The confirmation reloads current settings
and checks the connected display; the runner repeats validation. Loading saved
settings never restores override authorization: each interactive launch needs
a fresh decision. Overrides are rejected for simulation and presentation tests.

Python callers can make the same explicit decision with
`authorize_researcher_override(request, spec, profile, acknowledged=True)` from
`psychophysics_lab.config.researcher_override`, then pass the returned request to
`run_request`. A boolean request flag does not bypass validation. This is an
auditable researcher choice, not an authentication or tamper-proof signature.

## Regression evidence

`tests/test_researcher_override.py` exercises strict defaults, acknowledgement and
cancel, stale review rejection, reserved identities, retained configuration and
hardware checks, ordinary human storage, protocol initialization, and accepted
response preservation on completion, abort and error. Display/input fixtures
exercise the human branch without acquiring participant data or claiming physical
hardware certification. The existing display, response and scientific parity
tests continue to apply.
