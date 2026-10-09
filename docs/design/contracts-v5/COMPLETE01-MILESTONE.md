# C076 — verified local completion with retained history

Exact source: bdce832b8fdb68f6317c033155474a4204703189. Full711 host tests PASS,
24.789 seconds, exit0. See evidence/operations/complete01-20261009/verification.json.
The full log is retained separately; a reviewer not supplied that log relies on
the source-bound host receipt. These are temporary SQLite/loopback tests, not CI,
real-model usefulness, product activation or production operation.

The local path now connects actual MEM -> TSK -> mock RUN -> ART -> VER -> C10 ->
C14. Only current saved structural all-MET evidence can complete the exact work.
Unknown semantic/source-fetch checks cannot complete. Completion preserves epoch
and budgets, closes occupancy and emits one replayable result. Later source stop
keeps historical completion while denying future evidence/body reuse. Running
dependents invalidate in the same transaction; completed history gets a scoped
notice. No release can reopen completed/cancelled/failed work.

Native Astra authored TSK completion/history/terminal safety; separate native Sol
approved a48d0cf3 with46 tests after correcting stored-call identity/index defects.
Another native Sol froze16 RUN acceptance tests before code. Exact CO SWE-2 High
task39213ad4 authored RUN and passed that declared verifier. Root then connected
actual owners, found the C02 request mismatch and preserved all first failures.
Independent Sol also found unknown VER error terminalization. Root fixed both and
strict receipt handling plus retained diagnostics. Independent Sol approves final
bdce832 with30 RUN tests and independent probes. No self-report alone closes this.

New61 methods distinguish evidence classes:

- TSK22 use explicit readonly VER/ART doubles to probe authority, current saved
  identities, event/replay/lease atomicity, source history and terminal release.
- Immutable RUN16 use synthetic public owners and initially missed C02 shape;
  they remain unchanged, not retroactively relabelled as real integration.
- Actual TSK9 use temporary-file MEM/TSK/ART/VER plus public C14. They cover one
  completion, reopen/replay/next claim, unknown checks, both selected/unselected
  dependencies, shared stopped source across completed/running Goals, two-connection
  ordering, stale epoch/set, corrupt VER and failure/interrupt after each actual
  state/lease/flag/event/replay write.
- Actual RUN8 exercise one-call compose/verify/complete, bounded non-MET progress,
  committed/lost and uncommitted/ambiguous response boundaries, same-host reentry,
  new-epoch verification without another model call, latest controls and malformed
  completion receipts. Fault wrappers alter response delivery around actual owners.
- Strict RUN6 reject malformed checks/current sets, boolean WorkRefs and unknown
  owner outcomes; same-lease reentry retains saved diagnostics.

Corrections did not loosen Conditions or budgets. Generic persistence uncertainty
is unavailable and cannot manufacture user-work failure or a new inference permit.
Trusted Python collaborators are not a sandbox: a hostile callback COMMIT cannot
be undone. General new-runner restart adoption and remote cessation remain excluded.

Next dependency candidate for design assessment: C11 user-view/read support for
saved verification and a small consumer connecting C14 references to owned bodies.
Current VER exposes typed get_verification/inspect but no C11 display body. Do not
build an abstraction without a concrete consumer. The precise smallest next scope
is under analysis; Opus should evaluate it alongside this milestone before adoption.
PRI/provider/UI, real semantics/source fetching, questions/change, source summaries,
general recovery, complete v5 activation and actual usefulness remain unfinished.
No original unknown CO/AGY call, stopped schedule, live DB, auth, paid fallback or
publication is activated by this candidate. A green checkpoint leads to the next
unfinished authorized dependency, not another routine owner-approval question.

Outcome: exact CO claude/claude-opus-5-5 taskd2abb079 is ALIGNED for C076, no
current-scope blocker. Root compared every supplied snapshot file to07c0c07 and
current code/test bytes tobdce832. tasks_v5.py is byte-identical to the independently
reviewed a48d0cf3. C076 local slice is MET; no product gate is promoted.

READ01 separately received REFINE, adopted as design clarifications: an injectable
guarded read clock with per-kind observation semantics, stable dumps/UTF-8 projection
and public ART hash/bytes, not-current wording, real paginated C14 consumer with
independent TSK state, and explicit tests. Exact implementation scope awaits SWE
consultation. Keep Opus's nonblocking recognized-VER-authority-disagreement note
for the next RUN edit; this milestone does not claim arbitrary owners cannot fail.
