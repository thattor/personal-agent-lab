# COMPLETE01/1 — verified local completion with retained history

ADOPTED technical Stage B under D038 after Opus consultation72fabf04 and SWE
consultationd8bd21a2 (both REFINE), with Root dispositions below. Stage A VER
implementation is independently reviewed atfab7c77 and full650 passes.
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
Construct TSK first with a forwarding closure to VER, then construct VER with
TSK.verification_context, like the existing ART cycle; no mutable public setter.
Missing collaborator makes new complete unavailable, checked after key replay.
Existing control strings remain
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
Malformed owner output or corrupt evidence is unavailable. First preserve current
authority errors, then missing verification not_found. Different inspected Goal or
revision is conflict; old inspected epoch or changed set is stale. After all TSK
comparisons and current source gates pass, an unexplained invalidated status is
unavailable because the owners disagree. Source gate failures keep their existing
denied/unavailable mapping. Valid unknown/unmet is conflict. Empty Condition lists
are invalid stored state, never vacuous success.

Before writing completion, require each call in the current lease to be returned,
raised or not_entered; every returned row needs its finished Step and no Step in
the revision may be started. Unknown saved call/Step state is unavailable; valid
unfinished activity is conflict. No
budget refund or extra reservation. In the same transaction persist completed,
close the active lease, clear pause/drain flags, append exactly one result event
with current artifact refs and verification Ref, and store the original receipt.
Current epoch remains unchanged. Same-key replay after closure/stop returns original
history and emits nothing. Ordinary exceptions and BaseException roll back all
owned writes; BaseException propagates. Trusted collaborator COMMIT cannot be undone.

## Completed history and terminal safety

invalidate_by_refs must accept dependencies of completed work. Keep its state,
epoch, flags, artifact set and completion fact, even at maximum epoch. In the
existing MEM transaction emit one progress notice per completed Goal/key to the
work session with only the stopped refs registered for that Goal. Fixed text:
'a source registered for this completed work was stopped; completion is historical'.
This does not claim completion revocation or that an unused optional source was a
VER dependency. Keep the existing closed {work_refs} result: it lists only works
whose epochs were invalidated; completed history is signalled by the progress event.
MEM currently validates this list and does not use its values (_callback); no new
field or second invalidation engine is necessary. No VER mutation hook is added.
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
Supplying verifications without artifacts is invalid host configuration.
Default verifications=None preserves current bounded draft-only operation. This is
test/local composition, not a real service toggle. Model verify Action stays closed
and verification Ref never enters Step.result_refs or model context in this slice.

Host reads the exact current artifact set, then calls C09 verify with a canonical
key dumps(['C09.verify',work,refs]). If every fixed check is met it calls C10
complete with dumps(['C10.complete',work,verification_ref]). C10 revalidates all
authority. Success returns completed without an additional release. Keep finished
step/call diagnostics and the original verification receipt in the local response.
Unknown/unmet falls through to the normal finite step loop, with the verification
result available in the local response. It does not by itself release/fail work or
skip a needed next step. Existing actual budget exhaustion can still fail work.

Run this finalization seam after each finished compose. At entry, first pass the
existing started-Step and get_call readiness checks; only trigger finalization
when the last finished Step is compose and its artifact is the current set tail.
For an active retained lease this happens before new inference and permits bounded
same-input verification/completion replay after lost responses without a second
model call or a separate persistence engine. Use the existing three-attempt local
unavailable retry limit, with no new inference to repair local persistence. On
persistent ambiguous completion response retain occupancy and return unavailable;
active-lease reentry reaches the same finalization seam first. If completion had
committed, the lease is already inactive and the next claim may move to another
Goal; it never invokes a model again for that completed Goal. A current pause/cancel/source stop
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
  one source shared by completed and running work must stop both uses atomically;
- admitted call, started Step and returned unadopted output cannot close occupancy;
- failures/interrupts after actual completion writes roll back state, lease, event
  and replay; commit-lost responses replay once, persistent uncertainty/reentry never
  invokes another model or corrupts terminal history;
- reopen keeps original completion receipt and source-stop history distinct;
  inspect preserves caller ownership, no cross-owner SQL/hidden model calls.

Frozen tests/host receipts and independent review must precede a milestone claim.
CO verified covers its declared command only. Whole PAL, semantic usefulness and
the user-facing real assistant remain unfinished even when this local slice passes.

## Frozen SWE disposition

Adopt the ten complete steps and the explicit R1-R8 details from the consultation.
The public constructor rejects verifications without artifacts with ValueError.
A successful RUN completion returns status=completed, work_ref, state=completed,
control_status=none, lease_id, the original C09 receipt under verification, finished
steps, call_ids and existing excluded_refs/excluded_step_ids diagnostics. It does
not fabricate a finished verify Step. Include the last verification receipt in
normal finite-slice results when present, so unknown is visible without a Goal
completion claim. No change to the default collaborator-free behavior.

After valid non-MET, continue the normal bounded loop. After complete conflict,
stale or denied, likewise return to the loop; its execution-context authority and
existing release boundary settle any newer pause/cancel/drain before inference.
A persistent verify unavailable uses yield_or_retain; persistent complete
unavailable returns unavailable without release. Other malformed/unknown callback
outcomes fail closed without treating model re-invocation as persistence repair.
Keep canonical C09/C10 requests unchanged through each three-attempt retry.

Readonly inspect guards must clean their owned savepoint on failure; do not copy
only the success path of the older _inspect_artifact helper. Validate recognized
call and Step statuses before readiness comparisons. Invalidated while every TSK
comparison/source gate succeeds means owner disagreement, not a guessed source
stop. Root selected work_refs to contain only actual epoch invalidations, avoiding
a needless MEM contract change; historical completed notices carry their own refs.

All changes remain isolated until the three TSK safety pieces pass together. The
RUN owner depends on this frozen contract, not implementation internals; actual
consumer tests and independent reviews gate the integrated milestone claim.
