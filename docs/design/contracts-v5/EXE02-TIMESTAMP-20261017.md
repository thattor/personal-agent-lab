# EXE02 timestamp correction — candidate, not adopted

This is a defect correction within the existing second-resolution UTC format,
not a new operation authority, design decision record or provider qualification.
Current STATE.md / DECISIONS.md and the latest direct owner instruction govern.

## Reproduced defect and correction

The issue version decoder and host observation-clock gate used independent
regular expressions with Unicode `\d` and day range 01..31. Both admitted
non-ASCII digits, year zero, impossible month/day combinations and non-leap
February 29. Consequently a synthetic read could succeed with an invalid
provider version or observation timestamp.

Both gates now use one pure, bounded ASCII/calendar validator. Valid wire
values and canonical body bytes are unchanged. Offsets, fractional seconds,
leap seconds and normalization remain unsupported. Calendar validity alone
proves neither freshness nor a trusted clock.

Seven frozen regression methods exercise the two public boundaries, including
real inert-child reads, owned exit, failed outcomes without body or provenance,
and valid issue/file version preservation. Current local RED21 becomes GREEN;
the previous 25 decoder tests and three mock demos also pass. All 106 previous
test files remain byte-identical. Local full verification timed out and exposed
an import-hygiene failure also reproduced on the unchanged baseline; it is NOT
a full PASS. Exact source and result hashes are in
`evidence/operations/exe02-timestamps-20261017/verification.json`.

Independent Claude/SWE-2 review has not run. Previous C110 review applies only
to its original source, not automatically to this changed source. Hosted full
regression and independent source review are separate requirements. Do not
adopt into PR19, merge main, qualify providers or declare PAL complete from
these self-checks.

## Continuation and owner constraints (2026-10-17)

The owner requests chat-controlled closed-loop development. Codex is prohibited
even when credits remain; any proposed use requires the owner's specific
approval first. Use only existing approved Claude/SWE-2/AGY routes with verified
no-extra-cost conditions. Do not enable billing, paid fallback, new services or
authentication. Source-only candidate work is not an independent model review.

Next: verify the exact hosted CI source; obtain independent review when the
existing route is available; reconcile the original isolated EXE01 ledger before
any adoption. Do not overwrite unseen local work, retry old UNKNOWN calls or
relax functional/permission/termination evidence to obtain PASS.
