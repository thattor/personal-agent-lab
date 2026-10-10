REFINE

# SWE-2 High scope consultation — ART01-store/1

Assessment of ART01-SCOPE.md against C08/C11/C13, TSK02-SCOPE and the existing
v5 owners/helpers at base 2aaca0a. The design is sound and consistent with the
codebase's established transaction, replay and callback patterns. No structural
contradiction found. Five minimum corrections/clarifications are required before
dispatch; all are contract pinning, not scope change.

## What is already aligned

- **Strict C08 shape**: `save({key,work_ref,step_id,content,media_type,source_refs})`
  -> `{artifact_ref,hash,bytes}` matches C08 exactly. `artifact_ref` must be a
  Ref JSON `{'kind':'artifact','id':str}` (consistent with `work_ref` JSON in
  C03 receipts); `hash` is the lowercase sha256 hex from `prepare_content`;
  `bytes` the exact UTF-8 count. `media_type` is limited to the C08 enum by
  `prepare_content`, which also enforces the inclusive 1 MiB limit — reuse it
  unmodified and map `ArtifactContentError.code` to `invalid_input`/`limit`
  with fixed messages (no input or exception text in errors).
- **Key replay before authority**: matches the existing `IntakeStore`/`TaskStore`
  pattern (`_lookup_replay` inside `BEGIN IMMEDIATE`, before authority checks).
  Same canonical input returns the stored receipt even after source stop; a
  different input under the same key returns `conflict`; a rolled-back attempt
  leaves no replay row, so failed requests never burn the key. The replay row,
  artifact row and dep rows commit atomically.
- **Immutable BLOB + readback**: store content as a BLOB plus sha256/byte_count/
  media_type/work_ref/step_id/canonical input. `read` must run
  `check_bytes(body, stored_sha256, stored_count)` inside its read transaction
  and map any non-`met` status, unparseable stored metadata or UTF-8 decode
  failure to `unavailable` — never repair, never trust a text mirror.
- **Same-connection read-only TSK callback**: `TaskStore._transaction` opens
  `BEGIN IMMEDIATE`, so the callback must not. Reuse the proven wrapper:
  `SAVEPOINT`, call, verify `connection.in_transaction`, `RELEASE`, compare
  `connection.total_changes`. The TSK-side method must additionally enforce
  `connection is self._conn` (mirroring `_require_transaction`); a foreign
  connection is a programmer error. Callback `Exception` -> bounded
  `unavailable`; `BaseException` -> rollback and propagate.
- **Record-only conservative union**: the callback's union must be built from
  `v5_tsk_call.sources` of the call that produced the started compose step
  (found via `step.call`), not from `compose.source_refs`. Since
  `parse_model_action` at `begin_step` already enforces
  `action.source_refs ⊆ call.sources`, the union naturally contains every
  request ref and typically exceeds it — which is the intended anti-omission
  property. Validate the returned value as a closed object `{source_refs:[Ref]}`,
  nonempty, containing all request `source_refs`, every member `kind=='record'`;
  otherwise `unavailable` (non-record deps are out of this slice). Then re-run
  `source_gate(connection, union)` in the same transaction; outcomes map
  exactly as `GATE_OUTCOMES` (available/not_found/denied/unavailable).
- **Ordering**: a MEM `stop_reference` commit that lands before the save's
  `BEGIN IMMEDIATE` is seen by `authorize_save` (epoch+1/drain -> stale or
  conflict) and by the gate (denied). A save that commits first leaves durable
  history; the later stop fences it at read time — `model_context`/`verification`
  -> `denied`, `user_view` -> `usable:false`; `not_found`/`unavailable` ->
  `unavailable` for every purpose.
- **Per-step uniqueness**: explicit `SELECT ... WHERE step_id=?` before insert;
  an existing row under a different key -> `conflict`. A `UNIQUE(step_id)`
  column remains as backstop. Per-step, not per-work: later steps may each save.
- **Interruption**: `except Exception -> rollback -> unavailable`,
  `except BaseException -> rollback -> raise`, matching `IntakeStore._mutate`/
  `TaskStore._transaction`.
- **Honest verification split**: CO unit tests on `:memory:` cover logic only;
  root independently verifies real temp-file reopen and both connection orders
  (stop committed on a second connection between save and read; replay after
  close/reopen). Keep the two evidence sets separated in the return.

## Required minimum corrections

1. **Callback name inconsistency.** The signature block says `authorize_save`;
   the Integration section says `authorize_artifact_save`. Pin one: recommended
   `TaskStore.authorize_artifact_save(connection, request)`, injected via the
   existing constructor kwarg name `authorize_save` at wiring time.
2. **Pin the callback's failure mapping** (currently unspecified):
   `Result.failure` codes are preserved verbatim to the save caller.
   - unknown `step_id` or no current work row -> `not_found`
   - goal exists but revision/epoch mismatch (incl. post-invalidation epoch)
     -> `stale`
   - no active lease, or `call.lease != active lease.id` -> `denied`
   - request `source_refs` not subset of the producing call's `sources`
     -> `denied` (mirrors `admit_call` membership failure)
   - work not `running`, pause/drain flags set, step status not `started`,
     call status not `returned`, or canonical action mismatch -> `conflict`
   - missing call row, non-record union member, malformed internals ->
     `unavailable`
   The action check is canonical: compare `dumps(provided action)` with the
   stored `step.wire.action` (`{'kind':'compose','content','media_type',
   'source_refs'}`), which prevents saving content that differs from the
   model's actual compose output.
3. **Pin `get_by_key`**: strict input `{key}`, idle connection, returns the
   identical value object `save` returned (`{artifact_ref,hash,bytes}`) from
   the replay row, or `not_found`. No authority or gate checks — it is a
   historical recovery receipt (C13 pattern), and read authority stays with
   `read`/`authorize_save`.
4. **Pin `read` details**: strict `{ref}`; `ref.kind != 'artifact'` ->
   `unavailable`; absent row -> `not_found`; output keys exactly
   `{ref,content,media_type,hash,observed_at,work_ref,source_refs,usable}`
   with no `version` key; `observed_at`/`work_ref` are the stored historical
   values; `usable` reflects the current gate outcome over the stored union
   (available -> true; denied -> usable:false for `user_view`, `denied` error
   otherwise; not_found/unavailable -> `unavailable`). Invalid `purpose` ->
   `ValueError` programmer error (same as `MemoryStore.read`).
5. **Acknowledge the compose-step dead end explicitly.** Verified against
   `tasks_v5.py`: a started step blocks the next `admit_call` (`conflict`)
   and blocks an unfenced `yield` release (`conflict`, since the returned
   call's step is not `finished`). With `finish_step` refusing compose this
   slice, the only exits are `release(outcome='failed')` or a fenced release
   after pause/cancel/source-stop — both abandon the started step. This is
   correct conservative behavior, but the scope should state it plainly: the
   connected test's terminal for the compose path is a `failed` (or fenced)
   release, not `yield`; after reclaim the step index is consumed, the
   artifact remains durable and key-replayable, and its preserved
   WorkRef+step_id binding is what a later attachment slice will recover.
   No new mechanism (no ad-hoc finish, no auto-abandon) is needed or allowed.

## Suggested public surface (for dispatch precision)

```python
ArtifactStore(connection, *, authorize_save, source_gate, id_factory=None, clock=None)
save(request: dict) -> Result            # {'key','work_ref','step_id','content','media_type','source_refs'}
get_by_key(request: dict) -> Result      # {'key'}
read(request: dict, *, purpose: str) -> Result  # {'ref'}, purpose in model_context|verification|user_view
```

Internal save order: strict parse + `prepare_content` (pre-transaction) ->
`_require_idle` -> `BEGIN IMMEDIATE` -> replay lookup -> step_id uniqueness ->
savepoint-wrapped `authorize_save` -> validate union -> savepoint-wrapped
`source_gate` -> mint id -> INSERT artifact + deps + replay -> `COMMIT`.
Host key: `dumps(['C08.save', work_ref, step_id])`; canonical input is the
normalized full request. Tables are `v5_art_` prefixed only (own replay table;
no schema change to existing tables).

## Test obligations worth restating

Exact empty/Unicode/newline/1 MiB-inclusive content; replay-after-stop returns
receipt while `read` denies; changed-key-input and same-step-different-key
`conflict`; wrong step/work/action; union exceeds input `source_refs` (omit a
call-supplied ref from the compose action and confirm it is still stored and
still gates); stopped/not_found/unavailable gate; `id_factory` collision ->
`unavailable` with rollback; trigger fault after INSERT rolls back all rows;
`KeyboardInterrupt`/`SystemExit` mid-transaction propagate with full rollback;
metadata/body corruption -> `unavailable`; error payloads contain no body or
raw exception text. Root separately proves file-backed reopen and both
connection orders; `:memory:` cannot prove those.

## Limits of this slice (unchanged)

No finish/attach/VER/recovery, no non-record deps, no events or TSK writes from
ART, no filesystem I/O in transactions. A saved-but-unattached artifact is
historical data only; adoption requires a later authorized slice.
