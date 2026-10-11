# COMPLETE01 immutable RUN acceptance tests

Test-only source base: `a189deb04827ceae17107415144731ea07a796c8`.
Frozen input: adopted COMPLETE01-SCOPE and its final SWE dispositions. Only the
new test module and this plan are owned; no RUN/TSK implementation or canonical
records change. Different native Sol reviews the later implementation.

`SyntheticOwners` exposes the public TSK/MEM/ART/VER methods consumed by MockRunner.
It is explicitly a protocol fixture, not production persistence or connected
MEM/TSK/ART/VER evidence. Its only SQLite connection is `:memory:`; no files,
subprocesses, sockets, provider or external calls occur in the tests.

The16 methods freeze:

- Invalid VER-without-ART host configuration and unchanged default draft-only run.
- Compose -> canonical whole-set C09 -> canonical C10, completed response with
  verification/finished diagnostics, no release and no extra inference/reservation.
- Unknown/unmet continues the finite next-step loop and remains visible locally.
- Identical bounded verification retries followed by yield or retained occupancy;
  persistent ambiguous completion retains without release and reenters before
  inference. Committed/lost completion response replays without reopening work.
- Retained finished compose tail finalizes only after call/Step readiness; started
  Step, existing next call, readiness failure, non-compose or non-tail history does
  not authorize entry finalization. Ordering asserts readiness before verification,
  not a private implementation method layout.
- Latest pause/cancel/source-authority denial is fenced by the subsequent execution
  context/release boundary; malformed VER receipt fails without inference repair.
- Verification Ref never enters model context or Step.result_refs; no verify Step
  is fabricated.

AST validation and `git diff --check` pass. Isolated command:

```
/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_mock_completion_v5.py -v
```

Author RED:16 tests,0.002s,exit1; existing default draft-only test PASS and15 new
path errors all report missing `MockRunner(..., verifications=...)` support.
Log: `/private/tmp/pal-complete-run-tests-red.log`. No skip/fake implementation is
used. Test body behavior beyond that constructor is NOT_RUN until the RUN owner
implements the adopted seam. The test explicitly inserts its repository root for
isolated discovery. Scope/connections/new milestone acceptance are not inferred
from syntax, RED reproduction or protocol doubles.

Root separately owns real SQLite owner integration, control/source-stop ordering,
completion event/lease/history safety and final full regression. These tests do
not claim completion of the project or replace independent implementation review.
