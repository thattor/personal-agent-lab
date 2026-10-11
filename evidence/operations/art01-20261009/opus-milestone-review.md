ALIGNED

# Opus milestone review: ART01-store/1 + ART01-bind/1

This is a single review step by Opus 5.5. I ran no commands, tests or probes. Every statement below comes from the supplied snapshot:

- the contract documents
- `pal/*_v5.py`
- `tests/test_artifact_connection_v5.py`
- `verification.json` and `actual-connection-final.log`
- the Sol and Astra review notes

The following were not supplied, so I did not read them: `pal/events_v5.py`, `pal/artifact_content_v5.py`, `pal/artifact_integrity_v5.py`, the TSK owner tests and `full-integrated.log`.

## Verdict

The milestone is ALIGNED for what it claims: a mock compose produces a durable exact-byte draft, which is attached as one current artifact, with one reconnectable C14 progress event, while the Goal stays unfinished. I found no blocker within that scope. This is not a PASS for the whole of PAL, for VER, for completion or for the product.

## Role, contract and value alignment

- **Ownership matches PAL-contracts-v5 section 2 and the BINDING minimal boundary.**
  - ART-01 owns bytes, hash, receipt and provenance (`v5_art_*`).
  - TSK owns the current set (`v5_tsk_artifact_set`), state, events and lease.
  - RUN owns no persistent data and coordinates only through public methods.
  - TSK never reads ART SQL. It uses `artifact_inspect` on the same active connection (`TaskStore._inspect_artifact`).
- **C08 behaviour matches.**
  - Exact UTF-8 bytes are stored, and content over 1MiB returns `limit` (Astra fix).
  - The same key returns the same receipt; changed input returns conflict.
  - Each step gets one immutable save.
  - Saving neither completes nor attaches (`test_saved_bytes_reopen_and_receipt_do_not_complete_or_attach_work`).
- **C13 compose finish matches** (`TaskStore._finish_compose`).
  - The request needs exactly one artifact Ref and no error, truncated or excluded fields; otherwise invalid_input.
  - It rechecks authority, then inspects the artifact: wrong WorkRef is stale, wrong step is conflict, and the dependency set must be equal.
  - It rechecks the source gate.
  - Step, set row, record dependencies, progress event and replay are then written in one transaction.
  - Replay lookup runs before authority checks (`_transaction`).
- **C02 `get_work` matches.** It projects the set, and validation runs in both directions (`TaskStore._artifact_set`), which closes Sol's P2 finding.
- **Value matches.** Draft persistence and reconnect are real on temporary SQLite. Models never mark a Goal complete, and `report` is display-only.

## Evidence classes

These are kept separate.

1. **Mocked.**
   - The Expert is an in-process Python callable driven by `MockInvoker`.
   - There is no MOD or provider, and no remote cessation.
   - Cessation is proven only by the callback returning or raising.
   - Fault injection uses a test-only `FaultConnection` subclass.
2. **Actual temporary-file SQLite.**
   - Real `MemoryStore`, `TaskStore`, `ArtifactStore` and `MockRunner` share one file database.
   - The tests cover reopen, a second connection for stop and control, `BEGIN IMMEDIATE` contention, and Exception, KeyboardInterrupt and SystemExit after a write.
   - The supplied log shows 83 tests OK: 18 connection tests, 20 ART owner tests, and the content and integrity tests.
   - The 605-test full run and the 52 TSK owner tests are supported only by `verification.json`.
3. **Unproven product scope.**
   - Provider/MOD, PRI/UI, EXE, VER/C09 and C10 complete.
   - change, answer and waiting_input.
   - General restart recovery and a cross-process start lock.
   - Human usefulness.
   - CO task 917989 stays unknown and is not adopted.

## Assessment

- **Controls: sound.**
  - Pause or cancel before save returns conflict or stale, and no artifact is created.
  - Pause, cancel or stop after save keeps the saved history but adds no attachment and no event. The Goal ends paused, cancelled or queued respectively (`test_latest_pause_cancel_stop_after_save_cannot_attach_history`).
  - `release` keeps the latest control intent.
- **Conservative provenance: sound.**
  - `authorize_artifact_save` returns every record supplied to the model call, not just the ones the model selected.
  - ART stores that union and gates on it.
  - Finish registers the union in the TSK source index, so a MEM stop reaches the Goal.
  - Stopping an unselected source is tested both before and after attachment.
  - The milestone correctly calls this invalidation coverage, not proof that the bodies were read.
- **Receipt recovery vs attachment authority: sound.**
  - `get_by_key` is used only after save returns `unavailable`, never after conflict or invalid_input (`MockRunner.run_once`).
  - A recovered receipt still passes the full finish authority checks.
  - Persistent failure keeps occupancy and never calls the model again; the budget stays at exactly one model unit and one step unit.
- **Current-set validation: sound.**
  - Rows are appended in order and are unique per artifact and per step.
  - A corrupt or missing row returns unavailable.
  - Earlier work returns `[]`.
- **Closed artifact re-input: sound, partly evidenced.**
  - The TSK source index stays record-only.
  - `register_sources` with an artifact returns unavailable (tested).
  - `parse_model_action` only allows available records.
  - A finished compose Step lists its artifact in `step_sources`, so RUN excludes the whole Step (`excluded_step_ids` is tested).
  - An artifact in `Brief.context_refs` or `lookup.source_refs` is closed by code (the MEM gate returns unavailable for non-records, plus the membership check), but the supplied connection evidence does not exercise these paths.

## Blockers

None for this milestone.

Three non-blocking editorial refinements (P3, no rereview needed):

- ART01-MILESTONE.md joins identifiers to counts (`source2e8dfcf...`, `connection18`, `Rootfa40b66`). Adding spaces would make it easier to audit.
- The milestone says `TSK owner52`, while `verification.json` says `binding_owner_tests: 52`. Use one label.
- Mark the unsupplied full log and helper modules as host-verified, not review-read.

## Later obligations

None of these block this milestone, but each must land before the named capability.

- **L1, high, before C10.** `TaskStore.invalidate_by_refs` rejects any affected Goal whose state is not queued, running or paused, and returns unavailable. That aborts the whole MEM `stop_reference`. Once a `completed` state exists, stopping any source used by any completed Goal would fail.
- **L2, high, before C10.** `TaskStore.release` recomputes state from flags and outcome, so it would overwrite `completed` with queued or failed.
- **L3, before any verify Step.** `get_execution_context` rejects non-compose Steps whose results are not registered. A Step whose result is a verification ref would make the execution context permanently unavailable.
- **L4, before semantic VER calls.** `reserve_budget` accepts only the `expert` role, so a semantic VER call would need a verifier reservation (C15).
- **L5.** The artifact set is append-only. If an attached artifact's source is stopped, that revision can never complete until C10 change (a new revision) exists. This must fail closed, never filter the set.
- **L6.** A persistent local failure holds the single host lease (`v5_tsk_one_lease`) until a pause or cancel. Restart adoption (C13 recover and ART old-epoch adoption) does not exist yet.
- **L7.** Artifact re-input needs one-level kind dispatch plus registration of both the artifact and its record dependencies, as BINDING describes.

## Recommended next step: two staged slices

Stage two bounded slices and review each separately. Complete must not become reachable until L1 and L2 land in the same accepted change.

### Stage A: deterministic C09 in VER-01, without completion

- **One VER transaction.**
  - A new VER owner with its own `v5_ver_` tables and tests.
  - TSK adds one read-only callback on the same connection, guarded like `authorize_artifact_save`. It returns the current WorkRef (revision and epoch), the stored Conditions and the exact ordered current set.
  - VER calls ART `inspect` for each artifact and the MEM gate on the dependency union, all inside that transaction.
- **Input rules.** `artifact_refs` must equal the exact current set; a mismatch is conflict and a changed WorkRef is stale.
- **Check outcomes.**
  - `artifact_saved`: met only from inspected hash, bytes and WorkRef revision with usable sources. An empty set is unmet.
  - `source_fetched`: unknown, because there is no EXE yet.
  - `semantic`: unknown with a fixed reason. This slice makes no MOD call and spends no budget.
  - Unknown never counts as met, and a later evaluator's unavailable or failed result must also map to unknown.
- **Storage.** Store a typed record (WorkRef, condition IDs, ordered refs, checks, source union) with key replay. Replay is history, not authority.
- **`get_verification`.**
  - It derives `valid|invalidated` read-only from the current WorkRef, the exact set and the source gate.
  - Those inputs only move forward: epochs increase, the set is append-only, and stops are never undone. So the derived status is monotonic, and no invalidation engine is needed.
- **Actual temporary-SQLite tests.**
  - compose then verify gives met;
  - a Goal with a semantic condition gives unknown;
  - a second attachment invalidates the earlier record;
  - a source stop gives stale or invalidated;
  - reopen;
  - rollback after a fault following a write.

### Stage B: C10 complete together with completed-history source stop

These parts are combined because none of them is safe alone.

- **`complete{verification_ref}`.**
  - One TSK transaction reads the typed VER result through a guarded callback.
  - It requires running state, the current lease, no pause or drain, the exact WorkRef and set, every mandatory check met, and available sources.
  - It then marks the Goal completed, closes the lease, writes one `result` event and saves replay.
  - A change gives stale; unmet or unknown gives conflict.
  - Pause and complete are ordered as in section 5 and CT-08.
- **Completed-history source stop (L1).**
  - Completed Goals keep their state and epoch in `invalidate_by_refs`.
  - They get one notice event, and the stop itself is not aborted.
  - Verification then reads invalidated, and ART reads return denied or `usable:false`.
- **Release fix (L2).** `release` must not overwrite a terminal state.
- **RUN.**
  - After a finished compose, the host triggers verify within the same lease epoch and completes only when every check is met.
  - A model `verify` or `report` never completes a Goal.
  - Record this as a SOL coordination choice. The model verify Action stays unavailable, which avoids L3.
- **Tests.** CT-08, CT-11 and CT-17; complete followed by a stop on another connection; reopen.

This review proposes no code, no permission, provider or paid fallback, no second state engine and no recurring human gate. It is technical advice only.
