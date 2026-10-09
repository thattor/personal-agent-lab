# TSK01/1 isolated intake preparation

This implements only the fixed [TSK01 scope](TSK01-SCOPE.md): C03.create and
C02.get_work over a caller-owned SQLite connection. It remains unused preparation.
No existing PAL persistence code was read or copied; no live DB/service, CO state,
other helper, canonical record or project was changed by this implementation unit.

## Provenance and ownership

Baseline: `d8e4465df049b2fae411b19e04990a08928aaa9c`, isolated branch
`codex/pal-tsk01-agy` in `/private/tmp/pal-tsk01-agy-20261009`.

The first author was an actual AGY `claude-opus-5-5-high` text-only call. Root
reported its CLI print timeout at 420 seconds and incomplete JSON, despite the
wrapper's exit 0 / SUCCESS indication. That incomplete artifact was rejected;
it is not an author-task success or verification result. Root mechanically
recovered just the fully closed module value, 12,465 bytes, initially untested:

`pal/intake_v5.py` SHA256
`29f5162ca648fa25da4ad7714f3fc90319707fefcaad30347b43f9816b31225b`.

Under the explicitly assigned D036/D037 alternative route, native Astra inspected
that source, completed the focused tests and this note, and verified the unit.
No source correction proved necessary in this targeted self-check; the module
retains the exact recovered SHA256 above. Astra is now an implementation owner,
not this unit's independent reviewer. The AGY conversation/state was neither
reissued nor cancelled. Root's separate fresh Sol6.1 exact-commit review, consumer
probe and full regression are pending outside this authored self-check.

## API and persistence decisions

```python
from pal.intake_v5 import IntakeStore
from pal.contracts_v5 import Grant, Limits

# connection is an already-open, caller-owned sqlite3 connection;
# source_gate is required trusted host code with same-DB availability reads.
ceiling = Grant(['read'], ['synthetic/repo'], Limits(0, 2, 3))
store = IntakeStore(connection, host_grant=ceiling, expert_id='expert',
                    source_gate=source_gate)
result = store.create({
    'key': 'request-1', 'session_id': 'session-1',
    'origin_record_ref': {'kind': 'record', 'id': 'record-1'},
    'brief': {
        'purpose': 'Prepare a summary',
        'target': {'repository': 'synthetic/repo', 'issue_numbers': [], 'files': []},
        'constraints': ['read only'],
        'conditions': [{'description': 'Save summary', 'check': 'artifact_saved'}],
        'context_refs': [],
    },
}, request_scope=ceiling)
if result.ok:
    created = result.value.to_json()
    current = store.get_work({'goal_id': created['work_ref']['goal_id']})
```

The constructor requires `isolation_level=None`, no preexisting transaction,
a typed host Grant, nonempty UTF-8 expert ID and callable source gate. Invalid
configuration raises a programmer/configuration exception. Initialization creates
only three `v5_intake_` tables in its own explicit transaction. No file is opened
by the module. A typed trusted `request_scope` is mandatory outside the wire;
an incorrect host argument is TypeError, not a model-supplied authorization.

Request shape validation precedes writes. `BEGIN IMMEDIATE` precedes replay,
grant intersection, source reads and inserts. Replay identity uses normalized
full original request plus original request_scope, not the effective Grant.
Object-key order normalizes; array order, exact text and scope duplicates remain
part of identity. Equal replay returns the saved Result before current host/gate
checks, even after a later source stop or host configuration change. It neither
mints IDs nor grants current execution authority. Different input returns conflict.

A fresh create intersects set-like capability/repository arrays in request order,
removes duplicate members, and takes the minimum of each finite integer budget.
Zero budgets and empty capabilities remain valid. Target repository membership
is required; free-text constraints remain intact and confer no rights.

The gate receives the same connection and a tuple containing the origin record
Ref and every context Ref. Repository file revision strings are excluded. Exact
string outcomes are available/not_found/denied/unavailable. Exceptions, malformed
outcomes and observed gate transaction changes produce bounded unavailable.
A savepoint also detects a gate ending the transaction and starting another;
total_changes detects ordinary gate writes that must be rolled back. The gate
is trusted read-only host code: these checks are not a sandbox against arbitrary
host code, and cannot undo a forbidden gate-owned commit of unrelated writes.

Work, immutable formal Brief/Grant/bindings, one accepted event and replay Result
commit together. Failure rolls back new effects and preserves earlier successful
work. Default IDs use UUIDs. The deterministic id_factory seam generates the event
ID after the work insert, allowing an actual mid-transaction failure test.

Root explicitly clarified Condition IDs as unique **within the immutable Brief
addressed by WorkRef**. This unit rejects duplicates there and uses SQL uniqueness
for Goal/revision and event IDs. It adds no global cross-Goal condition registry;
C09 verification is WorkRef-bound. The default UUID factory naturally avoids reuse.
Factory collisions or invalid IDs fail without partial effects; no retry loop
silently accepts a colliding host identifier.

get_work returns exactly work_ref/brief/grant/state/current_artifact_refs/
open_questions. Omitted revision selects the stored current revision (only 1 in
this unit); an unknown Goal or requested missing revision is not_found. Bool,
zero, malformed revision or extra keys are invalid_input. No stale code is
invented for reads. expert_id belongs in the create response and saved binding,
not as an extra C02 field. Reads make no persistence changes.

## Targeted validation and known limits

Command executed with Python 3.13:

```sh
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_intake_v5.py -v
```

**14 tests PASS**, using fresh temporary SQLite files, explicit reopen and
synthetic source records. Coverage includes durable complete Brief/Grant/bindings,
exact create/read shapes and event correspondence; ordered/deduplicated/zero
Grant intersection and denial/retry; same-connection active write reservation
before first intake insert; source missing/stopped/exception/invalid/commit/
rollback/restart cases; replay after reopen/source stop/changed ceiling/expert;
original-scope changes that leave the same intersection; event-stage abort on a
nonempty DB and successful retry; condition/Goal/event collisions and invalid
factory IDs; second-connection write contention; strict input and bounded errors;
read revision selection/no writes; constructor configuration rejection.

Final log: `/private/tmp/pal-tsk01-astra-targeted.txt`.
Initial log: `/private/tmp/pal-tsk01-astra-initial.txt` (retained failure).
These local logs need Root's evidence retention; their temporary paths alone are
not durable project evidence.

The initial failure was in Astra's test helper: its `None` default substituted a
valid request for the explicit invalid None case, causing success and a gate call.
A dedicated sentinel now distinguishes omitted test input from JSON null. The
same rejection test verifies null reaches the real public API and produces
invalid_input with no effects. This is a test correction, not a product parser
failure or relaxed oracle. Future helper changes must keep absent/default and
explicit null distinct; no additional approval gate is introduced.

No concrete implementation defect remains known from these scoped self-checks.
Independent exact-commit review, Root consumer checks and full regression remain
pending. Real PRI authority resolution, real MEM source availability/reference
stop and dependency invalidation, C14 shared transaction API, search/attach,
expected-version mutations/leases/Operation, historical revisions, providers/UI,
startup lock, activation, full v5 adoption, service CT/E2E and human usefulness
remain **NOT_RUN**. Synthetic transaction ordering does not certify those services.
