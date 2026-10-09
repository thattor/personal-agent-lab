# TSK02/1 scope review: Opus design consultation

This review checks TSK02-SCOPE.md (draft) against PAL v5 C03/C10/C13/C14/C15, MEM01-SCOPE and the snapshot of pal/intake_v5.py and pal/memory_v5.py. It assesses contract and intent for this goal/scope only. It is not code review, not runtime evidence, and makes no completion or usefulness claim. It adds no owner approval gate, and SOL keeps the disposition.

The direction is right. One connected path (append, intake, claim, mock step, event, release) tested with barriers is the correct next unit. The corrections below are needed before the scope is frozen.

## Findings in the actual code

- F1 `invalidate_by_refs` returns unavailable for any matched state other than queued.
  - Once TSK02 writes running, paused or cancelled, the stop-held-call test cannot pass.
  - A stop of a record used by any cancelled Goal would roll back every time.
  - Fix: extend it with the same check-all-before-write rule:
    - queued: epoch+1, stays queued.
    - running: epoch+1 and draining.
    - paused: epoch+1, stays paused.
    - cancelled/failed: no write, left out of work_refs (history unchanged).
    - waiting_input/completed: still unavailable (not reachable in this scope).
  - Keep the coverage check and the replay behavior.
- F2 `v5_intake_work` has no control or lease columns, and `CREATE TABLE IF NOT EXISTS` cannot add them. Migration is out of scope.
  - Add new `v5_tsk_` tables (slot, lease, control, call, step, host budget, work budget, reservation) keyed by goal_id+revision.
  - A missing control row means no control.
  - The existing `state` text column takes running, paused, cancelled and failed.
- F3 `MemoryStore.search` rejects work_ref. Lookup must pass the Goal's stored session_id. Search and read run on an idle connection, never inside a TSK transaction.
- F4 The source index is per revision.
  - Required refs are origin plus brief.context_refs, which is already the coverage set.
  - Lookup results are optional dependencies added to the same index.
- F5 `MemoryStore.read` is not bound to a transaction. Admission must therefore recheck refs with the bound `source_gate` inside its own transaction.

## 1. Smallest connected path and API shapes

Each iteration runs on one lease, where n is the number of steps so far:

1. `claim` returns the lease.
2. `register_sources({work_ref,refs})` registers the required refs.
   - If a source is denied: `release(failed, required source stopped)` with an error event.
   - The work is not requeued, so it cannot spin.
3. `reserve_budget` with kind model and key `dumps([C15.reserve, lease_id, n, model])`.
4. The host reads the usable registered refs with `read(purpose=model_context)`.
   - Denied refs are excluded and named in the call input.
   - They are never served from a cache.
5. `admit_call` (transaction), then the mock runs outside any transaction, then `end_call` (transaction).
6. `begin_step` reserves a step. Only report and lookup are accepted; other actions return unavailable.
7. Record the step:
   - report: `finish_step(result_refs=[])`, plus a progress event carrying the summary.
   - lookup: the host calls `search({query, session_id: work session, limit<=50})`. `finish_step` stores the record refs and the truncated flag, registers the refs as sources, and writes a progress event.
8. Repeat from step 3, or `release(yield)`.
   - Bodies are reread for every call.
   - Steps persist Refs only.

`claim({runner_id})` returns one of:
- `{status:claimed, lease_id, work_ref, brief, grant, checkpoint, steps, pending_inputs:[]}`
- `{status:empty}`

Rules for `claim`:
- It takes the oldest queued Goal by rowid, sets epoch+1 and state running, and writes a state event.
- The same runner with an active lease gets that lease back with the current work_ref. No new lease and no epoch change.
- Another runner while the slot is occupied gets conflict.
- If the host budget is exhausted it returns limit and writes nothing.
- The host mints runner_id per process start, so a reopened host never inherits a lease.

`begin_step({key,work_ref,action})` returns a started Step. It requires:
- the current epoch;
- no active control;
- the call for index n has ended with outcome returned;
- the Action's refs are a subset of the refs supplied to that call (stored on the call row).

`finish_step` replays by step_id, and changed input is a conflict. It returns stale or denied if the epoch or control changed.

All errors use only the eight v5 codes.

## 2. Call admission versus control

The linearization point is the SQLite commit order (v5 section 5). No in-process coordinator lock is required. If one exists, it must never be held while the callable runs.

`admit_call({call_id,lease_id,work_ref,reservation_id,source_refs})` runs in BEGIN IMMEDIATE and checks:
- the lease owns the slot;
- work_ref matches on revision and epoch;
- state is running and no control is active;
- the lease has no unended call;
- the reservation is kind model, for the same work and not yet bound (it is bound here, which is the C15 consume);
- `source_gate(refs)` is available and the refs are a subset of the registered ones.

It then inserts the call row with status admitted. Errors are stale, denied, conflict, not_found and unavailable. call_id is `dumps([C15.call, lease_id, n])`, and an equal replay returns the same row.

A committed admission is not the same as the callable being entered. After the admit commits, the wrapper may reread control and skip entry, recording not_entered. Otherwise the call counts as running for every control decision.

## 3. Lease retry/release and observed cessation

The trusted mock invoker is the only path to the mock:

1. Commit the admission.
2. Run the mock under `try`/`except BaseException`.
3. From that termination path only, write `end_call({call_id, outcome: returned|raised|not_entered})` in its own transaction.

Rules for cessation:
- If the mock is threaded, end_call follows an observed join, never a timeout.
- No call_stopped boolean and no Expert self-report are accepted.
- If end_call hits a busy database, it retries a bounded number of times. After that the call stays visibly unended; cessation is never inferred.

`release({lease_id, work_ref, outcome: yield|paused|failed, reason})` returns `{work_ref, state, control_status: none}`.
- paused is accepted only when a pause intent is recorded; otherwise conflict.
- Unknown lease: not_found.
- Lease is not the current slot owner: denied.
- Goal or revision mismatch: stale.
- Any admitted call without end_call: conflict (call not ceased).
- An old epoch is accepted when the lease matches.

In the same transaction, release abandons started steps, frees the slot, computes the state (section 6) and writes one state event. It replays by lease_id, and changed input is a conflict.

After a reopen, an unended call blocks the slot: claim returns conflict and release returns conflict. There is no automatic clearing, no new call and no inferred provider termination. C13 recover stays unsupported. This proves only that the mock callable stopped.

## 4. Minimal MOD versus TSK ownership

A separate MOD raw-result ledger is not essential for this mock step.

TSK owns these as C13 execution-right metadata:
- the lease;
- the admission row (call_id, lease, index, reservation, supplied refs, epoch);
- the cessation outcome.

It stores no content. The mock output travels in memory to begin_step. If the host crashes, that output is lost and the call blocks the slot (no recompute). RUN keeps no persistent state.

These remain unmet and must be labelled as such: C15 call status, raw content and replay; model_id; interrupted; calls without a Goal. When MOD lands, its commit calls end_call. The TSK rows are not a substitute for MOD.

## 5. Durable finite host/work budget

Host identity:
- One ledger per database: `v5_tsk_host_budget`, kinds step, model and operation, each holding limit and used.
- Its lifetime is the database. There is no time window and no reset API.
- The constructor requires finite host_limits: int, at least 0, not bool, at most the SQLite maximum. A missing setting is a configuration error.
- A new setting changes the limit only and never resets used. used >= limit means exhausted.

Work budget: per goal_id across revisions, with limits taken from Grant.limits. Pause, resume, control and reopen never reset it.

`reserve_budget({key,work_ref,kind,role?})` returns `{reservation_id, remaining:{work, host}}`.
- It increments used for both ledgers in one transaction.
- The same key replays; a different input is a conflict.
- It returns stale or denied under the same rules as admission, and limit if either ledger is exhausted.
- kind operation returns unavailable.
- A reservation without a Goal returns unavailable unless it is implemented on the host ledger only.
- Reservations are never refunded (failed, raised, not_entered or unbound).

Zero or exhausted budgets:
- Work budget: limit, then release(failed) with an error event. The mock count stays 0.
- Host budget at claim: limit, no state change.
- Host budget mid-lease: release(yield) with a reason. The claim precheck stops this from spinning.

## 6. Source stop and draining precedence

A stop on running work sets epoch+1 and draining inside MEM's transaction. The slot stays occupied. Late results return stale, and the next admission is denied. Intents are stored separately: `stop_intent none|pause|cancel` and a `draining` flag.

The released state follows this order:
1. cancelled, if the work was cancelled;
2. otherwise paused, if a pause intent exists;
3. otherwise queued, if draining;
4. otherwise the runner's outcome (yield gives queued, failed gives failed).

This covers pause then stop, stop then pause, and stop then cancel, in either order.

Control commands compare goal_id and revision only:
- pause on queued: paused.
- pause on running: pause_requested, with no epoch change. It blocks admission and adoption.
- cancel on non-terminal work: cancelled, epoch+1, slot kept.
- resume on paused: queued.
- resume on running or terminal work: conflict.
- A repeated pause or cancel under a new key returns the current state.

After a requeue, a stopped required ref makes the next claim end in failed (section 1, step 2). Stopped optional refs are excluded. There is no retry spin and no cached body.

## Essential barrier tests

Use one connection per thread, Events for coordination, and no sleeps.

1. Pause commits before admit: admission denied, mock count 0, release gives paused.
2. Admit before pause:
   - control returns while the mock is held;
   - release before end_call is a conflict;
   - a late begin_step is denied;
   - release gives paused; mock count 1.
3. Admit, then pause before entry: not_entered, mock count 0.
4. Cancel a held call: cancelled and epoch+1 at once. Another runner's claim is a conflict until end_call and release.
5. MEM stop of a held call commits on another connection:
   - the late result is stale;
   - release gives queued;
   - the reclaim with a stopped origin fails once.
6. Stop then pause, stop then cancel, and pause then stop give paused, cancelled and paused.
7. A wrong lease is denied. An old-epoch lease owned by the runner releases and keeps the newer intent.
8. A raising mock is recorded as stopped, with no refund.
9. A reopen with an unended call stays blocked, with no clearing.
10. Lookup:
    - real MEM bodies and hashes reach the next call;
    - a stop between search and registration excludes the ref;
    - a stop after registration drains the work.
11. Zero work or host budget gives zero invocations. Usage persists across reopen and limit changes.
12. Replay and conflict for every API. An injected failure in a step, event or reservation transaction rolls back only that transaction.
13. A cancelled Goal sharing a stopped record does not block the stop. A mixed queued and running stop is atomic.

## Adopted corrections

- F1 through F5.
- Commit order is the linearization point.
- The lifecycle is admit / not_entered / end_call.
- Precedence: cancel, then pause, then draining, then the runner's outcome.
- Required versus optional sources.
- A per-database host ledger that never resets.
- runner_id is minted per process.
- No MOD ledger, with the gap labelled.

## Unfinished boundaries

- ask/answer/C04, change/attach, operations, ART/VER/complete, recover, C14 cursor writes, and invalidation of waiting_input/completed.
- MOD C15 storage.
- Work-less budget.
- Real models, GitHub, UI and runtime.
- CT-20 or whole-contract completion is not claimed.

## Planner note

Within this goal/scope:
- Freeze TSK02 with these corrections.
- Implementation: one isolated TSK owner over the new v5_tsk_ tables plus the extension to invalidate_by_refs.
- Integration: root mock driver and invoker, then the test list above.
- Review: independent review after author tests.
- No concurrent writes to shared files, no added approval gate, no network, authentication, cost or runtime changes.

## Verdict

REFINE
