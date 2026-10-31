# Reviewed student/startup and researcher-experience integration candidate

Base develop: 649b7058cc6692e476cac4121ab847cb4ebf1759. Main remains 179d32f.

Exact reviewed heads retained as ancestors through ordinary merge commits:

| PR | Accepted head |
|---|---|
| 181 | 7487d0893286b39c67adbb2cf57dc8d4470c17b2 |
| 182 | cf569a60b1d949498e10cfbe5962e52e16727948 |
| 183 | 31ba81bedf285d32832d4e0c8e7c4567969fe673 |
| 184 | ab040b007c2fffe7552e0f53a88329212003b8bf |

The P2 follow-up ca71c649b37ddc03759b7b123390dd77d412f622 is a direct child
of the student's unchanged head. The student's fork is not rewritten or pushed.
Its review-only PR uses an exact owned mirror of that head to show only the
correction. It is included in this candidate, not separately merged to a protected
branch. README, ui/setup.py, ui/console.py and the scientific source guard merged
automatically; both overlapping contributions were inspected and retained.

## Intended protected-branch sequence

1. Review #181 and its narrowly scoped P2 follow-up, together with #182–#184.
2. Review this cumulative PR into develop, with its own full final Windows and
   portability evidence. Prefer one merge commit for this candidate; do not also
   merge each original PR independently. The original commits/reviews remain
   linked, and their heads are ancestors of the candidate.
3. Only after maintainer approval, merge the candidate into develop. Then verify
   the resulting develop push CI. Earlier PRs can be closed as included only after
   confirming ancestry; no automatic administrative closure is performed here.
4. Prepare/review develop → main, test that exact PR and require explicit approval
   for that second protected promotion. No tag, release or installation update.

## Acceptance scope

Final-source qualification includes complete Windows regression, portability,
frozen scientific equivalence, both contrast methods, independent project/external
experiments/custom stimuli, generic Configure/Review and A1/A2/B onboarding,
startup/recovery/native-host harness, saved-run readers, calibration/readiness and
researcher-override regressions. Results and exact CI links accompany the PR.

The P2 evidence is additive manifest software metadata, outside the twenty trial
columns. Unknown/direct launches do not acquire inferred qualification. The
development route remains usable for legitimate testing/pilots under the existing
readiness/calibration/override rules. No participant-frame status or extra response
guidance is added. Old records without environment evidence remain unknown/readable.

The student's reported successful Windows adaptive/fixed acquisition is an
important retained acceptance case. Their exact earlier interpreter/launcher and
raw data are unavailable: software regressions cannot verify that particular
computer or retrospectively certify its environment. Native independent researcher,
student-account and apparatus qualification remain separate and unverified here.
No qualified installation, participant/calibration data or local laboratory code
is modified. This candidate is not itself a software release.
