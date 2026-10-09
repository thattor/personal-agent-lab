# MEM01/1 — record-to-intake connection

Status: ADOPTED technical scope under D038, after actual Opus5.5 consultation and
SOL dispositions. Source prerequisite c3ace7ad917a7b1b2a601a0d2a63d16a19a66115;
worker dispatch pins the commit containing this frozen scope. PAL v5 C05 append /
record stop, record-only C06, C11 record read, C14 events and queued TSK invalidation.
Python standard library only. No real service, model call, live DB, migration,
external access, schedule or runtime/config change.

## Ownership and deliverables

SOL owns pal/intake_v5.py, its tests, shared examples, integration and canonical docs.
Astra owns only pal/memory_v5.py, tests/test_memory_v5.py and
 docs/design/contracts-v5/MEM01-IMPLEMENTATION.md in its separate worktree. Read
this scope, pal/contracts_v5.py, pal/intake_v5.py, pal/sanitize.py and v5 contract.
Return those three files, actual targeted test results and remaining limitations.
Independent Sol6.1 reviews the exact integrated commit after author tests pass.

The complete small path is MEM append → real TSK create → MEM reference-stop →
TSK queued epoch invalidation and event in the same transaction. Fresh intake/read
is denied; old create receipt replays unchanged; owner history retains the body.
This is unfinished product integration, not another fake availability table.

## Shared transaction interfaces (frozen)

Both stores receive the same caller-owned sqlite3 connection, isolation_level=None.
Constructors reject active transactions/config errors. They initialize only their
own v5_ tables in a transaction. No file opening or old-schema migration.
Standalone create/append/stop own BEGIN IMMEDIATE through COMMIT/ROLLBACK. Busy returns
unavailable. Callbacks never start/end a transaction or perform external I/O.

TSK exposes these host-only public methods:

- append_event(connection, request:dict) -> Result[{event_id}]. request is exactly
  C14 key, session_id, kind, text, refs, with optional work_ref (omit if absent).
  Strict JSON values. Equal key/canonical input replays; different input conflicts.
- invalidate_by_refs(connection, *, key:str, session_id:str, refs:tuple[Ref,...])
  -> Result[{work_refs:[WorkRef JSON]}]. Require exact stored connection and an active
  transaction (programmer errors otherwise). Deduplicate refs in first-seen order.
  TSK finds current dependent work from its source table. Require complete origin
  dependency coverage; old/inconsistent work without it returns unavailable.
  Precheck all affected states before any writes: only queued is supported. Other
  states return unavailable, so caller rolls back the stop. For each affected Goal,
  epoch+1, same revision/state queued, one state event, all within caller transaction.
  Replay by key includes session and refs; equal request never increments twice.
  No fake transition for running/paused/waiting/terminal states.

Callbacks return strict Result, not raw IDs or exceptions for business failures.
Caller must propagate failed Result and roll back its whole mutation. Programmer /
SQLite exceptions become bounded unavailable at the standalone entrypoint. Verify
result shape; malformed results are unavailable. These are trusted host methods,
not a sandbox. SAVEPOINT plus active-transaction checks may detect misuse, but a
callback which commits earlier writes violates the contract and cannot be rolled
back retroactively. Do not claim otherwise. Test the actual TSK methods never commit;
atomic rollback tests inject ordinary exceptions while the transaction stays open.

Use dumps([...]) with separate namespace/command/key/goal elements for internal keys;
opaque IDs can contain punctuation, so colon concatenation is not collision-safe.
TSK create registers origin and every context Ref in v5_intake_source atomically
with work/event/replay. Its saved C03 result remains immutable when current epoch
changes. Current get_work returns the changed epoch. No historical receipt grants
current execution or reference authority.

## MEM API and persistence

MemoryStore(connection, *, sanitize_text, append_event, invalidate_by_refs,
            id_factory=None, clock=None)

All three collaborators are required trusted callables. id_factory(prefix) defaults
to UUID IDs; clock() returns nonempty UTF-8 host timestamp (default UTC ISO8601).
No identity sanitizer/default-allow invalidator. At integration pass current
pal.sanitize.sanitize, and the real bound TSK methods. A host closure connects TSK's
required gate to the MEM instance after both stores are initialized; no create before
initialization completes. MEM owns only v5_mem_record and v5_mem_replay.

append({client_key,session_id,role,text}) -> Result[{record_ref}]
- role exactly user|assistant; strict UTF-8 text, including empty/whitespace. Reject
  extras/wrong types/empty IDs before writes. Sanitize before BEGIN; exception or
  non-str/bad-UTF8 result is unavailable. Current sanitizer is deliberately imperfect.
- Replay identity is canonical sanitized input; different raw text with equal sanitized
  text replays equally. Changed sanitized content/session/role conflicts. Never persist
  raw input, raw-input hash or a second unsanitized replay ledger.
- New immutable host record ID, durable sequence, role/session, sanitized text/hash,
  observed_at and usable flag. A new Ref is always a new immutable body/version.
- Same transaction calls append_event with namespace [C05.append,client_key,event],
  kind accepted, text record saved, refs [record_ref], no work_ref, then saves replay.

stop_reference({key,source_ref}, *, session_id) -> Result[{affected_refs}]
- source_ref must be record; strict key/session. Session is trusted initiating host
  context and participates in replay identity. Missing record is not_found.
- Equal operation/key/input replays; changed input conflicts. If available: mark
  stopped, call invalidate_by_refs with namespace [C05.stop_reference,key,invalidate],
  then append_event with namespace [C05.stop_reference,key,event], kind state,
  text source use stopped, refs [source_ref], no work_ref. Save Result, commit.
- Already stopped under a new key saves a receipt without another event/invalidation.
  No physical delete or body overwrite; append replay never restores usability.

read({ref}, *, purpose) -> Result[C11 value]
- purpose is trusted host context, exactly model_context|verification|user_view;
  invalid host purpose is a configuration/programmer error. Request validates Ref.
- Only record owner is implemented. Other kinds return unavailable; missing record
  not_found; stopped model/verification read denied. user_view returns usable:false.
- Exact C11 required fields: ref, content, media_type=text/plain, hash=SHA256 UTF-8,
  observed_at, source_refs=[], usable. Omit optional version/work_ref; null is not str.

search({query,session_id,limit,work_ref?}) -> Result[C06 value]
- query may be empty (recent records); otherwise exact literal substring, no language
  normalization. Same-session available records ordered durable seq descending.
- limit strict int 1..50; bool/zero/overflow invalid_input. Validate WorkRef if present,
  then unavailable for this unfinished optional filter; never silently ignore it.
- summaries=[], record_refs eligible matches, truncated iff more eligible matches
  exist than limit (fetch limit+1). Stopped rows cannot displace eligible older rows.

source_gate(connection, refs:tuple[Ref,...]) -> str
- Bound method requires identical connection and active transaction; mismatch or
  malformed refs returns unavailable. Reads only, no changes/transaction control.
- Non-record ownership unavailable; missing record not_found; stopped denied; all
  available returns available. Deterministic first failing Ref order, empty available.

## Required tests and outcome

Use fresh tempfile SQLite databases and actual reopen, no original/live data.
- Exact durable Unicode/empty/whitespace/sanitized append and immutable hash/time/order;
  canonical replay/conflict, sanitizer failure, no raw secret persisted or in errors.
- Ref kind aliases, missing/stopped/history purposes; current read after old selection.
- Callback failures/malformed results roll back record/availability/event/replay and
  preserve preexisting data; failed key remains retryable. No premature commit by actual
  TSK callbacks. Trusted contract violations are not sandbox/rollback success claims.
- Real MEM→intake→stop: current epoch0→1, queued, source refs indexed, TSK/MEM events;
  fresh intake denied without effects, old intake receipt remains epoch0.
- Two connection orders with explicit locks/barriers, no sleeps: stop-first denies;
  intake-first commits, then stop invalidates that work. Non-queued affected state
  or missing dependency index rejects the whole stop with all previous rows unchanged.
- Search bounds/order/truncation/stop exclusion, work_ref unavailable; lock contention.
- Separate independent review of integrated source, targeted tests and root full suite.

Unmet: notes/remember/correct/transitive propagation; all non-queued invalidation;
step/artifact/verification dependency registration; claim/leases/draining; C14 cursor;
full C06/cross-session relevance; real PRI authority, model, UI/execution activation.
Before execution, satisfy the corresponding v5 obligations. Do not label CT-20 or
whole C05/06/11/14 complete. After this scope passes, continue the next authorized
TSK/RUN connection dependency instead of stopping at the checkpoint.
