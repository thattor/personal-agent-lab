# C075 — saved verification is connected, completion remains separate

Exact implementation source: fab7c77bb4e8ece6b094e7b96c9f7194c04e3d53.
Root full regression: 650 tests PASS, 24.227 seconds, exit0, authorized temporary
SQLite/loopback host tests. This is not CI, real model or product acceptance.
Receipt: evidence/operations/ver01-20261009/verification.json. Full log exists at
full-integrated.log; if not supplied to a reviewer, it is receipt-supported only.

Value: saved draft existence/integrity is checked against immutable host Conditions
and the exact current artifact set, then persisted as a typed historical receipt.
Consumers distinguish an old MET receipt from currently valid evidence. Saving or
verifying does not set a Goal completed. Semantic/source_fetched remain unknown.

CO taskf9f8dd69c40f4ebca78d294deaa5f640, exact devin/swe-2-high Free, authored
the isolated VER module and implementation note. Native Sol wrote the immutable16
public acceptance tests beforehand; CO passed them. Root added real-owner connection
and strict corrupt-state probes. Independent native Sol reviewed exact source;
Root fixed the reproduced findings; rereview APPROVE with45 tests independently run.
Native Astra independently approves Root's readonly TSK context with8 tests.

Evidence classes:

- 16 immutable VER component methods use explicit in-memory owner doubles.
- 8 actual TSK methods check snapshot/authority and stored corruption boundaries.
- 9 strict VER integrity methods use owner doubles and scoped storage corruption;
  initial20 failing subcases are retained, then corrected. These are contract and
  transaction probes, not hostile-callback sandbox guarantees.
- 12 actual temporary-file MEM/TSK/ART/VER connection methods cover saved compose,
  exact set, current Conditions, no extra budgets/completion, reopen, older ART
  epoch with new verification, replay after invalidation, selected/unselected source
  stop, legitimate set append, unchanged pause, missing/corrupt owner evidence,
  two-connection write ordering, after-INSERT failures/interrupts and caller writes.
- The Expert remains an in-process mock callable. No MOD, EXE or real model executes.

The integration corrections distinguish source/epoch/append invalidation from
corrupted fixed context, compare the full immutable ART WorkRef, reject empty fixed
Conditions/dependencies and guard ID minting before VER writes. The original CO
result and successful16-test verifier are preserved without relabelling them as
the final corrected source or whole product verification.

Next dependency: COMPLETE01-SCOPE freezes C10 complete together with completed
source-stop history and terminal-safe lease handling, following Opus72fabf04 and
SWEd8bd21a2 consultations. TSK and RUN have separate file ownership; actual consumer
integration remains Root-owned. No completion activation before all safety pieces
pass together. A milestone opinion is not extra owner approval or permission to
enable semantic models, service/UI/providers, schedules, new auth or paid fallback.

Still unmet: completed Goals, model-verifier budgets, real source fetching,
artifact re-input, general recovery, PRI/provider/UI, full v5 activation and actual
personal usefulness. Earlier unknown CO/AGY calls remain untouched and unadopted.

Exact CO Opus5.5 task0e78d5da returned ALIGNED without current-scope blockers.
Review note structure was verified by CO; no commands were run by the reviewer.
Root compared supplied implementation/test bytes to git fab7c77. The full log,
original component fixture and TSK context tests were receipt-supported, not
review-read. Earlier Astra review remains exact to3f37f78; Sol covers fab7c77.

Diagnostic precedence is deliberate: a known stale epoch, legitimate append or
denied source proves non-validity without inspecting all later evidence. Concurrent
corruption may therefore be masked by invalidated; neither outcome grants validity
or completion. This does not claim all causes have been diagnosed.
