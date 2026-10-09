# TSK02/1 SWE implementation review

## Assessment

The adopted scope correctly reflects the Opus F1-F5 corrections: `TaskStore(IntakeStore)`, new `v5_tsk_` tables, retained queued-only `IntakeStore` behavior, mixed-state invalidation, one occupied slot, admit/not_entered/end_call, finite non-refunding ledgers, commit-order linearization and required-versus-optional sources are all present.

It is still not safe to code verbatim. Four lifecycle details need explicit rulings: release of a returned-but-unadopted call, draining-flag reset, reservation-to-lease/index binding, and the post-admission entry predicate. Without them the implementation can create a permanently requeued blocker, reuse a stale reservation, or accidentally reinvoke on replay.

## Minimal persistence

Do not alter `v5_intake_*` schemas. Required refs remain `origin_record_ref + brief.context_refs`, derivable from stored JSON; optional refs are `v5_intake_source - required`.

Add only:

- `v5_tsk_slot`: singleton row containing active `lease_id`, `runner_id`, `goal_id`, `revision`, claimed `epoch`.
- `v5_tsk_work_exec`: `goal_id/revision`, `pause_requested`, `draining`.
- `v5_tsk_call`: `call_id`, lease/work/epoch, `step_index`, `reservation_id`, persisted `supplied_refs`, `outcome NULL|returned|raised|not_entered`, `adopted_step_id NULL`. No mock output or MEM bodies.
- `v5_tsk_step`: C13 step plus internal `call_id`, `truncated`, `excluded_refs`; returned Step keeps the exact C13 shape.
- `v5_tsk_reservation`: `reservation_id`, `lease_id`, work/epoch, `planned_index`, `kind`, `role`, `bound_id`.
- `v5_tsk_host_budget(kind,limit,used)` and `v5_tsk_work_budget(goal_id,kind,used)`.

Constructor accepts the existing signature plus required finite `host_limits: Limits`, validates each value `0..SQLite-int64-max`, initializes/updates limits and never resets `used`.

## Transaction and lifecycle rulings

- Standalone mutations use `BEGIN IMMEDIATE`; failure rolls back that mutation only. `invalidate_by_refs` remains a same-connection/same-transaction callback: no BEGIN/COMMIT inside, check all matches before writes. `source_gate` runs inside a savepoint with transaction/change checks as in intake create.
- MEM `search`/`read` happen outside transactions. Admission rechecks `required ⊆ supplied ⊆ registered` and all supplied refs through the bound gate.
- Flow: claim, register/reverify required refs, read usable context, reserve model, admit, invoke outside a transaction, record end_call, begin_step, perform lookup I/O, finish_step, then repeat or release.
- `claim` should return `{status:'claimed',...}` or `{status:'empty'}`. One occupied slot serializes all runners; active leases and unended/unadopted calls survive reopen and block. A fresh `runner_id` never adopts them.

## Required corrections

1. **Returned-but-unadopted output.** `release` must not yield/pause this work: the volatile output would be lost while the call row still blocks the next admission. If cancelled, release may persist cancelled. Otherwise `release(failed)` persists failed with a lost-output reason; `yield`/`paused` returns conflict and keeps the slot occupied. Do not let pause/draining precedence resurrect it.
2. **Draining is one-shot.** Clear `draining` on every successful release. Otherwise stop→queued→claim→required-source-denied→release(failed) would keep choosing queued and spin instead of one terminal blocker.
3. **Reservation relation.** `reserve_budget` infers the sole active lease for the work, requires current running/no control, and stores lease/epoch/`planned_index`. `consume` is an internal transaction participant: admission binds only the model reservation for that exact lease/epoch/index; begin_step binds only its own step reservation. A public standalone `consume` must not independently authorize anything.
4. **Admission replay.** A stored admission receipt is not a dispatch signal. The trusted invoker must dedupe `call_id` in its process or use an explicit persisted dispatch transition; a crash after admission leaves the occupied call blocked because a fresh runner cannot adopt it.
5. **Entry evidence.** Document the allowed read-only call-status query before driver use and include enough state for `may_enter`, e.g. call phase plus current control/draining. After admission commits, reread it: `may_enter=false` records `not_entered`; otherwise invoke once. Threading requires observed return/join, never timeout-as-cessation. Bounded SQLite-busy retry for `end_call`; if still unwritten, the call remains unended and occupancy blocks.
6. **Adoption.** `begin_step` accepts only the latest `returned` call at the next index and action refs supplied to it. `raised`/`not_entered` and any prior unadopted call block admission/adoption. Mark the call adopted only when `finish_step` commits; abandoning a started step does not adopt output.
7. **Lookup refs.** Supplied refs must still be current; stale/denied rolls back step/event. Newly returned lookup refs are optional: deny/not_found refs are excluded and recorded in internal/event/checkpoint metadata, usable refs are persisted and registered; `unavailable` gate failure rolls back. Never persist bodies or silently omit a stopped ref.
8. **Release identity.** Compare the lease, goal and revision, and accept only the lease's claimed epoch or the work's current epoch; not an arbitrary epoch. Cancel keeps the occupied slot until all calls end and release commits.
9. **Budget invocation guard.** Before invoking, require headroom for both model and the next step; otherwise no callable runs. Used counts persist across reopen/limit changes and are never refunded for raise, not_entered, unused or failed reservations.
10. **Compatibility/events.** Preserve base `IntakeStore.invalidate_by_refs` queued-only semantics for existing callers; the extended mixed-state behavior belongs to the TaskStore override. Work events use `work.session_id`; MEM's acknowledgement uses the initiating session.

## Essential tests

Add barrier tests for pause-before-admit, admit-then-pause-held, pause-before-entry (`not_entered`), cancel/stop-held, late-result stale and all stop/pause/cancel release orders. Specifically cover: unadopted returned output cannot yield/pause; draining clears and stopped required source fails once; replay admission invokes zero times; `end_call` persistence failure blocks; raising mock has no refund; orphan lease/call remains blocked after reopen; unrelated/stale reservation cannot authorize; zero model/step work or host budget invokes nothing; optional stopped lookup refs are named exclusions; required stop fails closed; mixed queued/running/terminal invalidation is atomic while base IntakeStore still rejects non-queued. Verify all-or-nothing step/event/reservation rollback, singleton slot conflict, session event routing and absence of MEM body copies.

## Planner instruction (<1200 bytes)

Update the implementation brief, then assign one isolated author: `pal/tasks_v5.py`, its tests, TSK02-IMPLEMENTATION, and only required protected hooks in `pal/intake_v5.py`. Require the ten corrections above, especially unadopted-output fail-close, one-shot draining, lease/epoch/index-bound reservations, one-shot admission dispatch and documented `may_enter` status. Root owns mock invoker, connected tests and integration; no code in this step.

## Verdict

REFINE