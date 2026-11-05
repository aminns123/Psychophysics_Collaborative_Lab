# Exact pre-audit primary-analysis source

`primary.py` is copied from develop
`fcaff4d1139e85e7fc090d16c322c13958bf7a08` at
`src/psychophysics_lab/analysis/primary.py`, without numerical or reporting edits.
LF-normalized SHA256:
`eed030450388e00f4769e9022451d7ee9a0b7d8b80fd38399788cc420f9f6467`.

It is historical evidence outside the runtime package, not an active module.
The original frozen authoring fixture retains its existing digest. The source
guard checks this archive against that digest, then compares every live
top-level definition except the deliberately corrected derived-report writer
against this original AST. Estimation, canonical-run reads and acquisition
results must remain identical. New regression tests check the repaired writer's
origin labels, quality flags, input hashes and unchanged source records.
