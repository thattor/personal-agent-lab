# MEM01/1 author implementation

Scope: [MEM01-SCOPE.md](MEM01-SCOPE.md), adopted D038 technical boundary.
Author base `7a12a111ff1a21b796269a9e2f28bd04a535146d`, isolated branch
`codex/pal-mem01-astra`, `/private/tmp/pal-mem01-astra-20261009`.
Native Astra authored only `pal/memory_v5.py`, `tests/test_memory_v5.py` and this
note. Root owns TSK/shared-source changes and real two-store integration. No old
PAL persistence implementation, original DB, provider, CO/AGY state, service,
configuration, schedule or external system was used or changed by this unit.

## Public API and data ownership

```python
from pal.memory_v5 import MemoryStore
from pal.sanitize import sanitize

# Same caller-owned sqlite3 connection as the initialized TSK store.
# Root's host closure connects intake.source_gate to this instance afterwards.
memory = MemoryStore(connection, sanitize_text=sanitize,
                     append_event=intake.append_event,
                     invalidate_by_refs=intake.invalidate_by_refs)
created = memory.append({'client_key': 'message-1', 'session_id': 'session-1',
                         'role': 'user', 'text': '保存する本文'})
if created.ok:
    ref = created.value.to_json()['record_ref']
    current = memory.read({'ref': ref}, purpose='model_context')
    stopped = memory.stop_reference({'key': 'stop-1', 'source_ref': ref},
                                    session_id='session-1')
    history = memory.read({'ref': ref}, purpose='user_view')
```

The example specifies composition with Root's public methods; it is not an
executed integration claim. Both stores must be initialized before intake begins.

MemoryStore requires an idle SQLite connection with `isolation_level=None`, plus
all three trusted callables: sanitizer, event writer and invalidator. Optional
host `id_factory(prefix)` and `clock()` enable deterministic failures/tests; default
IDs use UUIDs and timestamps UTC ISO8601. No file is opened by this module.
Initialization owns one transaction and creates only `v5_mem_record` and
`v5_mem_replay`. Invalid configuration raises programmer/configuration errors.

Record rows store durable sequence, immutable record ID/session/role/sanitized
text/hash/timestamp and mutable usability. Ref.kind is always record; no alias
or foreign-owner registration exists. Replay rows contain command/key, canonical
**sanitized** request and exact saved Result. Raw text and raw-text hashes are not
stored in either table. Sanitizer failures or non-str/invalid-UTF8 results return
unavailable before BEGIN. Current `pal.sanitize.sanitize` is deliberately imperfect;
this implementation does not promise complete secret detection.

append validates exact keys/types/UTF-8 before sanitization. Equal sanitized
content/session/role with the same key replays, including different raw inputs
that sanitize equally. Changed canonical input conflicts. Neither IDs/timestamps
nor events are regenerated on replay, and replay cannot restore usability.

stop_reference requires a record Ref and a trusted initiating session. Its replay
identity includes session and source Ref. A first stop changes availability, invokes
TSK invalidation, emits its event and saves the receipt in the same transaction.
An already-stopped record under a new key records an equal affected-Ref receipt
without another invalidation/event. Missing records return not_found without a
saved failed key. The immutable body remains available for owner history.

## Transactions and callback boundaries

Standalone append/stop own BEGIN IMMEDIATE through COMMIT/ROLLBACK. Busy operations
return unavailable. A failed callback Result rolls back all new MEM and same-DB
callback effects; successful operations save their replay only after callbacks.
Preexisting records/events remain. No nested public mutation is allowed.

Callbacks receive the identical connection and never own transaction completion:

- append_event receives exact C14 fields, without absent optional work_ref.
- invalidate_by_refs receives key/session and a tuple of immutable Ref objects.
- Internal keys use `dumps([command, original_key, purpose])`, preserving opaque
  punctuation without ambiguous delimiter concatenation.
- Both callbacks must return an exact Result. Success payloads are validated:
  event_id is a nonempty UTF-8 ID; work_refs is a list of strict WorkRef JSON.
- Failed callback codes propagate, but messages and refs are normalized to a fixed
  bounded public message and empty refs. Thus arbitrary callback text/identifiers
  cannot become public secret-bearing diagnostics. Exceptions/malformed results
  become bounded unavailable. Failure remains failure and saves no replay key.

A savepoint detects some callback transaction replacement. These are trusted host
callbacks, not sandboxed code: a contract-violating callback that commits earlier
writes cannot be rolled back retroactively. Tests prove ordinary same-transaction
exception/failure rollback, not impossible recovery from malicious commits.

Root's TSK source index, queued epoch invalidation, non-queued/inconsistent-index
rejection and real public C14 implementation are outside these three author files.
They must be checked together with MEM before the connection slice is accepted.

## Current availability and retrieval

read takes only `{ref}` plus required trusted purpose. Invalid host purposes raise
ValueError. Unknown record is not_found; unsupported owner kind is unavailable;
invalid Ref syntax is invalid_input. Stopped model_context/verification reads are
denied. user_view returns the retained sanitized body with usable=false.

C11 output contains exactly ref/content/media_type/hash/observed_at/source_refs/
usable. Content is text/plain with SHA256 of UTF-8 bytes. source_refs is empty for
original records; optional version/work_ref are omitted, never null.

search is same-session, usable-only, newest durable sequence first. Empty query
means recent records; nonempty query uses exact literal substring matching without
case/language normalization or LIKE wildcard interpretation. Limit is strict int
1..50. Fetching limit+1 eligible rows determines truncation, so stopped newer rows
do not displace usable older candidates. summaries is empty. A valid optional
work_ref returns unavailable; malformed WorkRef returns invalid_input. The unfinished
filter is not silently ignored.

source_gate requires its identical connection, active transaction and tuple of
exact Ref values. It performs only reads, in first-failure order: unsupported owner
unavailable, unknown record not_found, stopped record denied, otherwise available.
Empty tuple is available. A selected Ref is not cached authority: subsequent reads
and gates check current availability again.

## Author verification and remaining work

Executed command:

```sh
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_memory_v5.py -v
```

**19 tests PASS**, using fresh temporary SQLite files and actual reopen. Tests cover
Unicode/empty/whitespace fidelity, hash/timestamp/order, sanitization and absence
of raw secrets/hashes, sanitized replay/conflict and callback suppression, stop
receipts/history/current denial/no reactivation, opaque event-key namespaces,
callback failures/malformed results with rollback and retry, private callback error
payload normalization, factory collisions/clock failures, literal search/bounds/
truncation/exclusion, optional WorkRef failure, source-gate connection/transaction/
order/no writes, lock contention, strict input and constructor/nested-call errors.
Synthetic event/invalidator tables intentionally let callback writes participate
in rollback. They do not establish real TSK dependency or epoch behavior.

Initial 18-test log: `/private/tmp/pal-mem01-astra-targeted-initial.txt` (PASS).
Final 19-test log: `/private/tmp/pal-mem01-astra-targeted.txt` (PASS).
The additional test follows Root's explicit bounded-callback-error reminder and
checks a long sentinel-bearing failed Result including a private Ref. No failing
run is suppressed. Root must retain these temporary logs in project evidence.

Author checks are not independent review. Root's actual MEM→TSK→stop→epoch path,
controlled two-connection ordering, non-queued/missing-index rollback, exact-commit
independent Sol6.1 review and full regression remain pending at author handoff.

Notes/remember/correct/transitive propagation; non-queued invalidation;
step/artifact/verification source registration; claim/leases/draining; C14 cursor;
full C06 relevance; real PRI authority, models, UI/execution activation and overall
human usefulness remain NOT_RUN/UNMET. This note does not claim whole C05/C06/C11/
C14, CT-20, E2E or product completion. Continue the next authorized TSK/RUN dependency
after integration rather than treating this checkpoint as project completion.
