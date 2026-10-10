REFINE

# Opus design consultation: COMPLETE01/1 Stage B scope

This is one consultation step on the supplied snapshot only: COMPLETE01-SCOPE, VER01-SCOPE, PAL-contracts-v5, `pal/tasks_v5.py`, `pal/mock_runner_v5.py` and `pal/contracts_v5.py`. The ART01 Opus review is background, not an instruction source. No commands were run.

This is not an acceptance review and makes no claim about code behaviour. VER Stage A is in progress separately, so any VER behaviour cited below is its proposed contract.

## Verdict

Value, ownership and boundary are right. The verdict is REFINE because eight seam details must be frozen before the TSK and RUN owners start. None of them widens scope or adds a permission gate.

## Value, split, contract, boundary

- **Value: confirmed.** Completion comes only from TSK re-reading typed current VER state. `report` and save stay non-completing (`TaskStore.begin_step` allows only report/lookup/compose).
- **Split: confirmed.**
  - TSK owns state, lease, events, replay and the comparison.
  - VER owns the record and its derived status.
  - RUN owns no data.
  - One wiring gap exists (R7).
- **Shared contract: confirmed in shape.** It is the C10 object command, the typed `inspect` and an unchanged C14 kind set. R1–R6 fix its precision.
- **Minimal boundary: confirmed.**
  - complete, the completed-history source stop (L1) and terminal-safe release (L2) must land together.
  - Without the L1 change, `TaskStore.invalidate_by_refs` returns unavailable for any completed Goal and aborts the whole MEM stop.

## Analysis

**Atomicity.** `TaskStore._transaction` already does three things:

- runs BEGIN IMMEDIATE;
- performs canonical key replay before the operation;
- saves the replay in the same transaction, rolling back on BaseException.

The complete operation can therefore write all of these in one commit: state completed, lease inactive, flags cleared, one `result` event, and the receipt. VER.inspect, ART.inspect and the MEM gate are all reads inside that transaction. Guard them like `TaskStore._inspect_artifact`: savepoint, `in_transaction` and `total_changes` checks.

The completed-history stop runs in MEM's transaction through `invalidate_by_refs`, so complete and stop serialize on the SQLite write lock. No mixed ordering is possible.

**Typed current VER vs historical replay.** VER `inspect` with `context(status)` accepts `completed` state (`TaskStore._verification_context`), so status stays derivable after completion. `get_by_key` must never be called by complete; the proposal is correct here.

**Fixed Conditions.**

- `Brief.from_json` already rejects empty conditions (`_brief_fields`); stored-empty is therefore unavailable.
- Duplicates parse successfully, so complete must recheck uniqueness, as `_verification_context` does.

**Notice meaning.** The current text, 'work sources invalidated' with kind `state`, would misdescribe a completed Goal whose state and epoch do not change. TSK registers every call source and lookup result (`_register`), not only VER dependencies. A notice can therefore fire for a source the verification never used. The notice must mean "a source registered for this completed work was stopped; the completion is historical". It must not mean that the completion was revoked. VER status remains the authority on whether the record is still valid.

**Idempotency.**

- Same key: original receipt, even after the lease has closed or a source was stopped.
- Changed input: conflict.
- A new key on a completed Goal reaches `_authority` with no active lease and returns denied. That is the existing precedence and acceptable.

**Pause/cancel ordering.** Commands serialize through BEGIN IMMEDIATE.

- Pause first sets `pause=1`, and complete then gets conflict from `_authority`.
- Complete first makes `TaskStore.control` pause/cancel/resume return conflict, because the state is no longer running/queued/paused.
- Cancel first bumps the epoch, and complete returns stale.
- A source stop on running work bumps the epoch and sets drain, and complete returns stale.
- After a fenced complete, RUN's existing `release('yield')` resolves to paused, cancelled or queued.

**Host reentry.**

- While the lease stays active, `claim` returns the same lease with no epoch bump. The epoch-bound verify key and the complete key then both replay.
- If complete committed but the response was lost, the lease is inactive. The next `run_once` claims another Goal; the completed history is durable, so nothing needs recovering.

## Necessary refinements

**R1 Epoch and shape.**

- The complete branch of `TaskStore.control` must use exact-epoch `_authority(work)`, not the `epoch=False` lookup used by user commands. PAL-contracts-v5 §3 says host results match revision and epoch.
- Validate the closed command object before the transaction: `{kind,verification_ref}`, kind `complete`, Ref kind `verification`.
- Check whether the collaborator is missing inside the operation, after replay lookup.
- Epoch equality with the single `v5_tsk_one_lease` binds the claim, so no lease_id is needed.

**R2 TSK truth first, VER second.** TSK compares the inspected result with its own stored data:

- `Brief.conditions` IDs in exact order, with uniqueness;
- `_artifact_set(work)` refs;
- its own required refs and registered sources;
- then `_gate` over the union.

Freeze the error precedence:

1. Authority: stale, denied or conflict.
2. VER not_found: not_found.
3. A different Goal or revision in the result: conflict, not stale.
4. A set mismatch: stale.
5. VER `invalidated` while every TSK-side check passes: unavailable, because the owners disagree.
6. Unmet or unknown: conflict.

**R3 Calls-ended predicate.** For every `v5_tsk_call` row of the lease:

- status must be returned, raised or not_entered;
- every returned row needs a step whose status is finished;
- no step of the revision may be `started`.

**R4 Completed source stop in `invalidate_by_refs`.**

- Branch on completed before the `epoch == _MAX` check.
- Leave epoch, flags and state unchanged.
- Write one event per completed Goal per key; replay already gives once-per-key.
- Use kind `progress` with fixed text that states the completion is historical.
- Restrict refs to the stopped refs that are in that Goal's registered set.
- Freeze what the result reports. If the MEM consumer reads `work_refs` as "invalidated", report completed Goals in a separate field.

**R5 RUN seam trigger and non-MET.**

- Run the seam at entry only after the existing started-Step and `get_call` readiness checks in `MockRunner.run_once`. Trigger it only when the last finished Step is a compose whose artifact is the tail of the current set. Run it again right after each compose finish.
- A non-MET result (semantic or source_fetched is always unknown in Stage A) must fall through to the normal bounded step loop. It must never release by itself. Otherwise yield→claim→verify becomes a zero-cost loop that never progresses, and it keeps head-of-queue `claim` on the same Goal.
- Budget exhaustion still fails a Goal as it does today. "No terminal failure" applies only to the verification outcome.

**R6 No release after complete.**

- A successful complete returns directly.
- A persistent ambiguous replay returns unavailable without calling release; the scope's retain choice.
- Document why a release is still harmless: it is denied for an inactive lease and cannot overwrite history.
- L2: `release` must also preserve completed and failed defensively, not only cancelled.

**R7 Wiring cycle.**

- VER needs `TaskStore.verification_context`, and TSK needs `VerificationStore.inspect`.
- Freeze the construction order, for example a forwarding closure that follows the existing ART pattern. Do not use a mutable public setter that could swap authority after init.

**R8 Mock composition.**

- `verifications` without `artifacts` is invalid configuration.
- Freeze the canonical keys: `dumps(['C09.verify', work, refs])` and `dumps(['C10.complete', work, verification_ref])`.
- Verification Refs never enter `result_refs`; this also avoids L3.

## Can wait

- A distinct "already completed" reason for pause or a re-complete after completion; conflict and denied suffice for now.
- The refs in existing running-Goal invalidation events, which currently list all stopped refs.
- waiting_input and change.
- Restart adoption and lease occupancy (L6).
- Verify Action (L3), verifier budget (L4) and artifact re-input (L7).
- Semantic evaluation, EXE source_fetched, UI and providers.
- Unknown earlier tasks and any external effects.

All of these stay excluded. No user permission gate is proposed.
