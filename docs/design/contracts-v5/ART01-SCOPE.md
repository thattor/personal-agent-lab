# ART01-store/1 — durable draft bytes and current source readback

Status: ADOPTED technical implementation scope under D038. SWE consultation
dc4fbad81715497481bb66a5e02f8f23 completed; SOL adopts its five clarifications below.
This implements existing C08/C11 semantics, not a new live capability.
Base prerequisite is TSK02/RUN01 source
ea2e8fa064cad188e4477d8b534692012083768a; actual dispatch pins the scope commit.

Value: a source-bound draft is really saved and read back with the same bytes/hash,
and a stopped source prevents later model/verification use while owner history
remains. Saving does not attach the artifact to a Step or complete the Goal.
The actual connection test is MEM -> TSK returned mock compose -> started Step ->
ART save -> C11 -> source stop -> denied use / retained history. This is scoped
local preparation, not the complete compose/verify/complete product path.

No VER, semantic check, Goal completion, current artifact-set attachment, new MOD
ledger/recovery, provider, UI, real files/services, live DB, schema migration,
scheduler, new auth/cost or external publication. Use Python stdlib and temporary
SQLite only. Do not search/read old PAL. Unknown old calls remain untouched.

## Ownership and public interface

Original CO SWE task remained unknown without returned files. Under the existing
owner fallback instruction, isolated native Sol6.1 authored pal/artifacts_v5.py,
tests/test_artifacts_v5.py and ART01-IMPLEMENTATION.md; independent Astra approved
exact98b8f12. SOL owns integration/common records, with separate Sol review of
TSK/RUN and actual connected tests. See ART01-MILESTONE and verification evidence.

ArtifactStore(connection, *, authorize_save, source_gate, id_factory=None,
clock=None) initializes only v5_art_ tables. The supplied SQLite connection is
idle with isolation_level=None; invalid host configuration is a programmer error.
Default IDs are host UUIDs and observed_at is host UTC; injected factories are
trusted deterministic test/host code, not model authority.

- save({key,work_ref,step_id,content,media_type,source_refs}) -> Result exactly
  {artifact_ref,hash,bytes}. Strict C08 shape, existing WorkRef/Ref/Result. WorkRef
  counters fit SQLite integers. prepare_content checks exact UTF-8 bytes/1MiB/type;
  use it without rewriting the helper. Reuse check_bytes for saved-body readback.
- get_by_key({key}) -> Result of the original receipt, or not_found. Read-only
  historical receipt, not current authority or permission to reuse its content.
- read({ref}, *, purpose=model_context|verification|user_view) -> Result of C11,
  with ref/content/media_type/hash/observed_at/work_ref/source_refs/usable. Omit
  absent version. Only artifact kind; known unsupported kinds are unavailable.
  purpose is a trusted host argument; wrong host purpose is a programmer error.

Input objects are closed, IDs nonempty strict UTF-8, bool excluded from integers.
Canonical object order may differ; array order remains input identity. Invalid
input -> invalid_input; absent saved identity -> not_found; changed key input ->
conflict; stale/denied/conflict from the TSK gate are preserved; storage/gate failure
-> bounded unavailable. No raw exception or supplied body in error messages.

## Save transaction and collaborator contract

Prepare/validate exact input and bytes before BEGIN IMMEDIATE. Compare canonical
input on key replay before current authority checks; same input returns its saved
receipt without new effects even after source stop. An old receipt does not bypass
current C11 checks. Failed requests do not burn the key. One immutable save per
step_id: same step with a different key returns conflict. Host key is canonically
dumps(['C08.save',work_ref,step_id]); tests use that exact host key, not a model ID.

Within the ART transaction call the exact trusted TSK public callback:

    authorize_save(connection, {
      'work_ref': WorkRef JSON, 'step_id': str,
      'action': {'kind':'compose','content':str,'media_type':str,'source_refs':[Ref]}
    }) -> Result[{'source_refs':[Ref]}]

It requires this same active connection; no BEGIN/COMMIT/ROLLBACK and no writes.
It confirms current running WorkRef/owned lease/no pause or drain, returned call,
started compose Step, exact stored Step.action, source membership/current usability.
Its output is a conservative dependency union including every actual call-supplied
Ref, not merely model-selected compose.source_refs. This prevents omitted citations
from hiding a stopped input. Require a valid nonempty dependency list containing
all request source_refs. This slice permits record refs only; other dependencies
are unavailable until their owners are integrated. Store this authoritative union
and return it as C11.source_refs; it may exceed the input source_refs.

Recheck required source_gate(connection, tuple[Ref,...]) on this same transaction.
Exact outcomes available/not_found/denied/unavailable match MEM. Both callbacks are
trusted same-DB read-only host methods. Savepoints plus total_changes may detect
violations but are not an arbitrary-code sandbox or a rollback guarantee after a
malicious collaborator commits. Abort on ended transaction, mutation or bad return.

Mint one ID and persist immutable BLOB, metadata, WorkRef, step ID, canonical input,
dependency refs and original receipt atomically. No TSK state or event write from
ART. Preserve both WorkRef and step binding for later attachment/recovery, but do
not implement that authority now. Rollback BaseException and propagate interruption;
ordinary failures return bounded unavailable. No filesystem or external I/O in TX.

## Current readback

Read body/metadata/dependencies and source availability in one short owned read
transaction. read requires an idle supplied connection; no nested transaction.
Validate stored metadata and bytes/hash/count before returning content. Missing or
corrupt metadata/provenance -> unavailable; never repair on read or trust display
JSON as canonical proof. Source denied -> model_context/verification denied;
user_view returns history with usable:false. Source not_found/unavailable ->
unavailable, not a guessed stopped state. Historical epoch is reported as saved;
read does not authorize adoption into a new epoch. get_by_key never returns body.

## Integration owned by SOL

Extend TSK begin_step to permit validated compose, and implement the exact read-only
authorize_artifact_save callback above. This slice's finish_step explicitly refuses
compose until artifact attachment is implemented; it must not silently finish an
unbound draft as though it were lookup. Root's existing MockRunner report/lookup
scope remains; connection tests explicitly own mock call/end/compose start/save.
No ad-hoc SQL step insertion counts as real TSK integration. Source dependencies
are already registered at call admission, so actual MEM stop invalidates the work
and later C11 checks the saved dependency union. No new global invalidation engine.

## Checks and return

CO unit tests can use :memory: SQLite so its restricted verifier does not require
filesystem writes. Root independently verifies real temporary-file reopen and two
connection orders; keep those results separate from CO verified. Test strict wire,
exact empty/Unicode/newline/1MiB content, receipt replay/changed identity, wrong step/
work/action, conservative provenance, stopped/failed gate, ID collision, atomic
faults after INSERT, process interruptions, metadata/body corruption, and no data
or raw errors leaked by failures. Tests must exercise public boundaries, not merely
repeat implementation details. Real MEM/TSK consumers and disk/lock tests are SOL's
acceptance obligations. Return exact diff, command/results, and remaining limits.


## SWE consultation disposition before dispatch

The callback method is exactly TaskStore.authorize_artifact_save(connection, request),
injected as ArtifactStore(..., authorize_save=tasks.authorize_artifact_save).
No alias, keyword-shape variant or synthetic-only signature is accepted.
Unknown work/step is not_found; revision/epoch mismatch stale; absent/wrong lease
or out-of-call source membership denied; non-running/control intent/non-started
step/non-returned call/canonical action mismatch conflict; missing call/corrupt
metadata/non-record provenance unavailable. Preserve Result failure codes while
using fixed bounded error text. Do not forward arbitrary collaborator messages.

get_by_key requires an idle connection and returns the exact original three-key
receipt value; it does not read content or re-authorize use. read has the exact
eight C11 keys stated above, no version; historical WorkRef/time remain unchanged.
Stored replay metadata must still have the declared shape and valid hash/count.

A started compose Step intentionally cannot finish in this storage stage. Tests
retain it or use an explicit fenced pause/cancel/stop release; they never fake a
successful yield/attachment. This stage is not a usable compose loop. The next
required stage binds the artifact into TSK's current set and connects RUN, together
with kind-aware source checks and RUN01/2 persistence handling. Only that stage
can establish mock compose -> saved and attached draft. VER/complete remain later.
SWE's statement that a failed release can be reclaimed is not adopted: failed is
terminal; only a valid control/drain transition can requeue under current TSK.
