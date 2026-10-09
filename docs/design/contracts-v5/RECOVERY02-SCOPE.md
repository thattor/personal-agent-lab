# RECOVERY02/1 — frozen saved compose recovery

SOL adopts qualified actual CO Claude Opus5.5 REFINE F1–F10 in
`evidence/operations/recovery02-20261010/opus-design-review.json`; the host-bound
nine input blobs and actual report-producing model are in design-disposition.json.
Root reconciled those readings with integrated RECOVERY01 TSK8f20d0. This scope
supersedes the provisional RECOVERY02 proposal. No EXE, provider or Primary
execution, live DB migration, new auth/cost/service, completion authority or whole
C13/product acceptance. `started operate` still holds external_tail.

ART owns artifacts_v5.py and all ART SQL. TSK owns tasks_v5.py and all settlement,
adoption/replay integrity. Root owns shared key, RUN integration, actual process
tests and canonical records. Separate contexts author fixed ART and TSK tests
before source, then independently review exact implementation bytes. No same-file
concurrent writes. Use actual temporary/in-memory v5 owners; no mock recovery proof.
Assignment pins its frozen Git base and explicit read/write paths. Return diff,
source hash, unchanged fixed/affected tests and remaining limits. Standard library.

## ART read-only callback

`ArtifactStore.lookup_saved(connection,{key,work_ref,step_id,action}) -> Result`.
Exact same active isolation_level=None connection, otherwise raise ValueError as
inspect does. Closed request, strict original WorkRef and nonempty UTF8 identities;
action must parse as the closed ComposeAction with its supplied source_refs.
Bad public input is invalid_input. No authorize_save, body return, ids/clock,
BEGIN/COMMIT, writes or replay creation. Caller transaction remains owned by caller.

Rebuild original C08 input as `{key,work_ref,step_id,content,media_type,source_refs}`.
Use exact ordered source list including duplicates; compare dumps byte-for-byte
against stored input_json, not a set. Read expected-key replay. Missing key AND no
body for this unique step_id is definitive not_found; body without expected key
is unavailable. Found canonical input mismatch is conflict. Validate _saved_receipt
and _loaded, original key/body/step/work/replay binding, exact immutable bytes,
hash/length/media/UTF8. A dangling receipt or foreign step/work body is unavailable,
never not_found. Required receipt projection is the existing closed inspection
value `{artifact_ref,work_ref,step_id,hash,bytes,source_refs}`. Its WorkRef remains
the original claim epoch. Gate all stored producer refs with existing guarded
same-connection source_gate: available succeeds; denied is denied; missing or
unavailable is unavailable. Ordinary exception yields bounded unavailable;
BaseException propagates after owned savepoint cleanup. Callback writes/commits
are detected; a committed hostile collaborator cannot honestly be rolled back.

## Shared immutable save identity

`pal.artifacts_v5.artifact_save_key(work_ref,step_id)` is the single pure function
returning dumps(['C08.save',original WorkRef,step_id]). Root has replaced RUN's
literal derivation with this function. TSK must import/use this same function.
No changed key, new receipt or caller artifact selector. A fixed case binds both
paths. ART absent-key/body distinction prevents key drift from discarding output.

## TSK recovery only

Add optional constructor collaborator `artifact_lookup=None`. It is callable or
constructor rejects. No callback keeps existing artifact_tail hold. Ordinary
finish_step/authority stay unchanged. Extend RECOVERY01 recover({key,lease_id}),
its existing transaction and same-key replay; public Step/Result/settled wires
stay unchanged. An artifact collaborator is never execution authority.

Order under one BEGIN IMMEDIATE: all original managed session/orphan/claim,
historical Step/call/reservation and artifact-set validation; latest intent;
current TSK source gate; exact ART lookup; projection/binding validation; premint;
settlement writes. Reconcile historical managed owner/claim checks unchanged.
Require started compose, original empty result_refs, no error key, returned linked
call, closed parseable ComposeAction, unique step/call/index/lease binding. Source
refs are nonempty duplicate-free records; required <= original call.sources <=
registered. Root confirmed authorize_artifact_save returns call.sources verbatim:
ART producer projection must equal this ordered list, as well as original WorkRef
and step_id, valid artifact/hash/bytes and no existing set/adoption artifact/Step.
No _register write: provenance is already registered and validated.

Definitive TSK ineligibility after full structural validation: replacement
revision, cancel intent/terminal state, paused state or pause flag. Skip new source
gate and ART lookup, abandon started compose, retain ART history, settle with
RECOVERY01 latest-intent rules. Adopt deliberate conservative pause non-adoption.
Same-revision attach/drain does not change purpose/conditions: allow adoption,
leave pending_inputs unconsumed. A valid open question alongside this orphan's
started compose is inconsistent: hold unavailable without settlement.

Otherwise TSK gates union(current required, original call.sources) once. Denied
means definitive ineligibility/abandon; missing/unavailable means artifact_tail
hold. Do not regate physical cleanup. ART success is considered only after TSK
available. ART denied/unavailable then is inconsistent and holds. ART not_found
abandons/settles without save or inference. conflict, invalid_input, exception,
corrupt projection or comparison mismatch hold; no write/replay/epoch/event.
Ordinary callback exceptions hold; BaseException rolls back and propagates.
Guard ART callback against writes/transaction replacement using existing trusted
savepoint/total_changes discipline. Held recovery may retry the same key later.

On adoption, atomically finish original Step with sole ART result_ref and original
WorkRef; insert next artifact-set row; close old lease; fence current epoch as
RECOVERY01; keep counters/reservations/calls/ART rows unchanged even at zero
remaining budget. No call, Step, reservation, refund, new source or model callback.
All identities are safely preminted before settlement writes. Roll back ordinary
faults/BaseException. Latest intent settles queued/paused/etc as RECOVERY01.

## Checked internal adoption, replay and one event

TSK owns `v5_tsk_recovery_adoption(step_id PK,call_id UNIQUE,lease_id UNIQUE,
artifact_id UNIQUE,origin_work_json,adopted_work_json,recover_key,event_id UNIQUE)`.
It also records recover_key, adopted_step_id (nullable), event_id in an internal
TSK recovery-replay binding, connected to existing `v5_intake_replay` command
`recover`. Public settled shape is unchanged. Pre-RECOVERY02 ordinary recovery
receipts remain historical; no retroactive adoption enrollment.

Extend artifact-set/recovery validation bidirectionally. For each adoption: Step
is finished compose with exactly its artifact, Step.call==call_id==call.step link,
call.lease==lease_id, returned call.work==Step.work==origin==managed lease claim;
same Goal/revision adopted, adopted.epoch>origin.epoch and equals its stored
recover settled work_ref; exactly one set row; recovery replay input links that
lease/key and result settled; its internal adoption reference equals this Step;
event exists with matching adopted WorkRef and refs [artifact]. Conversely every
internal replay adoption reference and every recovery adoption state event has
the corresponding row. Validate duplicate/missing/foreign links and row shape.
Ordinary finished compose with neither adoption nor marker remains valid. This
does not claim to detect coordinated forgery of all trusted local DB evidence.

Reuse one RECOVERY01 C14 state event in settlement. Adopted text is fixed
`mock saved draft recovered`, refs [artifact]; abandoned/ordinary recovery keeps
`mock execution recovered`, empty refs. The fixed adopted text is an independent
marker checked against adoption/replay, so deleting one annotation is detected.
No body, clock, progress/result event or completion announcement. Same-key replay
returns original settled value with zero new rows/epoch/event and still checks
managed guard/DB and stored recovery integrity. Different input conflicts.
Current get_work/current_artifact_refs and execution context expose the attached
ART through existing fields. VER unchanged: old verification is historical;
only fresh verify with new WorkRef/key may complete through ordinary checks.

## Fixed acceptance and Root connection

ART fixed cases: exact match zero changes/no body; definitive absence; dangling
receipt/body-without-key/foreign body; changed content/media/order/duplicates;
corrupt bytes/hash/UTF8/binding; gate denied versus missing/unavailable; wrong/idle
connection; mutating/committing gate and BaseException cleanup. Existing ART green.

TSK fixed cases: adopt once exact rows/counters at exhausted budget; same-key replay
and changed-input conflict; absent receipt abandons; each uncertainty holds zero
writes then available retry adopts; replacement/cancel/terminal/pause/flag/source
denied abandon with no lookup; projection/status/error/provenance mismatch;
missing/tampered side/replay/set row unavailable; ordinary history valid;
no collaborator still holds; premint/write fault and BaseException rollback.

Root actual fresh SQLite + HOST/TSK/ART/VER/RUN: process crash after ART COMMIT
adopts exact body; fresh VER under fenced/current epoch accepts old ART; old VER
invalidates/cannot complete; crash before save abandons and fresh call remains
within limits; second-connection pause/change/cancel/stop wins; shared save-key
identity; unchanged HOST tests/no startup save/call/reservation. Narrow owner
green is not the whole C13/PRI/provider/usefulness goal.
