# TSK02/1 — controlled mock Expert step

SOL technical disposition of the complete Opus5.5 consultation is adopted under
D038. Its CO document verifier failed on length; original note/receipt remain in
`evidence/operations/tsk02-20261009`. SWE consultation d3ad7fc12edc4abf89b66d3f46f93ba8
completed, with the technical dispositions below applied before code.
Prerequisite: MEM01/1 and TSK01/1, current source
6adf42b. This scope implements a local connected mock, not product activation.

Outcome: MEM append → intake → claim → source-bound mock Expert report/lookup →
durable step/event → release. Controls and reference stop must commit while the
actual mock callable waits at a deterministic barrier. Goal remains unfinished.
No new model/provider/auth/cost/service, existing live DB migration, UI, scheduler,
Operation, question/answer, change/attach, ART/VER completion or automatic recovery.
Python standard library only. Fresh isolated SQLite databases in tests.

## Ownership and files

One isolated author owns `pal/tasks_v5.py`, `tests/test_tasks_v5.py`, and
`docs/design/contracts-v5/TSK02-IMPLEMENTATION.md`. Small required internal hooks
in `pal/intake_v5.py` are also exclusively theirs. TSK remains one canonical owner.
Prefer `TaskStore(IntakeStore)` with the same constructor plus required host_limits
(Limits). Reuse intake/source/replay/event tables; add necessary v5_tsk_ tables.
No schema changes to existing tables. Existing IntakeStore callers retain their
queued-only behavior; TaskStore is the extended execution composition. Root owns
mock invoker/runner and connected tests, canonical docs and integration. Separate
Sol6.1 reviews the integrated implementation. C14 EventReader writes no state.

Standalone mutations require an idle caller connection and use BEGIN IMMEDIATE.
Rollback a failed transaction; no external call or body read inside a transaction.
MEM calls TaskStore.invalidate_by_refs on its exact active connection; no nested
BEGIN/COMMIT/ROLLBACK. Trusted callbacks are not arbitrary-code sandbox boundaries.

## Frozen host APIs

All request objects are strict v5 shapes; return Result with the eight ErrorCodes.
IDs are nonempty UTF-8 strings; integers exclude bool, are bounded for SQLite.
Repeated successful mutations return original receipts without new effects; changed
canonical input conflicts. Replay is historical, never fresh execution authority.
Internal keys use canonical JSON arrays. Missing identities are not_found;
wrong revision/epoch is stale; current-state/changed-input conflict is conflict;
stopped source is denied; exhausted budget is limit; persistence/source-owner
failure is bounded unavailable. Error messages never contain raw callback data.

- `claim({runner_id})`: oldest queued row by rowid → running, epoch+1, occupied
  lease and state event atomically. Return C13 fields lease_id/work_ref/brief/grant/
  checkpoint/steps/pending_inputs; empty is `{status:empty}`. Same runner while it
  owns an active lease returns that lease/current work metadata without new effects.
  Another runner sees conflict, even if the owned work was cancelled. Each host
  process mints a fresh runner_id; do not adopt an old runner after restart.
  Successful claim has no additional status field. Checkpoint is
  `{last_finished_index:int,open_question_refs:[],lookup_truncated?:bool,
  lookup_excluded_refs?:[Ref]}`;
  initial last_finished_index is -1, first step index is 0.
- `get_execution_context({lease_id,work_ref})`: host-only read for the root driver:
  return session_id, required_refs (origin plus Brief.context_refs), optional_refs
  (registered lookup refs minus required), remaining_budget (work and host counts
  per kind), and next_step_index. Check owned lease/current authority. No bodies.
  remaining_budget is exactly `{model:{work,host},step:{work,host}}`.
  This metadata read must not gate all optional refs before the driver can omit
  stopped ones. Effect admission separately checks required/supplied availability.
- `register_sources({work_ref,refs})`: current running authority/no control, verify
  all exact refs through MEM in transaction, insert dependencies once. No cached
  source authority. Required refs originate from intake; new refs are optional.
- `reserve_budget({key,work_ref,kind,role?})`: kind=model or step; only expert role
  for model in this slice. Work-less and operation are unavailable. Reserve one
  from both finite ledgers atomically; return reservation_id and remaining
  `{work:int,host:int}` for that kind. Failures never refund. Step reservation is
  internal to begin_step, not a second runner reservation.
  Bind reservation metadata to the sole active lease, claimed WorkRef, next index,
  kind and role. A model reservation also requires remaining work/host step budget
  before debit. A reserved last model unit remains valid when unused count is zero.
- `consume({reservation_id,call_or_operation_id})`: bind exactly once; same binding
  replays, another ID conflicts. Must not let an unrelated step/model reservation
  authorize a call. admit_call performs the model consume in its own transaction.
  A standalone consume is only a binding receipt, never invocation permission.
- `admit_call({call_id,lease_id,work_ref,reservation_id,source_refs})`: requires owned
  current running lease/no control, no unended call and no unadopted returned call
  for this next step. Recheck MEM and registered membership, consume model reservation
  and persist call lifecycle metadata atomically. Index is next step index; host
  call_id is derived from lease_id/index. Return call_id and status. Equal replay
  returns the original receipt but must not cause another invocation.
  Enforce required refs ⊆ supplied refs ⊆ registered refs and exact reservation
  lease/WorkRef/index/kind. Step headroom is still required before invocation.
  No next call while any step is started. A returned call without a step may only
  be adopted by begin_step; a finished step enables the next index. Raised or
  not_entered calls require release, never another call at that same index.
- `end_call({call_id,outcome})`: trusted invoker only, outcome returned/raised/
  not_entered, recorded after actual return/exception or known skipped entry. May
  finish an old epoch; cannot adopt its output. Replay by call_id + canonical input.
  No model/runner-supplied call_stopped boolean. A read-only call-status query is
  `get_call({call_id}) -> {call_id,lease_id,work_ref,index,
  status:admitted|returned|raised|not_entered,may_enter:bool,step_id?}`. may_enter
  requires admitted phase plus current owned running authority and no control.
  It is information, never
  invocation authority. Cessation persistence failure leaves occupancy blocked.
- `begin_step({key,work_ref,action})`: parse with shared model-action validator and
  refs actually supplied to the ended/returned call at next index. Only report and
  lookup supported; other valid actions return unavailable. Current authority and
  current supplied-source availability, no active control. Reserve step once and
  store C13 Step. No second step per call/index. Report is not completion.
- `finish_step({work_ref,step_id,result_refs,error?})`: strict C13 shape, replay by
  step_id/canonical input; current authority, no control, current sources. Report
  has empty result_refs. Lookup uses actual MEM same-session search plus C11 reads
  outside the transaction; recheck/register usable returned refs here. Newly found
  denied/not_found optional refs are excluded and named in checkpoint/event metadata;
  unavailable rolls back. Optional host keyword `excluded_refs=()` carries refs
  already excluded during C11 reads and is included in canonical replay identity.
  Previously supplied refs must still be available. Persist step/checkpoint and one
  progress/error event atomically. Lookup truncation is passed explicitly via a
  host-only keyword `truncated=False` and included in replay/event/checkpoint metadata;
  it must not silently add a field to C13 Step. Never store copied MEM bodies.
- `control({key,work_ref,command})`: pause/resume/cancel. Owner commands compare
  goal_id/revision, not epoch alone. Queued pause→paused; running pause records
  pause_requested without epoch change and blocks admission/adoption. Cancel on
  nonterminal sets cancelled and epoch+1, keeps occupied lease. Paused resume→queued;
  terminal/running resume conflicts. New-key repeated pause/cancel returns current
  state. Corresponding state event and replay commit together.
- `release({lease_id,work_ref,outcome,reason})`: yield/paused/failed. Unknown lease
  not_found; wrong slot owner denied; wrong Goal/revision stale. Every admitted
  call must have ended; otherwise conflict. Old owned epoch may release. paused
  requires pause intent. Abandon started steps, free slot and persist state/event/
  receipt together. Precedence: cancelled → paused intent → draining queued →
  runner outcome (yield queued, failed failed). Replay by lease_id + canonical input.
  Clear the resolved draining/pause flags on every successful release. Otherwise a
  requeued stopped origin could yield forever instead of failing once on reclaim.
  With no control intent, yield conflicts on a returned call without a finished
  step (including a started step). Explicit failed may terminate; cancellation,
  pause or draining may discard the fenced output while retaining the newer intent.

## Linearization and source-stop

Admit/control/stop are ordered by SQLite commit. Admission means the call is already
owned/in-flight for control purposes, even before Python entry; this is not proof
that the callback ran. A wrapper may reread and skip entry as not_entered. The small
race after that read belongs to the already admitted call: control still fences
its result and retains occupancy. Do not claim atomic physical callback entry or
remote termination. No DB transaction or coordinator lock spans the callback.
Root's trusted synchronous wrapper records end_call in its termination path. If
threading is used, observe actual callback return/join; a timeout is not cessation.
A repeated admission receipt never reinvokes a callable. Orphaned occupied calls
remain blocked after reopen; recover is unavailable, no clearing or recomputation.
Before admission, the one trusted invoker owned by the host process registers the
call ID under a process-local lock/map. Only its first owner can enter. An uncertain
admission result stays blocked. This map does not replace TSK persistence and is
not a security boundary against arbitrary host code. It prevents duplicate wrapper
entry, including concurrent calls; a new host uses a new runner ID and cannot
resume an old occupied lease. No lock spans the actual callable.

TaskStore invalidation retains check-all-before-write and coverage checks. For each
matched current revision: queued→epoch+1 queued; running→epoch+1 with draining flag;
paused→epoch+1 paused; cancelled/failed skip unchanged. waiting_input/completed remain
unavailable and are not reachable through this slice. Running may have pause intent;
keep it when marking draining. Event routes to the affected work's stored session;
MEM acknowledgement routes to the initiating session. Cancel/pause committed during
draining wins at release. Mixed queued/running/terminal dependencies remain atomic.
A stopped required source after requeue makes one explicit failed/blocker result,
not a retry spin. Stopped optional lookup sources are omitted and named as excluded
before a later call; no cached bodies and no stopped selected refs in model context.

## Budgets and limits

Host ledger lifetime is this database: explicit finite Limits required, each within
SQLite range, zero valid. No reset API. Configuration may change limits only, never
used counts; counts >= limit are exhausted. Work ledger is goal_id across revisions,
using Grant ceilings and no reset on control/reopen. Claim refuses exhausted host
model or step budgets without changing state. Mid-lease host limit yields with a
reason, work limit fails with a reason; required-source denial fails once. No unused
reservation refund. These are mock invocation/step counts, not real provider usage.
Full C15 MOD raw result/status/model_id/replay/interrupted/work-less calls remain
unmet. TSK owns only execution-right metadata, no raw model output ledger. A crash
losing in-memory output cannot safely reinvoke it and remains blocked for recovery.

SWE advice is applied on binding, one-shot draining, admission dedupe, readiness,
lookup exclusions and budget headroom. Two stronger suggestions are not adopted:
blanket refusal to release a returned-but-fenced output on pause/draining conflicts
with C13/latest-intent semantics; the ordinary no-control yield remains rejected.
Restricting old-epoch release to claimed/current epoch is unnecessary authority:
the owned lease plus Goal/revision authorizes freeing occupancy, never adoption.
Keep C13 old-owned-epoch release. Astra's matching lifecycle clarification adds no
new product scope. Root's mock entry/cessation is only a trusted in-process proof.

## Verification and returned evidence

Author tests: strict input, empty/occupied/retried claim, current/replayed/stale
control, wrong/old owned lease, step/call dedupe, finite budgets across reopen/limit
changes, all-or-nothing event/step/reservation failure, source coverage and mixed
state invalidation, no transaction crossing callbacks. Zero budget invokes nothing.
Root connected tests use actual MEM/TSK/C14 and a real mock callable: report then
lookup supplies actual usable bodies/hash to next call; pause-first/admit-first;
admit then pause before entry; cancel/stop while held; stop→pause/cancel and pause→stop;
late adoption denied; no release before cessation; raising callback no refund;
reopen orphan stays blocked; stop-before/after lookup registration; no duplicate
notification on reconnect. Use Events/barriers, never sleeps or caller stop booleans.

Return exact diff, test command/count/status, API shape note and unresolved limits.
Root verifies source, integrates, runs full suite and obtains separate review before
accepting the connected unit. Then continue the next unfinished authorized slice.
