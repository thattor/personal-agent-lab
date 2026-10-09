# VER01/1 — deterministic saved verification (Stage A)

PROPOSED technical API scope under D038/C074. Opus task7cd3d557 recommends this
stage before C10 completion; SWE consultation must refine it before implementation.
Base accepted source2e8dfcf, full605; actual dispatch pins the proposal commit.

Value: fixed host Conditions are checked against the whole saved artifact set and
persisted as a typed, replayable record. Later code can distinguish a historical
MET receipt from a verification that is currently valid. No Goal becomes completed.

No semantic model, provider, EXE operation, completion, completed-state changes,
RUN verify Action, general recovery, new state engine, artifact re-input, UI,
new permission/cost/service or live DB. Python stdlib and temporary SQLite only.
Unknown earlier calls remain untouched. Do not search/read old PAL implementation.

## Ownership and proposed APIs

SOL owns the TSK public callback, contracts and actual connected tests. A separate
implementation owner may write only pal/verification_v5.py, its focused tests and
VER01-IMPLEMENTATION.md. Independent reviewer differs from each author. No shared
writer, no VER reads of TSK/ART SQL or direct TSK state mutation.

TSK adds a same-active-connection readonly host callback:

    verification_context(connection, {work_ref}, *, purpose='save'|'status')
      -> Result{work_ref,conditions:[Condition],artifact_refs:[artifact Ref],
                source_refs:[record Ref]}

Both purposes require matching current WorkRef and validated immutable Conditions,
required origin/Brief record dependencies and the exact ordered current artifact
set (bidirectional Step/set validation). Save additionally requires current running
lease/no pause or drain; status is a factual snapshot independent of running/paused/
completed state, so a stopped control alone is not confused with changed evidence.
A later epoch returns stale. Missing state/corrupt stored contracts return explicit
not_found/unavailable, not an invented valid snapshot. It owns no transaction/write.

VerificationStore(connection, *, context, artifact_inspect, source_gate,
                  id_factory=None) owns only v5_ver_ tables on a caller-supplied idle
isolation_level=None connection. Proposed public methods:

- verify({key,work_ref,artifact_refs}) -> C09 Result{verification_ref,checks}.
- get_by_key({key}) -> original C09 receipt, or not_found; history only.
- get_verification({verification_ref}) -> C09 typed Result{
  work_ref,artifact_refs,checks,source_refs,status:valid|invalidated}.
- inspect(connection,{verification_ref}) -> the same typed result on the same
  supplied active transaction, readonly; this is the later C10 callback seam.

No C11 verification body input/dispatch is activated in this stage. Typed historical
checks remain available via get_verification with status; they contain bounded
host reasons and refs, not copied source bodies. Actual artifact C11 access stays
with ART. C11 VER readback is a later explicitly required API before its use.

## Verify and immutable history

Validate a closed input object, WorkRef integer bounds, artifact-only Ref list,
nonempty key, exact canonical input identity (object order irrelevant, arrays
preserved). Within one short BEGIN IMMEDIATE: key replay first; differing input
conflict. Call guarded TSK context(save) and require artifact_refs to equal the
entire exact ordered current set. No subset, duplicate, reordering or stale-epoch
success. Inspect every artifact through actual ART.inspect in the same transaction;
require matching Goal/revision (stored artifact epoch may be older), exact Ref and
valid hash/bytes. Source union includes required TSK context records and all artifact
dependencies; gate that union with actual MEM. Missing/corrupt owner evidence or
transient failure is unavailable, stopped source denied; no partial snapshot save.

Create exactly one Check per fixed Condition ID, in fixed Condition order:

- artifact_saved: met only if the current set is nonempty and every artifact's
  immutable body/hash/count/binding/current sources pass. Empty set is unmet.
  This predicate guarantees storage existence/integrity; a Condition description
  does not magically add semantic quality, delivery or arbitrary content checks.
- semantic: unknown with a fixed evaluator-unavailable reason.
- source_fetched: unknown because no actual EXE evidence owner is connected.

Do not substitute simpler Conditions or mark unknown as met. Verification consumes
no model/step budget in this deterministic stage. Store host-issued verification
Ref, current WorkRef, original input, fixed-condition snapshot, ordered artifact
refs, inspected artifact metadata, checks and conservative record dependencies in
one transaction with the original receipt. Strictly validate stored shapes/types/
condition IDs and metadata bindings on read; corruption is unavailable, no repair.
No raw exceptions/private input in errors. Ordinary failure rolls back; BaseException
rolls back and propagates. Readonly collaborators use savepoint/transaction/change
checks; they remain trusted host code, not a hostile-code sandbox.

## Current status, without another invalidation engine

get_verification owns a short read transaction; inspect uses its caller's existing
transaction. Neither changes rows. Load and validate the stored record, then compare
TSK context(status), the exact current set and current source availability. Current
WorkRef stale, a legitimately added artifact, or an explicitly denied record means
invalidated. Unavailable/missing/corrupt owner evidence remains unavailable; never
convert uncertainty to valid or guess that a record was deliberately stopped.
Check ART integrity through its owner before valid, binding it to the stored hash,
count and dependencies. A saved verification can never validate changed bytes.

Within this scoped system epochs only increase, artifact sets append and reference
stops cannot be undone, so derived invalidation is monotonic. C10 must later re-read
this typed result and all current conditions inside its own transaction; historical
get_by_key replay never grants completion authority. Source stop requires no new
VER mutation hook in Stage A. Before C10 becomes reachable, completed-state stop
and terminal-safe lease handling must land together, as Opus L1/L2 require.

## Required acceptance

Actual MEM/TSK/ART/VER on temporary SQLite: saved compose -> deterministic verify
met while Goal unfinished; semantic/source_fetched unknown; empty set unmet; reopen;
exact key replay after invalidation; subset/reorder/different-input refusal; later
attachment and next epoch invalidate; selected/unselected source stop invalidate;
missing/corrupt evidence unavailable. Two connections explicitly order verify vs
stop and attachment; no mixed snapshot. Rollback after actual VER write and process
interrupt leaves no partial record/key and preserves caller ownership. Typed forged
checks/duplicate or missing Conditions/unsupported refs/malformed callbacks fail.
No completion or product/real-model usefulness claim from these cases.
