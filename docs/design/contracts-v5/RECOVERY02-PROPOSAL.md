# RECOVERY02 proposal: saved compose tail

Proposal only; Root/Opus adoption required. Observed base:
`73b209a486ea62f3e9f76318e8ad8bf14255b1f5`. RECOVERY01 remains the frozen authority;
this note proposes only resolution of its `started compose → artifact_tail` hold.
No EXE, PRI, provider recovery, completion grant, or product acceptance is added.

## Observed seams

ART `get_by_key({key})` requires an idle connection and returns historical receipt
metadata. It cannot be called inside TSK's settlement transaction. ART `inspect`
already uses the supplied active connection, checks immutable body/UTF8/hash/length,
metadata and original replay binding, and gates stored producer records. TSK must
not query ART-owned tables directly. RUN's save key is derived from the original
WorkRef and step_id; its original closed save request includes the compose content,
media type and ordered source_refs. Recovery must use that original identity.

TSK ordinary finish requires live authority. Its artifact set validates finished
compose by Goal/revision, allowing older epochs. Step.call is UNIQUE; a fabricated
call or rewritten WorkRef cannot create a truthful ordinary recovery Step.

VER `verify` already accepts ART metadata with the same Goal/revision and epoch
less than or equal to the current WorkRef. It checks the current ordered artifact
set, conditions, required records and all ART dependencies. No VER wire change is
needed. The old verification receipt remains historical; fresh verification must
use the new WorkRef/key. Adoption itself conveys no semantic completion authority.

## Small ART-owner callback

Proposed constructor collaborator on TSK: `artifact_lookup`. ART implements
`lookup_saved(connection, request)`; name is provisional, not an existing API.
Precondition: the exact ART-owned supplied connection, isolation_level=None,
active caller transaction. Wrong connection/idle preconditions refuse consistently
with `inspect`. No BEGIN/COMMIT, writes, body copying, new receipt, authority-save
callback or model action. Caller and ART enforce trusted callback transaction
ownership; ordinary exceptions become unavailable, BaseException cleans owned
savepoints then propagates. A collaborator COMMIT is detected but cannot honestly
be rolled back after it committed.

Closed request:
`{key,work_ref,step_id,action}` where action is the exact closed original compose
Action. ART reconstructs its canonical original save input from this binding and
compares byte-exact content/media_type and ordered source_refs, including duplicate
identity. Key alone is insufficient. Success is the closed existing inspection
projection `{artifact_ref,work_ref,step_id,hash,bytes,source_refs}`; `source_refs`
are the full conservative recorded producer dependencies, not just selected refs.
The result's WorkRef remains the original WorkRef. ART validates the unique replay,
receipt/body identity, original input, immutable body and metadata before success.
It gates those producer records using the same connection under the caller's lock.
TSK compares returned provenance to the saved original C15 call as well.

Error distinctions: genuinely absent key AND no saved body for the original Step
is `not_found`; contradictory body/replay, dangling receipt, malformed metadata,
unknown lookup outcome or missing dependency is `unavailable`; stopped dependency
is `denied`; valid key belonging to different input is `conflict`. A body for this
Step with a missing expected receipt is corruption, never safe absence. ART owns
this distinction and performs its own SQL. TSK supplies original deterministic key
and binding; no caller-supplied artifact identifier may substitute for the lookup.

## TSK settlement extension

Extend RECOVERY01's existing closed `recover({key,lease_id})`, not ordinary
`finish_step`, with the new optional collaborator. No collaborator means the
existing artifact_tail hold. Validate managed session/death fencing, enrollment,
registration snapshot, original lease/call/reservation/Step and current revision
before any new writes, exactly as RECOVERY01. A compose Step must be started,
closed, linked to the returned original call, with original empty result_refs and
unchanged action. Preserve old Step/Call WorkRefs and all consumed counters.

Same Goal/revision eligibility means no changed purpose or completion conditions,
valid old authority snapshot, full producer refs consistent with the original
call and registered provenance, and current required sources available. Compare
immutable revision data rather than inventing a semantic equivalence test. Gate
current required and full producer refs within BEGIN IMMEDIATE before attachment.
The artifact metadata epoch must equal the original Step epoch, never the future
fenced epoch. Absent or malformed original action/key binding fails unavailable.

Success with an eligible receipt: finish the original Step using its original
WorkRef and sole artifact result_ref, insert one ordinary artifact-set row for
that Goal/revision, register validated dependency provenance, and insert one
TSK-owned recovery-adoption row binding original lease/call/Step/artifact/origin
WorkRef to the resulting current fenced WorkRef, recovery key and event identity.
This row explains the different epoch; it grants no reusable execution authority.
Do not alter ART body/receipt/origin metadata or manufacture a new call/reservation.
Finish and attach atomically with lease cleanup, epoch fence, current C14 event,
recovery replay and adoption binding. Premint bounded identities under the existing
callback guard before settlement writes. On failure roll back the entire operation.

Current artifact-set validation must additionally validate every recovery-adoption
row's bidirectional binding, epoch transition, Goal/revision and Step result; it
must distinguish recovered versus ordinary finished compose. Do not merely insert
an unchecked annotation. Existing old-epoch finished artifacts remain valid history.
Ordinary finish still rejects stale authority. Historical Step reads show the
original WorkRef, with no new fields in the closed Step wire shape. Current context
exposes the adopted artifact through its existing artifact_refs only.

Keep RECOVERY01's settled receipt shape. Existing Step result/current artifact
context return the ART Ref; no new model-facing Ref. Freeze one C14 event with the
artifact and recovery explanation before coding. Replay is historical, never new
body permission. No extra charge, refund or inference.

## Latest intent and unsuccessful lookup

Change to a higher revision or cancel/terminal intent: clean up and abandon the
original started Step without adopting into either revision. Preserve saved ART as
history. Pause/pause flag: settle paused and abandon this uncommitted Step; do not
attach on behalf of paused work. Shared source stop/denied provenance: abandon and
clean up with existing latest-intent state logic, not permanent occupied hold.
These are definitive ineligibility, distinct from uncertainty. No old revision is
revived, no old failure applied to its replacement. Proposed pause non-adoption is
a deliberate conservative choice requiring Root freeze, rather than assuming
that pause itself changes the revision.

For eligible unchanged work, authoritative ART not_found permits safe abandonment
and settlement, no re-save of retained compose content and no new model call.
Unavailable/conflict/corrupt/missing-source/unknown outcome retains artifact_tail
hold without writes/replay/epoch/event; operator cannot silently discard uncertain
saved output. Denied may safely settle without body adoption after full structural
validation. No read-history availability override applies to new adoption. If
latest intent already definitively forbids adoption, physical cleanup should not
require a successful source gate or successful ART lookup: RECOVERY01 cleanup
already preserves provenance without regating it. Corrupt TSK links still refuse.

## Alternative and consequence

A fresh recovery Step requires new non-C15 origin semantics and changes to call
uniqueness, validators, charging and model context. Prefer the original Step plus
checked side binding. Freeze the narrow exception: a compose Step can finish after
its epoch ceased solely through managed startup adoption; ordinary authority does
not change.

## Fixed acceptance and ownership

ART owner: active-connection exact request/binding; canonical duplicate/order
identity; receipt reply-loss; body bytes/hash/media UTF8; missing key/body versus
missing receipt; stopped versus missing/corrupt refs; mutating/committing callback
and BaseException guards; no durable read mutation. TSK owner: saved started tail
adopts once with original Step/Call WorkRefs; counter values unchanged even when
budget exhausted; exact artifact set and side binding; fresh VER accepts oldepoch
ART and old VER cannot complete; absent receipt abandons without save; unavailable
holds without replay; pause/change/cancel/shared-stop do not adopt. Deterministic
ordered two-connection controls prove latest intent wins before settlement.

Root tests actual ART+TSK+VER on fresh temporary SQLite: boundary crashes, commit
reply loss, premint rollback, history/readback and next-revision budget continuity.
No RUN save/Expert/reservation during startup. HOST tests stay fixed. No full C13,
provider or usefulness proof follows.

Open freeze decisions are the callback/API error taxonomy, precise side-table
integrity checks and public C14 event, and definitive pause/ineligibility settlement
policy. This proposal has no code/test validation or adoption claim; source reads
establish feasibility only. Root must reconcile these with RECOVERY01's adopted
implementation after it exists, without relying on uncommitted parallel work.
