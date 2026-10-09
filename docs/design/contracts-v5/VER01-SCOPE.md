# VER01/1 — deterministic saved verification (Stage A)

ADOPTED technical API scope under D038/C074 after Opus task7cd3d557 staging
and completed SWE consultation e2477652c7ce43cbb9e20a91386fe2e1 (REFINE).
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


## SWE disposition and frozen details

Adopt consultation items1-10 and meaningful cases, with these exact clarifications:

- The TSK method is verification_context(connection, request, *, purpose). The
  request contains only work_ref; the host-only purpose keyword is required.
  Wrong purpose returns invalid_input. The thin public wrapper requires the exact
  active connection before the Result wrapper, as existing ART-save authorization.
- Preserve existing _authority order: no owned active lease is denied, including
  an ordinarily released queued/paused Goal. An active pause/drain is conflict;
  cancel with an old WorkRef is stale. The consultation's test6 blanket queued/
  paused=conflict conflicts with its item2; use these existing precise outcomes.
- Status uses _current with epoch matching, not running authority or source gate.
  It returns required origin/Brief records only (not every registered optional
  lookup), fixed unique Condition IDs and the validated ordered artifact set.
  Required refs must remain registered/record-only; malformed stored state is
  unavailable, distinct from malformed caller input invalid_input.
- VER verify input non-artifact Ref is invalid_input; any ordered set mismatch
  (including duplicate/reorder) conflict. Owner ART not_found for an artifact in
  the current set and MEM not_found for a required dependency are unavailable.
  Different saved artifact Goal/revision is stale; an older artifact epoch of the
  same revision is allowed. Transient or corrupt evidence never creates an unmet
  check. Empty current set alone produces artifact_saved unmet.
- Context(status) stale or a legitimately appended artifact set yields invalidated.
  Source denied yields invalidated. Context not_found/unavailable remains that
  error; all other uncertain/broken owner evidence is unavailable. Pause with
  unchanged epoch/set/sources keeps the stored verification fact valid.
- Same-input verify/get_by_key returns the original receipt before authority
  checks. The later C10 typed read must never call get_by_key. No model/step spend.
- Storage layout is private to VER. Retain enough immutable context, artifact
  metadata and original receipt to validate all record bindings, exact fixed
  Condition IDs/order, expected deterministic checks/evidence refs and conservative
  dependency union. Recompute structural expected checks on stored-data validation;
  a forged semantic met is corrupt, never accepted. The suggested SQL column list
  is illustrative; no timestamp API or extra engine is required by C09.
- Callback guard errors clean only owned savepoints and preserve caller transaction
  for inspect. A trusted callback's COMMIT cannot be undone; document that limit.

Delivery split: scoped native test author prepares compact in-memory public-API
acceptance tests against this frozen contract (no claims before implementation).
SWE-2 High is assigned only the new VER module and implementation note through CO,
with those tests as immutable inputs and declared verifier. SOL owns the independent
TSK callback and later actual connected tests. This reduces implementation output
size after earlier large SWE coding timeouts; it does not retry unknown tasks or
change CO runtime/state/limits. A separate native reviewer will inspect exact code.
