REFINE

# SWE scope review: VER01 deterministic verification (Stage A)

Review of VER01-SCOPE.md Stage A against PAL-contracts-v5 (C02/C09/C10/C11/C13/C15), the adopted Opus Stage A slice in `evidence/operations/art01-20261009/opus-milestone-review.md`, and the supplied owners (`pal/tasks_v5.py`, `artifacts_v5.py`, `memory_v5.py`, `intake_v5.py`, `contracts_v5.py`). Consultation only; no code. The scope is implementable and consistent with C09 and the Opus slice. The corrections below are minimal and required before implementation.

## Confirmed aligned

- VER owns only `v5_ver_` tables; TSK exposes a readonly same-connection callback shaped like `TaskStore.authorize_artifact_save`; no VER reads of other owners' SQL. Matches §2 ownership.
- `artifact_saved` is structural only (nonempty set, per-artifact hash/bytes/binding/revision/source availability via `ArtifactStore.inspect`); empty set is unmet; no semantic quality is smuggled in.
- `semantic` and `source_fetched` are `unknown` with fixed reasons; no MOD call, no budget. Matches C09 (`モデル利用不可ならunknown`) and C15.
- Epoch handling: verify/status compare the full `WorkRef`; artifact binding requires `(goal_id, revision)` equality while the stored artifact epoch may be older — consistent with `_finish_compose`'s revision binding and the §3 epoch-fence rule.
- `get_by_key` replay is history only, never completion authority; `inspect(connection, ...)` is the C10 seam. Matches the C09/C10 split.
- Monotonic derived status is justified: epochs only increase, `v5_tsk_artifact_set` is append-only, MEM stops are irreversible. No invalidation engine needed.

## Required corrections

1. **Callback shape.** Implement `TaskStore.verification_context(connection, request)`: a thin public wrapper calling `self._require_transaction(connection)` (same object, `isolation_level=None`, `in_transaction`) then a `@_public`-wrapped `_verification_context`, exactly like `authorize_artifact_save`/`_authorize_artifact_save`. `purpose` must be `'save'` or `'status'`; anything else is `invalid_input`.

2. **Purpose-specific authority.** `purpose='save'` uses `_authority(work)`: running state, current active lease for this goal, no pause/drain — failures map `denied` (no/mismatched lease) or `conflict` (not running/flagged). `purpose='status'` uses only `_current(work)` with `epoch=True` plus `_artifact_set` and `_required` — never `_authority`, or paused/queued/completed goals would wrongly return `conflict` instead of a factual snapshot. Corrupt stored rows (`brief_json`, `Brief`/`WorkRef` `ContractError`, `_artifact_set` rejection) map to `unavailable`, never `invalid_input`.

3. **Returned `source_refs`.** Return `_required(row)` only (origin + `Brief.context_refs`), not `_registered`. Artifact dependencies already arrive through `inspect`, and `_registered` grows with step results VER does not need; `_finish_compose` already forces artifact deps to equal the authorized call-source union.

4. **Exact verify error mapping.**
   - `invalid_input`: malformed object, wrong types, empty key, non-artifact Ref in `artifact_refs`, out-of-range revision/epoch.
   - `not_found`: unknown goal (context), unknown key (`get_by_key`), unknown `verification_ref`.
   - `conflict`: key replay with different canonical input; `artifact_refs` ≠ the exact ordered current set — subset, superset, duplicate, reorder are all `conflict`.
   - `stale`: revision/epoch mismatch from context; artifact inspect reports a different revision than current.
   - `denied`: save-purpose without running authority; MEM gate or ART inspect `denied`.
   - `unavailable`: `BEGIN IMMEDIATE` busy (catch `sqlite3.OperationalError` like `MemoryStore._mutate`, key not burned), MEM gate `unavailable`, artifact `unavailable`/`not_found` while listed in the current set, corrupt stored verification rows, callback contract violation, collaborator that wrote or replaced the transaction.
   - `limit` and `ambiguous`: never emitted in this stage.

5. **Check vs error boundary.** Any failed owner call aborts `verify` with the mapped error and saves nothing — never record a check `unmet` because evidence was missing/denied/corrupt. `unmet` is produced only by a fully evaluated `artifact_saved` on an empty set. `semantic`/`source_fetched` are always `unknown`, never `met`/`unmet` in Stage A.

6. **Record shape.** Mirror `v5_art_body`/`v5_art_replay`: `v5_ver_receipt(id PK, work_json, input_json, conditions_json, artifacts_json, checks_json, sources_json, observed_at)` plus `v5_ver_replay(key PK, input_json, result_json, verification_id)`. Store canonical `dumps(input)` for conflict detection as in `ArtifactStore.save`; `id_factory` mints `verification-*` ids; Ref kind `verification`. Conceptually the key namespace is `C09.verify` even though the table is VER-private.

7. **Inspect seam.** `inspect(connection, request)` requires `connection is self._conn`, `in_transaction`, `isolation_level=None`, raising `ValueError` like `ArtifactStore.inspect`; it writes nothing. `get_verification` uses `self._idle()` + `BEGIN`/rollback like `ArtifactStore.read`.

8. **Derived status.** Load and strictly validate the stored record (corrupt → `unavailable` result). Then `context(status)`: `ok` proceeds; `stale` → `invalidated`; `not_found`/`unavailable` → return that error, not a status. Require exact ordered-set equality vs stored refs, gate the union via `source_gate`, and `ART.inspect` each artifact bound to the stored hash/bytes/revision. Any denied record, added artifact, or stale `WorkRef` → `invalidated`. Any uncertainty → `unavailable` error. `ok:true` typed results carry `status` ∈ {`valid`,`invalidated`} only; the status value itself never encodes uncertainty.

9. **Replay after invalidation.** `get_by_key` and same-input `verify` replay return the original stored receipt verbatim even after the record is invalidated; the acceptance item must assert this is history. Document that C10 must never read `get_by_key`.

10. **No-completion guarantee.** `verify` never writes `v5_tsk_*` tables and calls no TSK mutator; Goal state is unchanged. C10 completion, Opus L1/L2 (completed-state invalidate and `release` overwrite), semantic evaluators, EXE evidence, and C11 verification dispatch stay out; they remain Stage B obligations gated on L1–L3.

## Meaningful tests (actual temporary SQLite, real MEM/TSK/ART/VER)

1. compose→finish→verify: `artifact_saved` met; state stays running/queued; `v5_tsk_usage` unchanged (no model/step spend).
2. DraftBrief with `semantic` and `source_fetched` conditions → `unknown` with fixed reasons, in stored Condition order with fixed IDs.
3. `verify` with `[]` on a goal whose set is empty → saved record, `artifact_saved` unmet.
4. `artifact_refs` subset/superset/duplicate/reorder → `conflict`; non-artifact kind → `invalid_input`; nothing written (`get_by_key` `not_found`).
5. Older epoch `work_ref` (e.g. after `invalidate_by_refs` bump or re-claim) → `stale`; older revision → `stale`.
6. `verify` while queued/paused/pause-flagged → `conflict`; after cancel → `stale`; goal with no active lease → `denied`.
7. Key replay: identical input returns a byte-identical receipt; changed input → `conflict`; after a second attachment invalidates the record, replay still returns the original receipt.
8. `get_verification` invalidation: new attachment → `invalidated`; MEM stop of selected and unselected deps → `invalidated`; epoch bump alone → `invalidated`.
9. Uncertainty: faulting `source_gate` → `unavailable` error (not `invalidated`); deleted/corrupt artifact → `unavailable`; hand-corrupted `checks_json`/condition ids in `v5_ver_receipt` → `unavailable` on read.
10. Pause flag with unchanged epoch/set/sources → `status` stays `valid`, proving a stopped control alone is not confused with changed evidence.
11. Same-transaction guards: `verification_context` on another or an idle connection → `ValueError`; a poisoned `artifact_inspect` that writes → VER's savepoint/`total_changes` guard (mirroring `ArtifactStore._guard`) → `unavailable` and full rollback.
12. Busy database (second connection holds `BEGIN IMMEDIATE`) → `unavailable`, key not burned, retry succeeds.
13. Fault after a `v5_ver_` INSERT (`FaultConnection` subclass) → `unavailable`, rolled back, key retryable; `KeyboardInterrupt`/`SystemExit` propagate with no partial row and an idle connection.
14. Inspect seam: `inspect` on an idle connection → `ValueError`; inside a caller `BEGIN` → same typed result as `get_verification`; caller still in transaction with zero `total_changes` delta.
15. Artifact saved under an earlier epoch of the same revision → still `met` after re-validation (revision-bound, epoch-tolerant).
16. Close/reopen the database: `get_verification` and `get_by_key` return identical typed data.
17. Stored record with reordered/missing/duplicate condition ids → `unavailable`.

## Non-goals restated

No model calls, no RUN verify Action (avoids L3), no C10, no completed-state stop (L1/L2 land together in Stage B), no C11 verification dispatch, no permission/budget path, no recovery engine. Acceptance proves determinism and persistence only, not product usefulness.
