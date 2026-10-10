# PRI01 host independent review — preliminary draft findings

Reviewer is independent of PrimaryHost source (previously authored its TSK
prerequisite). Review base `19e5f6e1f5ff4cd12de1ab6fc1035aa63866fac0`; normative
PRI01-SCOPE and D048. Draft reviewed SHA256:
`4e6c01d03c720e68e34d4cb0f75137970be1e2468b8badc5565e643980755eab`.
No final candidate approval is given. Root is modifying the draft. No source,
fixed tests, shared contracts, canonical records or external systems were changed.

## Reproduced blockers on the original draft

1. **Source stop before admission still permits disclosure.** `run_turn` checks
   sources before reserve/consume, but its admission transaction does not recheck
   them. With actual temporary HOST/MEM/TSK owners, wrap the public tasks.consume:
   call the original method, then stop this turn's record through MEM, then return
   its original successful receipt. Running the turn invokes the callback once
   with the stopped body. Later failed adoption cannot undo that disclosure.
   Root's correction must check the full exposure set in admission's short
   transaction, with fingerprint checked immediately before it; any known refusal
   before actual callback entry must not fabricate a returned/raised call.

2. **Malformed saved error is echoed by get_turn.** `_view` (draft lines305–320)
   checks outer status/refs/reply but leaves error arbitrary. Create a successful
   none turn, change only stored outcome.error to a value with an extra key and
   private canary message, then get_turn. The result succeeds and includes the
   canary. Closed bounded error validation and durable outcome binding are needed;
   raw stored diagnostics must not be returned as authoritative public errors.

Both probes used Python3.13 -E -s -B, the existing fixed fixture's actual owners,
and fresh temporary files. Source hash before and after both probes was the draft
hash above. Outputs were limited to callback count, result status and canary
presence; no private message was printed. Findings were sent to Root before source
freeze. These are independent reproduction results, not source approval.

## Root planned repairs, not yet verified

Root confirmed admission/exposure checks, known not_entered ending, turn/call ID
and nonce/snapshot/intent binding, bounded malformed UTF8 handling, outcome hash
and closed fixed errors, one-transaction history gates and savepoint ownership
markers. Read/write transaction violations must fail unavailable and not commit
reply suppression as a substitute for rollback. These remain pending exact-source
rereview; proposed or author-reported repairs are not counted as passed.

## Existing alignment and limits

The draft uses public owner APIs rather than private MEM/TSK/ART/VER SQL;
constructor connection/guard identity checks are wiring only. Candidate exposure
closure includes every actual C11 body and all visible-candidate dependencies;
withheld metadata does not become selectable body authority. Primary is a bounded
in-process mock, never a subprocess/provider. Startup receipt lookup does not
re-dispatch effects; the final review must check durable binding and absence/error
handling against actual candidate bytes. Host permits protect lifetime and are
not invocation mutexes; durable CAS plus live ownership must prevent duplicate
entry. Wrong-but-listed model targets remain an explicitly accepted semantic risk.

Final acceptance will bind an exact candidate commit/hash and rerun meaningful
fixed and independent cases. Root owns process/whole mock integration and full
regression. This review does not establish a real-provider profile, authentic
usefulness, external service activation or complete product acceptance.

## Exact candidate review — REQUEST_CHANGES

Candidate `f7bac929cb4bec57205e8a6163106f3b7b058f82`, source SHA256
`d54f9e741b036acb334169b88e7481f1caf44e61239fec9299ca80dc947b2678`.
Reviewed in a separate detached checkout. Fixed39 PASS0.438s and binding8
PASS0.145s under Python3.13 -E -s -B. Original two independent cases are now PASS:
stop after actual consume causes zero callback entries; malformed saved error
returns unavailable without echoing the canary. Local logs:
`/private/tmp/pri-host-astra-fixed-review.log`,
`/private/tmp/pri-host-astra-binding-review.log`,
`/private/tmp/pri-host-astra-independent-probes.log`.

A blocking persisted phase/intent inconsistency remains. `_turn` validates that
applying requires intent, but does not validate the converse. An actual new_work
owner commit followed by response loss leaves applying with a valid saved intent.
Changing only turn.phase to returned (also pending/preparing/admitted) leaves its
intent/call hashes valid. Startup recovery then records interrupted, despite the
existing committed Goal, instead of holding the contradictory durable state.
This is not coordinated evidence forgery: only one phase column changes.

Independent fixed regression `tests/test_primary_phase_review_v5.py` creates this
real-owner commit gap, changes only phase, reopens the real managed host and
requires held/zero writes/no lookup/no new charge/no callback, retaining the Goal.
Original candidate: 1 method / 4 cases RED, 4 failures, 0.056s; evidence in
`/private/tmp/pri-host-astra-phase-red.log`. Tests do not modify production source.
Root acknowledged the finding and owns a minimal phase/intent/call consistency
repair; no repaired candidate has yet been reviewed here.

Process5 and whole-suite results are Root evidence, not this review's independent
runs. Final approval remains withheld pending an exact corrected candidate and
unchanged probe rerun. No provider/service/live-data operation was performed.

## Corrected candidate 39f08ce — REQUEST_CHANGES

Exact commit `39f08cee6bd835981604328066d9e5b6d23a2fc1`, source SHA256
`44dfbca17fdffd95df8c840a4da076622a44f0e7e0512aef4ea3bc3e1ddcdf86`.
Independent fixed39 PASS0.426s, binding8 PASS0.237s and phase1/4cases PASS0.073s.
The original single-column phase counterexample is fixed.

The stricter admitted-phase check introduces a genuine normal-recovery regression:
recover_turns commits call.status=interrupted first, leaving turn.phase=admitted;
_terminal reloads the row through _turn, which now rejects that combination.
The actual child-death process test therefore reports held after a write instead
of settling interrupted, and later recovery cannot repair it. This is not a
fixture mismatch or hypothetical corruption. The unchanged process suite gives
4 PASS / 1 FAIL, 0.366s, specifically
`test_admitted_child_death_interrupts_no_reinference_or_refund`.

Evidence: `/private/tmp/pri-host-astra-corrected-process.log`; focused logs use
`/private/tmp/pri-host-astra-corrected39.log`, `-corrected8.log`,
`-corrected-phase.log`. All commands use Python3.13 -E -s -B unittest discovery.
Recommended correction is atomic interruption plus terminal/event settlement,
so strict public validation need not accept an invalid intermediate persisted
phase. Root was notified before approval; production source remains untouched.

## Final exact candidate — APPROVE within PRI01/1

Commit `d9f0e12de2db00a24e502dbe06acbf8843ce9be6`; source SHA256
`81a5ec8b6c65fce3b6aa5f76b0cd0430d4914ea972ea1740a16100842d99bfec`.
The strict phase checks remain in place. Recovery now changes an old, qualified
admitted call to interrupted inside the same terminal transaction as its call
hash, turn outcome and C14 event. It no longer commits an invalid intermediate
admitted/interrupted state. No blocking finding remains in the reviewed scope.
The two prior REQUEST_CHANGES findings and evidence above remain retained.

Independent execution with `/opt/homebrew/bin/python3.13 -E -s -B`, unittest
TestLoader discovery of the four unchanged files:
`test_primary_host_v5.py`, `test_primary_binding_review_v5.py`,
`test_primary_phase_review_v5.py`, `test_primary_process_v5.py`:
**53 methods PASS, 1.034s, exit 0**. This includes fixed39, binding8, phase1 with
four corruption subcases, and process5 including actual child termination/wait,
two-connection concurrency and the bounded whole mock flow. Log:
`/private/tmp/pri-host-astra-final53.log`.

Four additional independent actual-owner cases passed under the same runtime:
- Original consume-to-admission source-stop produces zero callback entry.
- Original malformed saved error is unavailable with no canary echo.
- Actual callback return with failed ending persistence leaves admitted history;
  after a new managed startup, append_event performs its real writes then raises
  RuntimeError. Recovery holds with an identical database snapshot, including
  admitted call status/hash, and no budget change. Restoring the event owner lets
  the same turn settle interrupted without another callback.
- The same after-event-write KeyboardInterrupt rolls back every settlement write,
  propagates and leaves no transaction open; restored retry settles once.

Log `/private/tmp/pri-host-astra-final-independent.log` binds the exact source
hash. Final candidate checkout remains clean; reviewer changed only this review
note and the previously authorized independent phase test in the review branch.

Approval is exact-source and scoped to the cooperative managed in-process mock.
The hashes detect inconsistent persisted bindings; they are not cryptographic
proof against coordinated trusted-store forgery. Lock/permit evidence does not
prove child/provider cessation. No live DB migration or external provider was
used. Full regression remains Root's separate responsibility; this does not
establish real-provider readiness, authentic usefulness or overall product
completion. No new owner approval or execution authority is created by this note.
