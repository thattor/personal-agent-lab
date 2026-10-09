# TSK02/1 — proposed controlled mock Expert step

DRAFT for Opus consultation, not implementation adoption. Prerequisite is the
verified MEM01 connection at013bf52. TSK03 read-only event pagination is independently
running through CO; it does not write shared state. SOL owns contract/integration.

Next contribution: append → intake → claim → source-bound mock Expert report or
lookup → durable step/event → release. Exercise pause/cancel/reference-stop while
the actual mock callable is held at a barrier. This gives an early useful connected
execution path instead of another collection of disconnected helper functions.
It remains a local mock, not actual model/GitHub/UI or completion/usefulness proof.

## Proposed required behavior

TSK stays sole owner of work state, single execution slot, source dependencies,
steps, budget reservations and events. Reuse existing tables and add only necessary
lease/call-lifecycle, control metadata, steps and reservations. No existing DB
migration, providers, authentication, cost, arbitrary execution or schedule.
All standalone mutations use BEGIN IMMEDIATE; MEM invalidation remains inside its
own transaction through the public TSK callback. No model/I/O wait in a transaction.

- claim({runner_id}) occupies one queued Goal, increments epoch, returns C13 lease /
  work / Brief / Grant / checkpoint / steps / pending_inputs. Another owner cannot
  claim while occupied. Replayed claim by the same runner must not create a new lease.
- register_sources({work_ref,refs}) checks current running authority and MEM before
  registering model context and lookup dependencies; no cached source authority.
- reserve_budget({key,work_ref?,kind,role?}) and consume({reservation_id,call_or_operation_id})
  enforce finite work plus explicit finite host limits. Persist usage across reopen /
  control; same key replays, different input conflicts; failed calls never refund.
- begin_step({key,work_ref,action}) supports report/lookup only initially, reserves
  a step once, and records the validated Action. Model-selected Refs must belong
  to actual supplied context; they do not create IDs or permission.
- finish_step({work_ref,step_id,result_refs,error?}) checks current authority/sources,
  stores result and event atomically. Repeated equal finish input replays by step ID;
  changed input conflicts. Report never completes a Goal.
- control({key,work_ref,command}) implements pause/resume/cancel. Owner commands
  compare revision, not epoch alone. Pause queued→paused; pause running requests stop
  and blocks new work/adoption; cancel invalidates epoch and retains occupied slot
  until owned call termination. Terminal resume conflicts.
- release({lease_id,work_ref,outcome,reason}) requires the currently owned lease and
  actual owned-call cessation. It can release an old epoch without overwriting a
  later pause/cancel/source-stop intent. Wrong lease cannot free the slot.
- Extend source-stop: running→epoch invalidation/draining then queued after cessation;
  paused remains paused; terminal history remains unchanged. Later pause/cancel while
  draining takes precedence. Subsequent stopped-source use is a visible bounded
  blocker, never a retry spin or silent cached-body reuse.

## Questions for technical disposition

1. Freeze claim retry/occupied/empty result and C13 step replay/error shapes. The v5
   claim request has no explicit key; the same runner can recover its owned lease.
2. Define the smallest correct call-start/control linearization. A host coordinator
   serializes admission with structured control; it must release its lock before
   waiting for a callable, so controls remain responsive. Distinguish a committed
   admission from actual callable entry. Test both ordered races with barriers.
3. Do not accept call_stopped=True or EXP self-report. A required trusted mock-call
   wrapper allocates/binds call ID, observes return/exception, and records cessation
   from its own termination path. A leased/orphaned call after reopen stays blocked;
   no automatic clearing, new call or inferred provider termination. If threaded,
   observe actual termination/join. This proves only mock callable cessation.
4. Keep roles honest: RUN owns no persistent state. TSK may own reservation/call
   binding and lease metadata, while full C15 raw-model-result ownership belongs to
   MOD. Decide whether the first mock host can avoid a separate raw output ledger
   without claiming complete MOD, or whether that small owner is essential now.
5. Select a stable finite host-budget identity/lifetime; changed settings cannot
   erase usage. Define exhaustion failure/state/event behavior and zero-budget path.
6. Lookup persists Ref selections, not MEM bodies; reread before each later mock
   call. Use explicit same-session search (existing work_ref filter is unavailable)
   and register every source before model reservation. Avoid a fake semantic search.

## Acceptance and division

One report step produces one durable event/step, Goal still unfinished. Lookup
reads actual MEM content and supplies it to the next bounded mock call. Zero/exhausted
budgets cause zero invocation; replay/control/reopen do not refund. Barrier cases:
pause-before-start, start-before-pause, cancel-held-call, stop-held-call, and
stop→pause/cancel. Late result is rejected; occupancy remains until observed cessation;
an old owned lease releases without losing newer intent. Failure at step/event/
reservation persistence rolls back its transaction and preserves prior receipts.

Proposed author split after scope freeze: isolated TSK persistence/control owner
(Astra or available SWE); independent root mock-driver/consumer integration;
separate Sol6.1 code review. No concurrent writes to shared files. Opus assesses
intent/contract alignment, not actual code correctness or human usefulness.

Ask/answer/C04, change/attach revisions, external Operation, ART/VER/complete and
full process recovery can remain explicitly unsupported; never emulate a question
as a report or mark Goal complete from an Expert summary. State which requirements
are truly necessary for this first connection before adopting the scope.
