ALIGNED

# VER01 milestone candidate review: source fab7c77

Scope: an independent read-only review of the supplied file snapshot for candidate fab7c77bb4e8ece6b094e7b96c9f7194c04e3d53 (task base a189deb). This note is the only edit. It does not approve an owner, add a permission gate, or activate anything.

## What I did not do

- I ran no tests and executed no commands.
- I did not recompute the source_sha256 values in verification.json.
- I cannot prove that the supplied bytes equal fab7c77. I assume the coordinator supplied that source.

The following are supplied evidence, not product proof:

- **Host receipt:** 650 tests, exit 0, 24.227 s, temp SQLite/loopback, not CI.
- **Focused run:** 45 tests.
- **Sol rereview:** APPROVE with 45 tests on fab7c77.
- **Astra review:** APPROVE with 8 tests.

The following were not supplied, so their content is receipt-supported only:

- full-integrated.log
- tests/test_verification_v5.py
- tests/test_verification_context_v5.py

tests/test_verification_integrity_v5.py depends on the unsupplied `test_verification_v5` fixtures (`synthetic_context`, `synthetic_artifact`, `saved`). I could read its assertions but not its doubles.

Astra's TSK-context approval names source 3f37f78, not fab7c77. Sol's fab7c77 scope says it covers the 'actual consumer', so the TSK context code at fab7c77 is covered by Sol and by the receipt, not by Astra.

## Intended value

The candidate delivers what VER01-SCOPE promises:

- A saved draft set is checked against the immutable host Conditions and the exact current artifact set.
- The result is persisted once as a typed, replayable record.
- A current-status read separates a historical MET from currently valid evidence.
- Nothing completes a Goal. The connection test asserts that state stays non-completed and that budget usage is unchanged after verify.
- semantic and source_fetched are always `unknown` with fixed reasons (`pal/verification_v5.py:_checks`). There is no model, provider or EXE involvement.

## Owner separation

`pal/verification_v5.py` issues SQL only against `v5_ver_body` and `v5_ver_replay`. Every other fact comes through trusted callbacks on the same connection, each wrapped by `_guard`:

- TSK: `verification_context`
- ART: `inspect`
- MEM: `source_gate`

There are no TSK or ART table reads and no TSK state mutation. The TSK side (`pal/tasks_v5.py:_verification_context`) behaves as follows:

- It is readonly.
- It applies `_authority` only for `save`.
- It applies `_current` with epoch matching for `status`.
- It returns only required origin/Brief refs.
- It reuses the bidirectional `_artifact_set` validation.

This matches the frozen SWE disposition.

## Historical versus current

- **`get_by_key`** returns only the original receipt. It is still re-validated against the stored body via `_receipt_from_row` and `_stored`, so corrupt history is `unavailable`, not trusted.
- **`get_verification`** owns a short deferred read transaction and always rolls back.
- **`inspect`** requires the exact active caller connection, opens no transaction, and returns the same typed `{work_ref, artifact_refs, checks, source_refs, status}`.

The C10 seam therefore exists, and no code path lets `get_by_key` stand in for status. The connection tests show that replay of an old input after a source stop or epoch change returns the original receipt while status reports `invalidated`.

## Fixed Conditions and the whole ordered set

`_conditions` rejects:

- empty lists
- duplicate IDs

`_checks` emits exactly one Check per Condition, in stored order. Stored checks and the receipt are recomputed and compared on every read. A forged semantic `met`, a duplicate ID, or empty Conditions is therefore corrupt. The integrity test covers this, including the historical replay path.

`verify` demands exact list equality between the input and the TSK current set. Subset, reorder, duplicate and stale empty input all return `conflict`. The context set must itself be duplicate-free.

## Conservative dependencies

The stored `source_refs` is computed as follows:

1. Start with the required refs, in order.
2. Append each artifact's ART-reported dependencies, deduplicated in order.
3. Gate the result again through MEM inside the same transaction.

`_stored` recomputes this union and rejects any mismatch.

Because ART dependencies come from the authorized call sources, an unselected but supplied record still belongs to the union. The unselected-stop test confirms this. The union over-approximates rather than claiming which source was semantically used, which is the intended conservatism.

## Invalidation versus corruption

`_current_status` produces these outcomes:

| Condition | Result |
|---|---|
| Context `stale` | invalidated |
| Context `not_found` or `unavailable` | that error |
| Any other context error code | unavailable |
| Same-epoch `work_ref`, Condition or required-ref mismatch | unavailable |
| Set is a strict prefix-extension of the stored set | invalidated |
| Any other set change | unavailable |
| ART `denied` | invalidated |
| Any other ART error | unavailable |
| Changed ART metadata (full dict, including the immutable epoch) | unavailable |
| MEM `denied` | invalidated |
| Other MEM non-available | unavailable |

Pause with an unchanged epoch, set and sources stays valid, as the connection test shows.

All three Sol blockers are addressed in code and covered by retained probes:

1. Corrupt same-revision context: `test_impossible_same_revision_context_changes...`
2. Changed immutable ART epoch: `test_artifact_epoch_cannot_change...`
3. Empty Conditions: `_conditions` and `test_empty_conditions_and_forged_checks...`

Under the scoped monotonic model (epochs increase, sets append, stops are permanent), the derived invalidation is monotonic.

## Failure, interrupt and transaction ownership

`verify`:

- Owns a single `BEGIN IMMEDIATE`.
- Performs key replay first.
- Guards id minting before any VER write.
- On an ordinary exception, rolls back and returns `unavailable`.
- On BaseException, rolls back and re-raises.

`_guard` releases its own savepoint on success. On failure it rolls back to that savepoint and releases it, without touching the caller's outer work. It also detects a replaced transaction or a changed `total_changes`.

`inspect` never commits or rolls back the caller's transaction. The connection test shows that a mutating callback yields `unavailable` while the caller's own write survives.

The after-INSERT RuntimeError, KeyboardInterrupt and SystemExit tests leave no key on reopen. The documented limit is correct: a trusted collaborator's COMMIT cannot be undone. The id-factory probe shows this is detected before VER writes rather than hidden.

## Concrete current-scope blockers

None found in the supplied VER01 scope.

## Non-blocking observations

None of these require redesign.

1. **Status precedence masks co-occurring corruption** (`pal/verification_v5.py:_current_status`). It short-circuits to `invalidated` on context `stale`, on a legitimate append, or on the first ART `denied`. It does so before checking the integrity of the remaining stored artifacts. Simultaneous corruption can therefore be reported as `invalidated` rather than `unavailable`. Both outcomes are non-valid, and COMPLETE01 already treats an unexplained `invalidated` as owner disagreement. This is diagnostic precision, not a safety hole. A one-line precedence comment or a test would make the choice explicit.
2. **Pre-existing TSK debts belong to frozen COMPLETE01 work, not this milestone:**
   - `pal/tasks_v5.py:_inspect_artifact` does not clean its savepoint on failure.
   - `pal/tasks_v5.py:invalidate_by_refs` returns `unavailable` for `completed` rows.
   - `_verification_context` accepts `waiting_input`, which is otherwise unsupported.
3. **Provenance wording.** The milestone attributes TSK-context approval to Astra, but that approval is on 3f37f78. Pairing it with the Sol fab7c77 scope, as the milestone already does, is accurate. Readers should not read Astra's approval as fab7c77-exact.

## Remaining product gap

COMPLETE01 is frozen and in isolated implementation. This review does not call it complete or treat it as a new gate. VER01 remains a deterministic, local storage-integrity verification. The following are still unmet:

- C10 completion together with completed source-stop history and terminal-safe leases (the COMPLETE01 slice)
- semantic evaluation and model-verifier budgets
- real source fetching via EXE
- artifact re-input
- general restart recovery
- PRI, provider and UI
- full v5 activation
- personal usefulness

Earlier unknown calls remain untouched. Nothing here activates UI, providers, semantic models or retries.
