**REFINE**

The unit is the right size. Two changes are needed before implementation. First, Root SOL must record the trusted request-scope input as a v5 contract note. Second, historical `get_work` reads must be explicitly deferred.

## Blockers and choices

**1. Request limits (needs Root SOL to record it; nothing else needs an owner decision)**
- Add a trusted host argument `request_scope = {capabilities, repositories, limits}` to the host-side `create`. Keep it out of the C03 wire and out of `DraftBrief`.
- TSK computes Grant as the overlap of `host_ceiling` and `request_scope`:
  - capabilities and repositories: set intersection, sorted;
  - each limit: the smaller of the two values.
- Because it is an overlap, a bad `request_scope` can only narrow the Grant, never widen it past host config. This needs no language understanding.
- `brief.target.repository` must be in `grant.repositories`. If not, return `denied` (the Brief proposes more than the request allows). An empty intersection, or a limit ≤ 0, also returns `denied`.
- `constraints` are stored word for word and never parsed. They can never widen the Grant.
- Who produces `request_scope` in production (PRI's semantic resolution) is deferred. In this unit, tests supply it directly.
- Adding a host argument changes C03's provider-side interface. Under the v5 rule that provider, consumer and contract examples change together, Root SOL owns this change. That is the one real authority item. Everything else below is a technical choice.

**2. Source existence (assumption with a narrow seam)**
- Inject `resolver(refs) -> {ref: available | not_found | unavailable}`. Call it **after** the idempotency lookup and **before** `BEGIN`, because no external I/O may happen inside a transaction.
- It covers `origin_record_ref` (kind must be `record`, otherwise `invalid_input`) and `context_refs`.
- Map results as follows: `not_found` → `not_found`; `unavailable` or an exception → `unavailable`. Either way, nothing is written.
- Stated assumption: Ref IDs point to immutable versions, so the gap between check and commit only covers later deletion. MEM owns that.
- Tests show that TSK handles resolver outcomes correctly. They do **not** show that MEM is a working source authority.

**3. `get_work` behaviour**
| Input | Result |
|---|---|
| Malformed `goal_id`, or `revision` that is not a strict int ≥ 1 (`bool` and `"1"` rejected) | `invalid_input` |
| Unknown `goal_id` | `not_found` |
| `revision` greater than the current revision | `not_found` (it never existed; not `stale`) |
| `revision` omitted or equal to current | current snapshot, with the current epoch |
| `revision` lower than current | deferred; cannot happen yet, since nothing creates revision 2 |

- `stale` is only for state changes made against an expected target. A read never returns `stale`.
- Defer the snapshot shape for historical reads (state, artifacts, whether it is current) to the C10 change work.

**Transactions and ownership**
- Use `isolation_level=None` with explicit `BEGIN IMMEDIATE`, then `COMMIT`, or `ROLLBACK` on any exception.
- One transaction writes: the work at revision 1 / epoch 0 / `queued`, the formal conditions, the Grant, the input refs, the expert binding, the `accepted` event and the idempotency row (key, normalized input, stored result).
- Keep the event writer internal: `_append_event(conn, …)` must never begin or commit. That way C14's eventual shared transaction owner can pass in its own transaction. Public `append_event` is deferred.
- The event key comes from the create key plus `accepted`. The event text is fixed host text, not model output.
- A unique-key race inside the transaction: re-read, then replay or return `conflict`.
- An sqlite busy/locked error returns `unavailable`. Invalid host config fails when the store is built, not as a `Result`.

**Idempotency**
- Normalized input is canonical JSON (sorted keys) of session, origin ref, draft brief and `request_scope`.
- Arrays keep their order. Text is not trimmed or case-folded.
- The key is scoped to the `create` command.
- A replay returns the stored result even if host config has changed since, and does not call the resolver.

**Smallest public API**
- `TaskStore(db_path, host_config={expert_id, ceiling}, id_factory, resolver)`
- `create(key, session_id, origin_record_ref, brief, request_scope) -> Result[{work_ref, expert_id, state, grant}]`
- `get_work(goal_id, revision=None) -> Result[{work_ref, brief, grant, state, current_artifact_refs, open_questions}]`

Tests inspect events with raw SQL on the temporary DB. No C14 read API is added.

## Minimum tests

**Rejection** (each one checks that every table stays empty):
- strict types: `bool`-as-int, empty IDs, extra fields, empty `conditions`, a bad `check` enum, a bad Ref kind, `issue_numbers` that are not ints;
- target repository outside the Grant → `denied`;
- empty capability intersection → `denied`;
- resolver `not_found`, `unavailable` and exception;
- the resolver is called with `conn.in_transaction == False`.

**Grant:**
- the result is the exact intersection and per-limit minimum;
- a `request_scope` larger than the ceiling is clipped, never widened;
- free-text constraints have no effect on the Grant.

**Replay:**
- same key and input: identical result, including condition IDs; one work row, one event, resolver not called again;
- same key with any change (including condition order or `request_scope`) → `conflict`, nothing written;
- different key with the same input → a second work.

**Rollback:**
- inject a failure after each insert (work, conditions, Grant, refs, event, idempotency row, before commit);
- every table stays empty and the key is not consumed;
- a retry with the same key then succeeds fresh.

**`get_work`:**
- after create: revision 1, epoch 0, `queued`, formal condition IDs, Grant equal to the create result, empty artifact and question lists;
- unknown ID and `revision=2` → `not_found`;
- `0`, `-1`, `True`, `"1"` → `invalid_input`;
- `total_changes` is unchanged by the read.

**Scope:**
- no claim, attach or state change after create;
- only the configured expert ID is bound.

## Remaining limits and deferred items

- PRI's semantic production of `request_scope`, and any confirmation from the person making the request.
- MEM as a real source authority; ref deletion after the check.
- C02 search; C03 attach and `pending_inputs`; C10 revisions and historical snapshots; "a change never widens the Grant".
- Public `append_event` and the C14 shared transaction owner; the C14 read cursor.
- The startup lock and cross-process concurrency.
- UI `client_key` and the internal-key generation policy.
- Everything stays on the isolated temporary DB, with no product activation.

