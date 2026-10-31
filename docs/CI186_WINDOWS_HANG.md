# Post-#186 Windows launcher CI investigation

## Frozen source and observed failure

Merged develop `8f493fa0a54cbe57109943120b5e410e77c0541a` and successful
PR #186 head `fdb61410f62daffa08af7a424445d6eb1c28277c` have identical Git
trees. No scientific difference should be inferred from the commit identities.

Successful workflow 41149788861 passed 2,612 tests / one skip and portability in
41m05s. Both cancelled attempts of develop workflow 41156599166 stop after
17/18 items in `test_researcher_architecture.py`. Its final case is
`test_windows_launcher_forwards_cli_arguments_and_preserves_spaces[True]`.
Diagnostic run 41170327563 then confirmed this exact live test and its first
`cmd /d /c call run_psycolab.bat ...` command, rather than a teardown or an
earlier architecture test. It was bounded at 90 seconds instead of hours.
Cancellation cleanup in both attempts reports orphaned conhost, cmd and
PowerShell processes.

Both successful and stalled CI used runner image `windows-2025-vs2026`
`20261021.278.1`, runner 2.338.2, CPython 3.11.9 and the same locked dependencies.
The local Windows 11 diagnostics use the existing disposable CPython 3.11.15
development environment; this difference is recorded, not treated as independent
hosted-runner equivalence.

## Executed diagnostic evidence

| Bounded exercise | Result |
|---|---|
| Original architecture file alone | 18 passed, 20.06s |
| Immediate predecessor plus original architecture file | 22 passed, 10.38s |
| Exact development launcher case alone | 1 passed, 14.48s |
| Earlier launcher/setup/environment tests, predecessor and architecture | 86 passed, 45.10s |
| Inherited-output fault reproduction on Windows | 0.25s requested deadline returned after 6.17s; faulthandler captured blocked reader threads and timeout-cleanup join |
| Proposed process-owner correction with preceding tests | 89 passed, 48.91s |
| Same real launcher with forced occupied legacy bootstrap path, before fix | FAIL: same native bootstrap fallback; no app launch |
| Atomic allocator, original batch/Restricted-PowerShell and cleanup checks | PASS; final exact-head CI result recorded in PR |

No immediate preceding-file dependency has been reproduced. Identical source
trees do not freeze OS temporary-name/console lifetimes. There is no evidence
of a dependency-version change.

## Root cause and why the PR could pass

The batch bootstrap used `%TEMP%\\PsyCoLab-launch-%RANDOM%-%RANDOM%.exe`, left
successful executables behind, and treated an occupied name as bootstrap failure.
Two RANDOM draws are not a uniqueness guarantee across fresh cmd processes;
an inherited `RANDOM` variable can make them constant.

At 05:13:47 UTC the hosted development command began; at 05:15:17 the diagnostic
watchdog ended pytest. The process snapshot showed PowerShell waiting in the
bootstrap fallback's `System.Windows.Forms.MessageBox.Show`. Only the two empty
bootstrap compiler logs from the successful locked launches existed; no third
compilation log had been created. In the original batch control flow, this is
the occupied-executable branch before compilation. The headless test was waiting
for a human to dismiss that modal. The same occupied-path branch was reproduced
deterministically with `RANDOM=17` and a private retained-file sentinel.

The passing PR used distinct available names; the failing runs reached the
collision branch. Their identical Git tree therefore does not make these
process/temp-directory outcomes identical. The immediate preceding tests were
innocent in the bounded local exercises; retained shared temporary executables
were the relevant external state.

The production correction is limited to `scripts/windows_startup.cmd`: atomically
claim a new private directory with `mkdir`, retry occupied candidates with a
bounded counter, compile only inside the claimed directory, and on a successful
exit remove only its own named files and empty directory. Existing candidates
are never reused, overwritten or deleted. Genuine compiler/bootstrap failures
still open the same recovery interface and retain their diagnostic files.

## Verified timeout-cleanup defect and narrow candidate

The original test calls `subprocess.run(..., capture_output=True, timeout=45)`.
On Windows CPython, `run()` handles a timeout by killing only the direct process
and calling **unbounded** `communicate()` again to drain output. A descendant
retaining an inherited write handle can keep reader threads alive indefinitely.
Consequently the apparent 45-second limit does not bound that test's cleanup.
This mechanism was reproduced separately with self-expiring child processes;
it does not itself prove what delayed the original hosted command.

The accompanying test-only `_windows_launcher_process.py`:

- Uses file-backed output, retaining stdout/stderr and nonzero failure assertions.
- Starts a gated worker, assigns it to a private Windows kill-on-close job, then
  permits it to launch the command. No descendant can race job assignment.
- Gives test commands closed input and retains the 45-second command deadline.
- Owns only the fixture's worker/descendants, closing that job on success, failure
  or timeout. It never enumerates/kills arbitrary machine applications.
- Also bounds the temporary-interpreter query. It neither changes production
  launch/recovery nor approves qualification or suppresses a failed command.

New fault regressions exercise an exited launcher whose child retains output,
a live hung launcher, descendant termination, partial diagnostics, nonzero exits
and released fixture file handles. A simultaneous two-launch regression forces
the same RANDOM values and an occupied candidate, proves two distinct claimed
directories, and checks successful cleanup without touching the existing file.
The real batch/Restricted-PowerShell raw-arg checks now force legacy/candidate
collisions too; qualification-record preservation assertions remain unchanged.

## Hosted evidence and acceptance

The first diagnostic commit used verbose per-test logging, faulthandler and
launcher stage logs. Its temporary hard watchdog prevented another hour-long
wait; the hosted process snapshot and bootstrap logs established the modal
branch. The Python reader-thread timeout mechanism was captured separately in
the local fault reproduction. The final correction removes the hard diagnostic
exit, retains ordinary faulthandler/verbose CI observability, and uses true
process-tree ownership to bound failed launcher commands. No timeout is increased.
Final hosted Windows/portability evidence is recorded in the PR.

Application/scientific source, locked profiles, installations, environment roles,
acquisition/calibration protections and participant data are outside this change.
Complete Windows CI and portability must pass before maintainer approval.
