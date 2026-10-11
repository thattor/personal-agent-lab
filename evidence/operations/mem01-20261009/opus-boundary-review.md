# MEM01 boundary review (Opus consultation)

Verdict: **REFINE**

Read: MEM01-SCOPE.md, PAL-contracts-v5 (C05, C06, C11, C14, s5, CT-15/20), TSK01-SCOPE.md,
boundary-analysis.md, pal/intake_v5.py, contracts_v5.py, sanitize.py. Design text only;
nothing was run, tested or verified.

## Reasons

1. Ownership matches v5: MEM owns bodies and availability. TSK owns work, sources and
   events. One SQLite transaction is used (s8). No v5 scope change is needed.
2. The scope is not dispatchable yet. Callback shapes, replay identity, search bounds
   and work-context search are still explicitly unfrozen.
3. intake_v5.py has no source-dependency index and only a private `_append_event`.
   Stop cannot find dependent work or emit a public C14 event without TSK changes.
4. Denying future intake alone fails C05/CT-20 for existing work.

## Recommended scope: connect now, not record-only

Intake can only create `queued` work. Queued invalidation therefore covers every state
this slice can produce. Add it now together with public C14 append_event. Record-only
preparation would save little and keep a known activation blocker.

### TSK changes (SOL, pal/intake_v5.py)

- create also writes `v5_intake_source(goal_id, revision, kind, id)` rows for the
  origin and context_refs, inside its existing transaction.
- `append_event(conn, *, key, session_id, work_ref, kind, text, refs) -> event_id` has
  the C14 shape, and work_ref may be None. It is idempotent per key: equal input
  returns the same id; different input raises conflict.
- `invalidate_by_refs(conn, *, key, session_id, refs) -> tuple[WorkRef, ...]`. For each
  current work whose source set intersects refs:
  - queued: epoch+1, state stays queued (v5: queued is re-evaluated), and one `state`
    event with the new WorkRef and matched refs, keyed `f'{key}:{goal_id}'`.
  - any other state (running, paused, waiting_input, terminal): raise Unsupported, so
    the whole stop fails closed.
- Both callbacks are transaction-bound. They require `conn is` the store connection and
  `conn.in_transaction`. They never BEGIN, COMMIT or ROLLBACK, and they raise on any
  failure.

### MEM transaction ownership (pal/memory_v5.py)

`sanitize_text(text: str) -> str` is pure and deterministic; the host wraps
`pal.sanitize.sanitize`. It is called before BEGIN. A non-str result or an exception
gives a bounded error with no writes.

`stop_reference({key, source_ref}, *, session_id)`:

1. Validate without writes; the ref kind must be record.
2. BEGIN IMMEDIATE. busy or locked returns unavailable.
3. Replay lookup `('C05.stop_reference', key)`. Equal canonical input returns the stored
   Result with no callbacks. Different input returns conflict.
4. A missing record returns not_found, and the key is not saved.
5. If the record is available: mark it stopped, call `invalidate_by_refs`, then
   `append_event(key=f'{key}:mem', work_ref=None, kind='state', refs=[source_ref])`.
   An already-stopped record under a new key causes no availability or TSK writes.
6. Save the replay Result `{affected_refs:[source_ref]}`, then COMMIT.

Callbacks run inside a SAVEPOINT. If the transaction was left or RELEASE fails, return
unavailable. Any exception leads to ROLLBACK and a bounded error; the key stays
unsaved and retryable. TSK create keeps its own transaction and calls the read-only
`MemoryStore.source_gate`. No standalone API nests another API's transaction.

### Replay identity

- Append canonical input is `dumps({client_key, session_id, role, text: sanitize_text(text)})`.
  Only sanitized text and the Result are stored.
- Raw inputs with equal sanitized output replay as equal; this is accepted and must be
  documented. A changed sanitizer can turn a retry into conflict.
- There is no raw ledger and no new keyword filter.
- Replay of a stopped record returns its original record_ref and never restores
  availability.
- Stop canonical input is `{key, source_ref, session_id}`.

### Read and search bounds

- `read({ref}, *, purpose)` takes purpose as a host kwarg: model_context, verification or
  user_view. Any other value is a programmer error.
  - Only the record kind is served. note returns unavailable (owner not implemented).
    A missing record returns not_found.
  - A stopped record returns denied for model_context and verification. user_view gets
    the body with usable:false.
  - The output has exactly the C11 fields: media_type text/plain, hash = sha256 of the
    UTF-8 body, observed_at = append host time, version null, work_ref null,
    source_refs [].
- `search({query, session_id, limit, work_ref?})`:
  - query must be a non-empty str. Matching is an exact substring of the sanitized text,
    with no normalization.
  - limit is an int from 1 to 50. bool, 0 or values above 50 return invalid_input.
  - Results come from the same session, available records only, ordered by seq
    descending. Fetch limit+1; truncated means more eligible rows existed.
  - summaries is always []. A present work_ref returns unavailable; it is never ignored.
- `source_gate` is read-only. Non-record kinds or a foreign connection return
  unavailable.

## Focused acceptance

First add a C05-stop CT example to the shared examples.

- A1: Append Unicode, empty and whitespace text, then reopen. Check exact replay,
  conflict, and that no table holds the raw secret.
- A2: Read under each purpose. Kind-alias and note requests are rejected.
- A3: append, then a real `IntakeStore.create` gated by `MemoryStore.source_gate`, then
  stop. Expect epoch 0 to 1, still queued, with TSK and MEM events. A fresh create is
  denied with zero rows. Old create replay returns the epoch-0 receipt unchanged, and
  get_work shows epoch 1.
- A4: Two barrier-synchronized connections, no sleeps. Stop-first means the intake is
  denied. Intake-first means that work is invalidated.
- A5: A seeded non-queued state makes stop fail with all rows unchanged.
- A6: Inject aborts after the availability update, after invalidate, after append_event,
  and via a callback COMMIT. Each fully rolls back, and a same-key retry succeeds.
- A7: Search limit bounds, truncated accuracy, empty results, older rows filling the
  result after a newer stop, and work_ref returning unavailable.
- A8: Lock contention and invalid sanitizer or callback results give bounded errors,
  with no partial effects and no body or secret in error text.

## Remaining limits (unmet, not claimed)

These stay open:

- invalidation of running, paused and waiting_input work
- terminal-state source display
- notes/remember and correct
- step, artifact and verification source registration
- claim, lease and draining
- C14 read cursor and cross-session search
- real model, UI and execution activation

Each is an execution-activation blocker. This note is not an implementation, test
result, review approval, CT-20 completion or product success.
