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
