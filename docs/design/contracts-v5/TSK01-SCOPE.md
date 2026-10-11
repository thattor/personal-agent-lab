# TSK01/1 — isolated create and read preparation

Owner/integrator: SOL. Contract: PAL-contracts-v5 C03.create, C02.get_work,
INT00/1 and the accepted ordering below. Source prerequisite: INT00 as integrated
in 02ff5a6156f6511bd7cff5a8155f1a703123a253. The actual worker base is the commit
containing this scope, recorded in its dispatch receipt. This is unused preparation,
not an adopted live service or permission to access an existing database.

## Assignment and interface

Implement only `pal/intake_v5.py`, `tests/test_intake_v5.py`, and
`docs/design/contracts-v5/TSK01-IMPLEMENTATION.md`. Read those new files, this scope,
`pal/contracts_v5.py`, `pal/__init__.py`, the common-wire scope and selected C02/C03/C14
contract excerpts. Python standard library only. No other file writes, real provider,
network, live DB, schema migration, canonical record update, or CO/runtime changes.
Use a separate staged workspace. SOL alone integrates and owns canonical records.

Expose `IntakeStore(connection, *, host_grant, expert_id, source_gate, id_factory=None)`.
The caller supplies a sqlite3 connection with `isolation_level=None`; no file is
opened by this module. Reject a preexisting transaction and invalid host configuration
as programmer/configuration errors. Unit tests use fresh temporary SQLite files and
reopen those exact files. The store may initialize only its own `v5_intake_` tables;
do not migrate another schema. Keep persistence small: a work row may embed immutable
formal Brief, Grant and bindings once; separate event and replay rows are enough.

`create(request: dict, *, request_scope: Grant) -> Result` takes exactly the C03
wire keys: key, session_id, origin_record_ref, brief. brief is DraftBrief JSON.
`get_work(request: dict) -> Result` takes exactly goal_id and optional revision.
Use the existing strict wire values and Result; do not import private parser helpers
or create another validation framework. Inputs are JSON objects, not raw JSON text.
Preserve valid text, array order and all data. Reject extras, bool-as-int, bad UTF-8,
empty IDs, wrong Ref kind and model-supplied Condition IDs with bounded invalid_input.

`request_scope` is a required **trusted host-only** Grant, outside the C03 wire and
DraftBrief. Tests provide synthetic trusted scopes. A real PRI authorization resolver
is NOT_RUN. Intersect capabilities/repositories with the host ceiling and take the
minimum of each limit. Preserve request order, omitting duplicates in the resulting
set-like capability/repository arrays. Zero limits and empty capabilities are valid
exhausted grants, never unlimited. Require the target repository in the intersection.
Free-text constraints remain unchanged and cannot enlarge rights. Intersection alone
does not prove that request_scope accurately represents the user's permission.

## Transaction and persistence contract

1. Validate request shape and types without writes.
2. BEGIN IMMEDIATE; busy/locked means unavailable, with no writes.
3. Look up the C03.create key. Equal canonical input returns the exact stored Result;
   any changed field, including request_scope, session, condition order or origin,
   returns conflict. Canonical object keys may reorder; text/array order may not.
   Replay precedes current grant/source checks and makes no effects or authority claim.
4. Compute the nonexpanding Grant and check target repository membership.
5. Call required `source_gate(connection, refs)` inside the same transaction. refs
   contains origin_record_ref (record kind) and every context_ref, as immutable Ref
   values; target.files[].ref is a repository revision, not this Ref gate's input.
   There is no default allow gate. The host-owned gate performs same-DB availability
   reads only: no external I/O, commit, rollback or other transaction control.
   Exact string outcomes: available, not_found, denied, unavailable. Missing is
   not_found; stopped is denied; invalid return or exception is unavailable.
   If the gate ended the transaction, return unavailable before any intake writes.
6. Mint unique host Goal/Condition/event IDs, revision1, epoch0, queued. Atomically
   persist the formal Brief, Grant, origin/session/configured expert binding, one
   accepted event carrying WorkRef, and the replay Result; then COMMIT.

Use an internal event writer on the existing connection, without commit. Public C14
append_event/shared transaction ownership is deferred. Rejections never save a key,
event or partial work. A failed key can be retried after its condition is repaired.
On failure after a write, roll back everything. Keep exception details/data out of
public errors. Do not swallow programmer/config errors in the constructor.
An optional host id_factory(prefix) supports deterministic IDs and one injected
mid-transaction abort; default to UUIDs. It does not authorize model-generated IDs.

get_work is read-only and returns exactly the C02 fields: work_ref, brief, grant,
state, current_artifact_refs=[], open_questions=[]. Unknown Goal or absent revision
is not_found. Invalid revision (including bool/zero) is invalid_input. This unit can
only store revision1; historical revision creation/read is NOT_RUN. `stale` belongs
to later expected-version mutations and must not be invented for this read.
The create result, rather than get_work, exposes expert_id per the v5 contract.

## Required checks and return

- Reopen durable intake; formal unique Condition IDs and complete immutable values.
- Exact/empty/zero Grant intersection; target denial; constraints preserved.
- Gate sees the same connection/in_transaction and every source Ref; synthetic
  stopped/missing sources, raising/invalid gate, and gate commit fail with no effects.
- Same-key replay after reopen and later source stop returns the same original result
  with no gate call/new event; reordered object keys replay, any changed field conflicts.
- Inject abort after the work insert but before accepted event/replay; no partial rows,
  then retry succeeds. Another connection's write lock returns unavailable.
- Strict input rejection and read selection; read causes no DB changes.

The synthetic gate table proves the seam and ordering, not a real MEM service or
reference-stop implementation. Do not implement search, attach, change/claim, lease,
Operation ledger, providers, UI, startup locks, real PRI authority, or historical
revision creation. No CT/E2E/full-product PASS follows these scoped tests.

Run `python3 -E -s -B -m unittest discover -s tests -p test_intake_v5.py -v`.
Return only the three new file contents/diff, actual targeted test result, API/example,
and remaining limits. SOL checks source hashes/diff and full regression. Independent
review comes from a separate model/context, never the author's self-check alone.
