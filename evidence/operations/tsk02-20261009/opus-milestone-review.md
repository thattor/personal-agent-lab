ALIGNED — TSK02/1 + RUN01/1 at ea2e8fa: the connected mock slice meets its frozen scope and keeps owner/contract boundaries. No finding blocks accepting this mock slice. F1 and F2 must be resolved in the next slice.

# Opus milestone design assessment — TSK02/1 + RUN01/1

- Base: ea2e8fa064cad188e4477d8b534692012083768a.
- Inputs: TSK02-SCOPE, PAL-contracts-v5, TSK02-IMPLEMENTATION, SPEC, DESIGN, the listed code and tests, and the two targeted logs.
- Line numbers come from the supplied snapshot and may be off by a line or two.
- No commands were run.
- This is a design-level assessment. Independent Sol code review runs concurrently. This note does not duplicate, gate or replace it.

## 1. Value and verdict reasoning

The slice delivers the Expert-lane half of three SPEC promises, in mock form:

- **Controls without waiting.** A user can pause, cancel or stop a reference while the Expert call is in flight, without waiting for it.
- **Stopped sources stay out of model context.** A stopped source leaves model context, together with any historical step derived from it.
- **Stale output is never adopted.** Late output from an old epoch is not used.

All of this is bounded by finite, non-refundable, lifetime budgets. The behaviour is proven against real MEM/TSK/C14 owners, with Events/barriers rather than sleeps (`tests/test_mock_execution_v5.py`).

This is enabling value, not user-visible value. No artifact exists, no Goal can complete, and the only terminal outcomes are failed or cancelled. That matches the milestone definition: the scope says the Goal remains unfinished. The slice is the correct prerequisite for INT-03, because compose, save, verify and complete need exactly this lease/epoch/admission/source-dependency substrate.

## 2. Boundary and contract conformance

- **Single canonical owner.** TaskStore extends IntakeStore (TSK-01/02/03 group) and writes only `v5_intake_*` and `v5_tsk_*` tables.
- **MEM stays within its own tables.** MEM writes only its own tables. It reaches TSK only through the exact `invalidate_by_refs` callback inside its own transaction (`pal/memory_v5.py` `_stop_locked`).
- **RUN holds no persistent state.** `pal/mock_runner_v5.py` owns nothing durable and hands the Expert a deep copy of the C12 object (lines ~189-196).
- **EventReader is read-only.** This preserves the C14 ownership split.
- **TSK never reads bodies.** It only gates through the injected source gate. Bodies are reread fresh before each call (runner `_read_context`, ~101-113). No copied body is stored (`finish_step` stores refs only, `pal/tasks_v5.py` ~435-445).
- **No transaction spans the callable.** Every mutation is its own BEGIN IMMEDIATE (`_transaction`, ~104-118). The connected tests assert no open transaction during the callable.
- **C13 semantics are honoured:**
  - claim bumps the epoch;
  - control checks the revision and ignores the epoch (~456);
  - release precedence is cancelled → pause → drain → outcome (~520-521);
  - release from an old owned epoch is allowed but cannot adopt output;
  - the R-02 source-usage set is held by TSK. Lookup refs are registered at `finish_step` (~435) and therefore become invalidation coverage.
- **Budgets follow C15/§6:**
  - one lifetime ledger per Goal (across revisions) plus a host ledger;
  - no refunds;
  - a limit change updates the ceiling only (~88-89);
  - claim refuses an exhausted host budget (~238-240);
  - a model reservation needs step headroom (~190-191).
- **Transitive provenance holds by construction.** A historical step is passed to the Expert only if its provenance ⊆ the refs actually read (runner ~164-175). The next call's supplied refs are exactly those reads, so derived summaries cannot outlive a stopped source. See F5 for the caveat.

## 3. Findings

### Carry-forward conditions (fix in the next slice, before any completion path)

**F1 — The runner turns transient errors into terminal Goal failure.**

- `failed()` (mock_runner ~143-144) releases with outcome `failed` for every non-ok result: context, register, read, reserve, invoke, begin_step, search and finish_step (~149-225).
- SQLite busy surfaces as `unavailable` (tests use timeout=0), so lock contention or one malformed mock output permanently fails the Goal.
- Contract §5 and C13 reserve `failed` for budget exhaustion or unresolvable conditions.
- A latest control intent still wins at release, so safety is intact. The issue is liveness and user-visible outcome.
- TSK also forces this choice: once output has returned, ordinary `yield` is rejected (~510-514), so the runner can only say `failed`.
- Recommended fix:
  - Before admission, `unavailable` → yield.
  - After output has returned, retry begin_step/finish_step a bounded number of times with the same input, as `_end` already does (~34-40). Their replay keys make this safe.
  - Reserve `failed` for `limit`, required-source denial and invalid model output.
- Related: `MockInvoker._owned` never releases a call_id (~48-51). Once admission fails, retry within the same process conflicts. Revisit this together with the retry policy.

**F2 — Source gating is record-only, and invalidation has no completed/artifact rule.**

- `MemoryStore.source_gate` returns `unavailable` for any non-record kind.
- `finish_step` and `admit_call` gate every ref through it (tasks ~330, ~420, ~425-431). An artifact or receipt ref in result_refs would therefore roll back the step.
- `invalidate_by_refs` aborts the whole MEM transaction if any matched work is not queued, running or paused (~550-551).
- Once `completed` is reachable, stopping any source used by a completed draft would make the user's forget fail with `unavailable`. C05 instead requires that history is not rewritten and that the stale source is displayed.
- Neither issue is reachable now, but both sit on the critical path to a saved verified draft.

### Accepted limits (consistent with scope; record, do not fix now)

**F3 — Orphaned leases, not just orphaned calls, block the single slot.**

- If a process crashes after claim but before admission, the lease stays active. A fresh runner_id gets `conflict` (~229-232), and no API enumerates or releases the old lease.
- The scope covers this under recover-unavailable. The practical consequence is still worth stating plainly: this composition must not run against any persistent DB until C13 recover exists.

**F4 — The no-retry policy is enforced by RUN, not TSK.**

- After a `raised` call, TSK allows `yield` (~510 only checks `returned`). Re-claiming then admits a new call at the same step index under a new lease.
- Model budget still bounds this, because there are no refunds. Today the runner chooses `failed`.
- A future real RUN must make this choice explicitly. It is not a TSK guarantee.

**F5 — The transitive provenance guarantee is runner-side.**

- `admit_call` checks required ⊆ supplied ⊆ registered (~322). It cannot know which historical steps the runner placed in C12.
- A future RUN must preserve the rule from §2: step provenance ⊆ refs read for this call.
- The same rule must carry into artifact source_refs when compose arrives.

**F6 — The execution-context read is non-transactional, and some metadata is mock-only.**

- `get_execution_context` (~253-270) is a multi-statement read outside a transaction, so it can observe interleaved commits. Admission regates the result, so this is metadata only and acceptable.
- The lookup progress event text is JSON metadata (~442), not user prose.
- The `excluded_refs`/`excluded_step_ids` keywords are mock-only and must not leak into the real C12 wire format.

**F7 — `end_call` is not bound to its lease.**

- `end_call` (~338-351) accepts any call_id from trusted host code.
- This matches the scope's trusted-wrapper boundary. Persisted cessation remains a host assertion, not proof of remote termination, as the implementation note states.

No finding shows MEM, RUN or the Expert gaining canonical write capability, model output bypassing host validation, or a broken contract shape.

## 4. Explicitly unmet, not defects

The following remain outside this slice:

- MOD-01 raw-result ledger, and C13/EXE recover and recomputation;
- C04/C10 ask, answer, change and attach;
- ART-01, VER-01 and C10.complete;
- PRI turns and UI;
- operation budgets and EXE/GitHub;
- real providers and activation;
- human usefulness evaluation;
- product completion.

`get_work` still returns `current_artifact_refs: []` and `open_questions: []` (intake_v5 `get_work`). This is correct for the slice.

## 5. Test-evidence limits

- **Supplied evidence:** only two targeted logs.
  - `host-author-final.log`: 34 tests (test_tasks_v5), OK in 0.160s.
  - `connected-final.log`: 14 tests (test_mock_execution_v5), OK in 0.105s.
- **Commit binding:** neither log records the command, interpreter, commit SHA or timestamp. Their link to ea2e8fa rests on Root's statement.
- **Missing logs:** the `/private/tmp` logs named in the implementation note are not in the snapshot.
- **Full suite:** Root's report that all 531 tests pass at this source is reported, not seen.
- **Unseen module:** `pal/sanitize` is imported by the connected tests but was not supplied.
- **Paths with no visible coverage:**
  - the runner's mid-lease host-budget `yield` branch (runner ~180-181); the zero-host test exercises only claim refusal;
  - work budget exhausted after one or more successful steps;
  - transient `unavailable` handling in the runner (F1);
  - call_id reuse after a failed admission;
  - real cross-process crash or kill; all concurrency is threads in one process with barriers;
  - multi-revision behaviour, which is unreachable in this slice.
- **Authorship:** the 34 host tests are author-written. The implementation note records an earlier case where author tests mirrored a wrong signature. The connected MEM→TSK test and the BaseException regressions address that class of error, but independent confirmation belongs to Sol's concurrent review.
- **What the tests do and do not prove:** they demonstrate mechanism-level control, fencing, source-stop and budget properties on isolated temporary SQLite. They do not demonstrate provider behaviour, UI, recovery or user value.

## 6. Recommended next bounded slice

The smallest dependency toward a saved verified draft is a mock compose → saved draft slice (ART01/1 plus the TSK/RUN compose adoption). It stops before verification.

1. **Compose adoption.** TSK `begin_step` accepts `compose`, with source_refs ⊆ the call's supplied refs (already enforced by `parse_model_action`).
2. **Saving the artifact.** RUN calls the C08 save outside any TSK transaction, with a key derived from step_id. ART checks the current WorkRef and source availability in its own transaction and stores immutable content plus a hash, with a 1 MiB limit.
3. **Binding the artifact.** `finish_step` binds the artifact_ref into a TSK-owned current-artifact set. `get_work.current_artifact_refs` reads that set.
4. **Kind-dispatching source gate (F2).** Records go to MEM and artifacts to ART, so admission and finish can gate artifact refs. The artifact's provenance is the closure of the call's supplied refs (F5).
5. **Source stop on a non-terminal work holding an artifact.** Keep the current queued/running/paused rules, and mark the artifact source-stale for display.
6. **Runner error mapping (F1).** Ship the fix in the same RUN change.
7. **Contract tests:**
   - CT-03 up to `C08`, with no completion;
   - CT-11 partial: a source stop after save makes the artifact historical;
   - crash between ART save and `finish_step`, recovered via ART `get_by_key` with no duplicate artifact (no general recover).
8. **Excluded from this slice:** VER, complete, MOD, recover, PRI/UI, EXE, real providers and live DB migration.

The following slice, VER01/1 plus C10.complete, must then:

- add deterministic `artifact_saved`/`source_fetched` checks;
- add a mock verifier reservation path, because `reserve_budget` currently accepts only role=expert (~293);
- return `unknown` for semantic conditions without a model, never PASS;
- implement complete against the stored verification, the current artifact set and source availability;
- define the completed-state invalidation rule (F2) before `completed` becomes reachable.

That slice yields the first saved verified mock draft. C13 recover (F3) is required before any activation, but it is not on that mock critical path.
