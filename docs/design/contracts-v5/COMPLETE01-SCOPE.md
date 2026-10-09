# COMPLETE01/1 — verified local completion with retained history

PROPOSED technical Stage B under D038/C074. Do not implement until Opus and SWE
consultation dispositions are recorded. Stage A VER is independently in progress.
This proposal follows Opus task7cd3d557 L1/L2 and the independent Astra analysis of
source3f37f78. It grants no product activation or new external effects.

Value: a saved draft can reach completed only from current, host-verified fixed
Conditions. A later source stop preserves that historical completion and stops
reuse. Merely returning an Expert report or saving a body cannot complete work.

One accepted slice must include all three: C10 complete, source-stop for completed
history, and terminal-safe lease handling. No partial activation of complete.
Exclude answer/change/questions, model verify Action, semantic evaluation/budget,
artifact model re-input, EXE/provider/PRI/UI, general restart recovery, live DB,
new service/auth/cost/publication and all prior unknown-call retries.

## TSK public seam and strict authority

TaskStore adds optional trusted verification_inspect=VerificationStore.inspect.
Missing collaborator makes complete unavailable. Existing control strings remain
pause/resume/cancel. Add one closed object command:

    control({key, work_ref,
             command:{kind:'complete', verification_ref:{kind:'verification',id}}})

Return the existing C10 shape {work_ref,state:'completed',control_status:'none'}.
No arbitrary checks/evidence/Goal state from caller. Wrong shape/kind invalid_input.

TSK owns BEGIN IMMEDIATE and original canonical key replay before current rights.
Changed same-key input conflict. New completion requires exact current WorkRef,
running owned lease, no pause/drain. Keep current authority error precedence.
Call VER.inspect on this exact connection inside that transaction with readonly
savepoint/change/transaction guards. No VER SQL reads and no get_by_key authority.

Strictly validate the typed Result shape: work_ref, ordered artifact_refs, checks,
record source_refs and status. Require status valid, exact WorkRef and whole ordered
current artifact set. Require exactly one Check for every immutable unique Condition
ID, in fixed order, and every status met. Bounded reasons and evidence Ref kinds/
membership must match the C09 available set. Required origin/Brief record refs must
be included, every dependency must be registered, and gate all supplied sources
again using MEM in this transaction. Actual VER owns the conservative ART union.
Malformed owner output or corrupt evidence is unavailable. Invalidated/old WorkRef
or changed set is stale; valid unknown/unmet is conflict; missing verification is
not_found. Empty Condition lists are invalid stored state, never vacuous success.

Before writing completion, require all calls in the current lease to have ended;
no admitted call, started Step or returned output without its finished Step. No
budget refund or extra reservation. In the same transaction persist completed,
close the active lease, clear pause/drain flags, append exactly one result event
with current artifact refs and verification Ref, and store the original receipt.
Current epoch remains unchanged. Same-key replay after closure/stop returns original
history and emits nothing. Ordinary exceptions and BaseException roll back all
owned writes; BaseException propagates. Trusted collaborator COMMIT cannot be undone.

## Completed history and terminal safety

invalidate_by_refs must accept dependencies of completed work. Keep its state,
epoch, artifact set and completion fact. In the existing MEM transaction emit a
bounded source-stop notice to the work session once per invalidation key; report
the current WorkRef in the affected result. No VER write hook/second state engine.
VER current status then derives invalidated from the denied MEM dependency; ART
verification/model_context reads deny and user_view retains history usable=false.
Existing cancelled/failed handling remains unchanged. Unsupported waiting_input
is not silently implemented by this slice.

release must preserve completed/cancelled/failed before considering flags/outcome.
It still requires the known matching active lease and cessation of admitted calls.
After successful complete the lease is already inactive: a new release request
may remain denied; an old replay keeps its original result. No reopen of terminals.
Do not filter stopped artifacts from the append-only current set to obtain MET;
completion of such a revision remains blocked until an explicit future change API.

## Optional mock host connection

MockRunner(..., artifacts=ART, verifications=VER) enables the local host sequence.
Default verifications=None preserves current bounded draft-only operation. This is
test/local composition, not a real service toggle. Model verify Action stays closed
and verification Ref never enters Step.result_refs or model context in this slice.

Host reads the exact current artifact set, then calls C09 verify with a canonical
key bound to WorkRef plus ordered set. If every fixed check is met it calls C10
complete with a key bound to WorkRef plus verification Ref. C10 revalidates all
authority. Success returns completed without an additional release. Keep finished
step/call diagnostics and the original verification receipt in the local response.
Unknown/unmet yields unfinished with an explicit reason and no terminal failure.

Run this finalization seam after finished compose and before any new inference when
reentering a lease that already holds attached artifacts. That permits bounded
same-input verification/completion replay after lost responses without a second
model call or a separate persistence engine. Use the existing three-attempt local
unavailable retry limit, with no new inference to repair local persistence. On
persistent ambiguous completion response retain occupancy and return unavailable;
reentry reaches the same finalization seam first. A current pause/cancel/source stop
uses existing TSK release fencing. Do not convert transient unavailability to failed.
An inactive lease after a committed but lost response never lets release overwrite
completed. General adoption by a new runner after process restart remains excluded.

## Ownership and required evidence

Root owns this contract, integration, actual consumer tests and canonical records.
One isolated implementation owner writes TSK complete/terminal/source-stop and
focused tests. Another writes the RUN host coordinator/tests only after this seam
is frozen. Their source files do not overlap; shared schema and event meaning remain
TSK-owned. Independent reviewers differ from authors; no mandatory double review.

Tests must use real temporary SQLite MEM/TSK/ART/VER for the connected path:

- compose -> verify MET -> complete, one result event, closed lease, next Goal claim;
  semantic/source_fetched unknown cannot complete; no additional model/step spend;
- stale epoch, new attachment, subset/reordered refs, missing/duplicate Conditions,
  forged/malformed callback or corrupted VER evidence fail closed;
- two-connection pause before complete vs complete before pause, and source stop
  before complete vs completed history followed by successful stop and invalidation;
- admitted call, started Step and returned unadopted output cannot close occupancy;
- failures/interrupts after actual completion writes roll back state, lease, event
  and replay; commit-lost responses replay once, persistent uncertainty/reentry never
  invokes another model or corrupts terminal history;
- reopen keeps original completion receipt and source-stop history distinct;
  inspect preserves caller ownership, no cross-owner SQL/hidden model calls.

Frozen tests/host receipts and independent review must precede a milestone claim.
CO verified covers its declared command only. Whole PAL, semantic usefulness and
the user-facing real assistant remain unfinished even when this local slice passes.
