# TSK02/1 implementation

TaskStore extends IntakeStore with durable local execution rights. This is author
implementation and self-check, not independent review, product activation or
proof of provider execution. Frozen scope and Root dispositions govern; no old
implementation or database was reused. IntakeStore and its existing schema are
unchanged. The new tables use the `v5_tsk_` prefix.

## API and persistence decisions

TaskStore accepts IntakeStore's constructor arguments plus required finite
`host_limits: Limits`. The connection is caller-owned, idle, and autocommit-mode
between commands. Standalone mutations use BEGIN IMMEDIATE; successful receipts,
work/lease/control/call/step/budget/dependency changes and C14 events commit together.
Failures roll back. Trusted source gates run inside the owner's transaction and
must perform no writes. No external invocation or body read occurs here.

Public methods are claim, get_execution_context, register_sources, reserve_budget,
consume, admit_call, end_call, get_call, begin_step, finish_step, control, release,
and the inherited intake/event APIs. Inputs are closed JSON objects; host callback
keywords retain their exact typed boundary. Results use shared immutable Result.
Contract failures are invalid_input; current-state failures conflict; identity,
version, source and budget errors use the frozen error table. Public failure
messages/refs never echo raw inputs, callback exception text or DB diagnostics.

- Successful claim has exactly lease_id/work_ref/brief/grant/checkpoint/steps/
  pending_inputs; empty has only status=empty. The checkpoint starts at index -1.
  First step index is 0. A retained lease blocks other runners even after cancel.
- Execution context returns session_id/required_refs/optional_refs/remaining_budget/
  next_step_index and Root's adopted `step_sources:[{step_id,refs}]` provenance.
  Provenance combines each stored call's supplied refs and its step result refs.
  Missing provenance fails closed. Optional stopped refs remain discoverable so
  the driver can exclude their bodies and dependent historical steps before C12.
  This metadata read grants no fresh source authority; admission gates supplied refs.
- register_sources returns `{refs}`. reserve_budget returns reservation_id and
  remaining work/host counts. The reservation stores lease, exact WorkRef, index,
  kind and role. Public step reservations remain valid C15 receipts, but the runner
  must not reserve twice: begin_step owns its own step reservation. consume returns
  reservation_id/call_or_operation_id; a binding is never invocation permission.
- admit_call/end_call return call_id/status. Call IDs are canonical JSON arrays
  `["C15.call", lease_id, index]`. Admission rejects wrong reservation provenance,
  missing required sources, unregistered sources, an outstanding call, a returned
  unadopted result or a started step. The last reserved model unit stays valid;
  step headroom is required before model reservation and again before admission.
- get_call exposes call_id/lease_id/work_ref/index/status/may_enter and optional
  step_id. may_enter is information only. end_call records trusted mock return,
  exception or skipped entry, including old epochs. Reopen never clears occupancy.
- C13 Steps retain their closed schema. Only report/lookup are adopted. Finished
  lookup source exclusions and truncation live in checkpoint/event metadata, not
  Step keys. `finish_step(..., truncated=False, excluded_refs=())` requires bool
  and tuple[Ref]; both participate in replay identity. New unavailable refs abort;
  denied/not_found refs are excluded. Report progress text is the stored summary;
  lookup progress text is JSON metadata. Host error text uses the error event kind.
- control and release return work_ref/state/control_status. Control compares
  Goal/revision, ignores epoch alone, and is replay-safe. Release requires the
  occupied lease and every admitted call's recorded cessation. Any owned old epoch
  can release; it cannot adopt output. Precedence is cancel, pause, drain, outcome.
  Successful release clears both flags. Ordinary yield cannot discard returned
  unfinished output; explicit failure or a newer control intent may discard it.
- `invalidate_by_refs(connection, *, key, session_id, refs)` retains the exact MEM
  callback signature; refs is tuple[Ref]. The caller owns commit/rollback. It checks
  all dependency coverage/states before writes, increments queued/running/paused
  epochs, marks running draining while preserving pause, and skips cancelled/failed.
  Events use each affected work's session. Unsupported states abort the enclosing
  MEM transaction. Callbacks are trusted host methods, not a sandbox; no claim of
  rollback after an arbitrary callback commits independently is made.

Host usage survives reopen and configuration changes; changing limits does not
reset use. Work usage is keyed by Goal, across revisions. Reservations never refund.
No default finite ceiling is silently invented. Claims refuse exhausted host budgets.
One current lease is enforced by a unique partial index. UUIDs remain the default
identity source; injected ID factories are trusted test/host code and collisions
cause rollback. C02 remains its closed base projection; active pause/drain is visible
through control/release responses, get_call and state events, not a new UI badge.

## Verification and corrected boundary defect

The initial 28 synthetic tests passed at `/private/tmp/pal-tsk02-author-initial.log`,
but Root found that the new invalidation method accepted a request dictionary while
MEM and the inherited method call keyword arguments. Cause: author tests repeated
the wrong local signature instead of testing the existing consumer boundary. This
initial result did not establish MEM integration. The correction retains the exact
base callback signature and adds an actual MemoryStore.stop_reference regression,
including stale adoption, drain release, requeue and required-source failure once.
Next changes to inherited callbacks must check their real caller signature and run
this connected boundary test, rather than relying only on a synthetic direct call.
The corrected callback run is `/private/tmp/pal-tsk02-author-callback.log`.

Final author command:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_tasks_v5.py -v
```

Final log: `/private/tmp/pal-tsk02-author-final.log`. 32 tests cover strict shapes,
closed actions/steps, identity collisions, empty/occupied/retried claims, historical
receipts versus authority, source membership and freshness, lookup exclusions,
provenance, pause/cancel/drain ordering, old-owned-epoch release, finite zero/last-unit
budgets, lifetime counts, wrong reservation kind/lease/index, event/reservation/step/
cessation failure rollback, same-connection MEM invalidation, mixed state prechecks,
source coverage, bounded callback failures, busy locking and orphan occupancy.
Tests use isolated temporary SQLite DBs and deterministic faults; no live services.

NOT_RUN here: Root's actual mock callable barrier/cessation and complete MEM→TSK→RUN
consumer suite, full regression and separate exact-commit review. Real MOD raw
output/status/model_id, external provider termination, recovery/recomputation,
Operation, PRI, historical revision mutation, question/answer/change, ART/VER,
completion, scheduling, UI, activation and human-value acceptance remain unmet.
A persisted admission or end_call receipt is not proof of remote provider cessation.

## Interruption cleanup follow-up

Root inspection found that the new constructor and standalone transaction owner
caught Exception rather than BaseException. Consequently KeyboardInterrupt or
SystemExit from trusted host code escaped without rolling back an open transaction.
The prior ordinary-exception tests did not cover process-control exceptions. A
pre-fix run retained at `/private/tmp/pal-tsk02-baseexception-before.log` reproduced
six failures across two new tests: both exception types after work/lease writes,
after the first TSK DDL statement, and after host-ledger setup. All showed an open
transaction remaining after interruption.

Both owner cleanup handlers now catch BaseException, roll back and re-raise the
original interruption. The public Result boundary still catches only Exception:
process-control exceptions are not converted into a normal failure response.
The new deterministic tests verify unchanged durable state/schema, an idle original
connection, and write-lock availability from another connection. They are the next-use
regression condition for changes to either transaction owner. Caller-owned MEM
callback transactions retain their existing ownership rules.

The same targeted Python 3.13 command now passes **34 tests**. Retained post-fix log:
`/private/tmp/pal-tsk02-baseexception-after.log`. This follow-up is an author check;
Root owns broader consumer regression and independent acceptance.
