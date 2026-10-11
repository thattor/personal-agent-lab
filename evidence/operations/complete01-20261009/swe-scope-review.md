REFINE

# SWE consultation — COMPLETE01/1 (Stage B), after Root disposition of Opus R1–R8

Reviewed COMPLETE01-SCOPE against `pal/tasks_v5.py`, `pal/mock_runner_v5.py` and `pal/memory_v5.py`. The scope correctly incorporates R1–R8 and matches the real seams; no architectural change, permission gate or redesign is needed. REFINE only pins binding details the text leaves open and one disposition split in the host seam. Stage A VER remains a separate in-progress dependency: this slice consumes only its frozen `inspect` contract and neither implements nor extends VER.

## Minimal architecture

1. `TaskStore.control` gains one closed-object branch: `command` must be exactly `{kind:'complete', verification_ref:{kind:'verification',id}}`; any other shape/kind is `invalid_input` before the transaction, as today.
2. `invalidate_by_refs` gains a completed branch.
3. `release` extends its terminal passthrough to completed/failed.
4. `MockRunner` gains a `verifications` collaborator and a finalization seam.

No new files, tables, MEM fields or mutable public setters. TSK receives `verification_inspect` via constructor using the same forwarding-closure cycle as ART (R7).

## complete: transaction and error precedence (frozen)

All inside `_transaction('control', key, data, op)`: canonical replay first, changed same-key input conflict, BaseException rolls back and propagates.

1. `_authority(work)` with exact epoch (R1); existing stale/denied/conflict precedence is preserved. The single-active-lease index binds the claim; no lease_id needed.
2. Missing `verification_inspect` → `unavailable`, checked after replay and authority.
3. `inspect` on this connection under the `_inspect_artifact` guards: savepoint, `in_transaction`, `total_changes` equality, `Result` re-parse; a trusted callback COMMIT cannot be undone. VER `not_found` → not_found. No VER SQL reads, no `get_by_key` authority.
4. Strict typed shape: exactly work_ref, ordered artifact_refs, checks, source_refs, status; malformed owner output or corrupt evidence → `unavailable`.
5. Different goal/revision → `conflict`; different epoch or any artifact-set mismatch (subset, reorder, duplicate) → `stale`; refs must equal `_artifact_set(work)` order exactly.
6. Check structure: exactly one check per immutable unique Condition ID in Brief order; empty stored conditions are corrupt → `unavailable`, never vacuous. Reasons are bounded strings; evidence_refs ⊆ (artifact_refs ∪ source_refs) with C09 kinds.
7. source_refs: record-only, required origin/Brief refs included, every supplied ref already registered; then `_gate` the union via MEM in this transaction — denied/unavailable keep their existing mapping.
8. Only after all TSK comparisons and gates pass: status `invalidated` → `unavailable` (owners disagree); valid unmet/unknown checks → `conflict`.
9. Calls-ended predicate: every lease call is returned/raised/not_entered; each returned call has a finished step; no step of the revision is started. Admitted calls, started steps and returned-unadopted output → `conflict`; unrecognized stored status → `unavailable`.
10. One commit: state `completed`, lease `active=0`, pause/drain cleared, exactly one `result` event carrying the ordered artifact refs plus the verification ref, and the replay receipt via existing `_save_replay`. Epoch unchanged; no budget refund or reservation.

Same-key replay after closure or source stop returns the original receipt and emits nothing; a new key on completed work reaches `_authority` and is denied.

## invalidate_by_refs completed branch (frozen)

- In the existing per-row scan, after the required-refs availability check and the `refs ∩ registered` test, branch `state=='completed'` before the state/`epoch==_MAX` rejection: emit one `progress` event per Goal to its own session with the fixed text and refs = stopped ∩ that Goal's registered set. Do not touch state, epoch, flags or the artifact set; never append to `affected`.
- The `{work_refs}` result continues to list only epoch-invalidated works. Confirmed against `memory_v5._callback`: it validates the list shape and never consumes the values, so no new MEM field or second engine is needed. Replay already gives once-per-key.

## release terminal guard

After the existing lease/active/matching/admitted-call checks, extend the state computation so `completed`, `cancelled` and `failed` are returned unchanged rather than recomputed from flags/outcome. A release after a committed complete is already denied on the inactive lease; this guard is defensive only. No terminal is ever reopened.

## MockRunner seam (frozen)

- `MockRunner(..., artifacts=ART, verifications=VER)`; `verifications` without `artifacts` raises ValueError at construction. `verifications=None` keeps current draft-only behaviour.
- The seam runs at entry after the existing started-step and `get_call` readiness checks, and again after each finished compose — always before any new inference.
- Trigger: the last finished step's action is compose and its artifact equals the tail of `get_work`'s `current_artifact_refs`.
- Sequence: read the exact current set via `get_work`; `verifications.verify` with key `dumps(['C09.verify',work,refs])`; if every check is met, `tasks.control` complete with key `dumps(['C10.complete',work,verification_ref])`. TSK revalidates all authority.
- Dispositions: non-MET (unmet/unknown) or complete conflict/stale/denied → fall through to the bounded step loop, carrying the verification result in the local response; it never releases or fails work by itself and never skips a needed step. Verify and complete calls use the existing three-attempt `persist` unavailable limit. Persistent verify unavailable → `yield_or_retain`. Persistent complete unavailable → retain the lease and return `unavailable`, never release: if complete committed, the lease is inactive and the next claim moves to another Goal; if not, active-lease reentry reaches the seam first and replays both canonical keys with no model call.
- Success response: `Result.success` with `status:'completed'`, work_ref, lease_id, the original C09 receipt (verification_ref and checks), finished steps, call_ids and the existing excluded-ref/step diagnostics. Verification refs never enter `result_refs` or model context.

## Tests to freeze before code

TSK on temporary SQLite MEM/TSK/ART/VER:

- compose → verify met → complete: completed state, inactive lease, cleared flags, one result event, stored receipt; same-key replay returns the original after lease close and after a later source stop.
- precedence: each authority failure; missing collaborator unavailable; VER not_found; different goal/revision conflict; old epoch and set mismatch stale; forged/malformed inspect output and corrupted evidence unavailable; valid unmet/unknown conflict; owners-disagree invalidated unavailable; stopped source denied; empty stored conditions unavailable.
- calls-ended: admitted call, started step, returned-unadopted output → conflict; corrupt status → unavailable.
- two-connection ordering: pause-before-complete conflict; complete-before-pause leaves pause/cancel conflict; cancel-first stale; drain stale.
- rollback: failure or interrupt after owned writes leaves no state, lease, event or replay row.

invalidate/release:

- stopping a source registered by completed work emits one progress event with the fixed text and intersected refs; `work_refs` is unchanged; VER status derives invalidated; same-key replay emits nothing.
- one source shared by completed and running works stops both uses atomically.
- release after complete is denied; the terminal guard never rewrites completed/failed.

MockRunner:

- seam fires at reentry and after compose only on the tail trigger; committed-lost response → next claim moves elsewhere; ambiguous response → retained lease, replayed keys, zero model calls; non-MET falls through, with normal bounded-loop and budget-exhaustion behaviour intact; `verifications` without `artifacts` raises.