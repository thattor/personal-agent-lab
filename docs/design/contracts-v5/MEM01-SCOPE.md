# MEM01/1 — proposed record-to-intake connection

Status: DRAFT for technical consultation; not an implementation dispatch or product
activation. SOL owns the shared contract and integration. Baseline:
666506a438e3bd1a793255875b6acf3ecd8b7989 (TSK01 source8db45fd). Scope is PAL v5
C05 append/record stop, bounded C06, C11 record reads and the C14 transaction seam.

## Intended result

In a fresh isolated SQLite database, persist a conversation record through MEM,
create a real TSK intake from that record, stop its use, and verify that new intake
and model/verification reads reject it while owner history retains the body.
Equal old intake replay returns its historical receipt without restoring availability.
Do not substitute a fake source table for the MEM provider in the connection test.

This must not become another disconnected helper. Resolve the shared event and
existing-work invalidation boundary before adoption. Full running/paused/waiting
invalidation, derived notes, correct, claim/leases, executor and actual model/UI
activation remain separate unfinished work, never inferred from this slice.

## Candidate ownership and interfaces

MEM owns immutable record bodies, availability, append/stop replay and record
selection. TSK owns work/source dependencies and events. Only the caller opens the
database; no existing database or migration is authorized. Both stores use the same
explicit sqlite3 connection with isolation_level=None. No provider or external I/O
is performed inside a transaction.

- `MemoryStore(connection, *, sanitize_text, append_event, invalidate_by_refs,
  id_factory=None, clock=None)`: required trusted host collaborators, no silent
  permissive defaults. Exact callback shapes are still under consultation.
- `append({client_key, session_id, role, text})`: strict C05 input, host identity/time
  and durable order. Preserve sanitized UTF-8 text, including empty text and whitespace.
- `stop_reference({key, source_ref}, *, session_id)`: session is trusted host context
  for the initiating notification, not inferred from the stopped record's session.
- `read({ref}, *, purpose)`: purpose is trusted host context. model_context and
  verification reject stopped records; user_view returns retained body and usable:false.
- `search({query, session_id, limit})`: initial record-only subset; summaries:[],
  deterministic matching/order, and accurate truncated. Optional work-context search
  is not silently ignored; its behavior must be frozen before acceptance.
- `source_gate(connection, refs)`: read-only within the identical active transaction.
  A record kind/id must match exactly. Other owners require an explicit dispatcher;
  absent owner adapters fail closed.

Each standalone MEM mutation owns BEGIN IMMEDIATE, replay lookup, mutation,
TSK-owned event/invalidation callbacks, replay result and COMMIT. TSK create continues
to own its transaction and calls the MEM read-only gate. Neither nests standalone
mutation APIs. A public TSK transaction-bound callback must not commit independently.
Any callback failure rolls back the entire operation and leaves its key retryable.

Equal canonical operation/key/input returns the original result; different input
conflicts. Replay may not store unsanitized text or reactivate a stopped record.
Current `pal/sanitize.py` supplies the existing policy, explicitly imperfect. Pass
that trusted function from the integration host. Freeze whether replay equality
uses sanitized canonical text before implementation; never persist the original
unsanitized input in a secondary replay ledger or invent a new keyword filter.

## Shared boundary to resolve

The native Astra and independent Sol6.1 analyses agree that future-intake rejection
alone cannot satisfy C05/CT-20 existing-work invalidation. A possible bounded first
implementation includes TSK-owned registration of origin/context sources and queued
work invalidation in the same stop transaction. Unsupported work states must fail
the entire stop rather than falsely acknowledge completion. Before any execution
activation, extend this owner to all required states, verification and adopted refs.
An alternative record-only preparation can be technically valid but leaves that
activation blocker explicit. SOL will choose after the required Opus consultation;
these alternatives are not new owner policy questions.

## Acceptance to freeze with the chosen boundary

1. Append, exact replay/conflict, immutable body/hash/identity/time/order and reopen.
2. Source-kind alias rejection; stopped/missing/unsupported owner outcomes.
3. MEM append → real intake → record stop → fresh intake denied with zero intake
   effects → old intake receipt replay unchanged, while current source reads deny.
4. Stop removes candidates, never raw owner history; append replay cannot restore it.
5. Stop-first and intake-first orders with two synchronized connections, no sleeps.
   State precisely which pre-existing work is invalidated in each committed order.
6. Inject abort after availability update and after event/invalidation writes;
   all changes roll back, preserving already-existing rows. Retry succeeds.
7. Candidate exclusion, strict limit/bool/overflow behavior, accurate truncation,
   empty matches, and eligible older rows filling a result after a newer stop.
8. Invalid input/sanitizer/callback results and lock contention cause bounded errors
   without partial effects, raw-secret replay copies, or output body leakage.

Python standard library only. SOL owns `pal/intake_v5.py`, shared examples, integration
tests and canonical records. The eventual MEM author receives isolated files
`pal/memory_v5.py`, `tests/test_memory_v5.py`, and a short implementation note. An
independent reviewer receives the exact integrated commit after author tests pass.
Root runs the meaningful connected cases and full regression, then selects the next
unfinished authorized dependency; a successful checkpoint is not a stop condition.
