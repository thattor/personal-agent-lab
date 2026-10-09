# PRI02-N/1 — distinct native lifetime and dynamic text connection

SOL freezes this technical slice under D049 after the received Opus two-stage
review, Astra's N host preparation and Sol's installed public-API comparison.
It follows the approved product goal; it adds no task type, service, auth or cost.
Stage T's sole actual call is UNKNOWN and remains consumed/untouched. Its failed
original-prompt comparison is not relaxed or retried. N independently qualifies
the existing ACP completion/EOF/wait path and dynamic observer; it cannot use T
as a successful prerequisite or inherit its weaker ending. All fixtures below
are explicitly fixtures, never provider proof.

## Ownership and dependencies

SOL owns this contract, native Primary integration, shared SQLite/C14 changes,
actual qualifications, canonical records and adoption. Independent Sol owns
fixed tests before source. CO SWE-2 High owns only pal/native_call_v5.py under
NATIVE-CALL01/1. Astra owns only tools/native_devin_text_v5.py under NATIVE-ACP01/1.
Each source writer uses an isolated checkout at the assigned full commit. A
different execution context reviews final source. No concurrent writes to the
same file, shared DB, runtime, capacity ledger or canonical document.

Inputs: current PRI01/1, PRI01-WIRE/1, NATIVE-TEXT01/1 and the exact installed
CO0.4.5 public adapter/host/capacity/delegation APIs. No old PAL code or DB.
PAL modules use the standard library only and import no CO module. The external
tool composes the existing public APIs; it is not another task/controller engine.
No automatic resume/respond/reexecute, model switch, mock fallback or refund.

## NATIVE-CALL01/1 pure host values

Module pal/native_call_v5.py exports NATIVE_PROFILE_ID =
`co-devin-acp-dynamic-text/1`, NativeProfile, NativeReturned, NativeNeverEntered,
and validate_native_evidence. These are trusted in-process host values, not
deserializers for model JSON, credential isolation or actual provider authority.

NativeProfile(*, model_id, qualification_sha256, evidence_kind) is immutable;
model_id must be exactly swe-2-high, qualification_sha256 exactly64 lowercase
hex, evidence_kind fixture or native_profile. Its id is the fixed profile above.
Its profile_sha256 is SHA256 of sorted compact UTF8 ensure_ascii=False JSON of
{id,model_id,qualification_sha256,evidence_kind}. to_json returns that closed
mapping plus profile_sha256; callers cannot override the ID/hash. No fake
verified/provider-stopped flag. Tests using fixture stay fixture.

NativeReturned(*, capture, cessation) retains an immutable defensive snapshot
of the closed NATIVE-TEXT01 capture and original cessation mapping. It exposes
text and validate(*, request_sha256, profile). A request digest is SHA256 of
canonical C15 JSON (pal.contracts_v5.dumps). validate returns closed evidence:
version=NATIVE-CALL01/1, request_sha256, profile_sha256, qualification_sha256,
evidence_kind, model_id, attempt_ref, output_sha256, utf8_bytes, chunks,
cessation, cessation_sha256 and evidence_ref. No output text in evidence.

Capture keys are exactly text/output_sha256/utf8_bytes/chunks/request_sha256/
profile_sha256/attempt_ref/cessation_sha256/evidence_ref. Validate UTF8 text
1..32768 bytes, exact text hash/byte count, exact integer chunks1..2048, exact
request/profile/attempt/ending cross-bindings and the original cessation checks
already frozen in NATIVE-TEXT01. Reuse that validator instead of weakening its
model/mode/capability/end_turn/effective_model/EOF/PID/wait/no-tools/permissions
requirements. Closed keys and exact scalar types are mandatory. Preserve actual
negative owned exit after original end_turn cleanup; it is not generic failure.

validate_native_evidence(evidence, *, request_sha256, profile) repeats strict
closed-schema/binding/cessation consistency without text and returns a defensive
mapping. Missing/deleted/partial/mismatched records raise a fixed safe ValueError.
This is durable local consistency under a trusted host; it never reconstructs a
live ACP transport or proves remote cessation on restart. Coordinated host/DB
forgery is outside this same trusted-host scope. No from_json native authority.

NativeNeverEntered(*, request_sha256, profile_sha256, evidence_ref) is a fixed
safe exception carrying only bounded hashes/owner evidence. The bridge may emit
it only for its own pre-entry refusal or exact public NeverStarted for the same
request. It is not an error-string heuristic; generic failures are unknown.

## NATIVE-ACP01/1 external composition

NativeDevinText(*, runtime, state_dir, attempt_root, executable, credential_files,
profile) is a non-callable provider object. It exposes preflight() and
invoke(request, *, on_enter). Root supplies an already evaluated NativeProfile;
a fixture profile alone never establishes qualification. Module import/preflight
must not run provider generation or create an alternative runtime/state/ledger.
All raw material remains in exclusive0700 per-call attempt directories.

Load only the installed exact public CO0.4.5 modules from the configured runtime;
verify origin/version and hash the relevant implementation files. Use existing
NativeCandidates.selection with fixed implement=devin/swe-2-high/coding pin,
fresh official CLI version/auth/model-catalog Free checks and exact measurement
binding. Never enable paid fallback or read credential contents. Credential
targets are explicit existing files checked by metadata only. Preserve original
launch_environment, check_launch_template, delegation and model validation.
Public selection's measurement describes normal CLI route eligibility, not ACP
or equivalence to the separately supplied current executable. Resolve the actual
official devin executable and bind its current version/hash/Free metadata to
this N envelope; the actual original ACP host then qualifies that executable.
Do not inspect private NativeCandidates fields or run extra infer probes to
pretend normal ATIF measurement qualified ACP.

Fixture seams are _load_runtime(runtime), returning a namespace with contracts,
DevinTextHost/DevinHostConfig/DevinAdapter/DelegatedScope/CapacityLedger/
PooledAdapter/gate/check_launch_template/launch_environment/NativeCandidates;
and _fresh_pin(api, state_dir, executable), which performs metadata-only checks.
Its exact closed mapping keys are route/model/version/cost_tier/
measurement_digest/selection_digest/runtime_hashes/wrapper_sha256/
capture_sha256/executable_sha256. measurement/selection use sha256:lowerhex64;
the other hashes are bare lowercase64 hex. runtime_hashes is a nonempty strict
relative CO module path -> SHA mapping; wrapper/capture identify current PAL
tool and buffer bytes. preflight returns a defensive copy of the exact fresh pin.
qualification_sha256 is SHA256 of sorted compact UTF8 ensure_ascii=False JSON
{version:NATIVE-ACP01/1,profile_id:co-devin-acp-dynamic-text/1,pin:closed_pin}.
preflight must compare that current envelope to NativeProfile.qualification_sha256.
The envelope is an immutable qualification candidate identity, not proof that
qualification already succeeded. Root observes the separately frozen actual N
case and its original native receipt before native product adoption; neither
profile label nor a supplied digest can substitute for that actual proof. Source
or selection drift invalidates the envelope. on_enter receives an exact plain
dict with run_id/job_id/attempt_id strings for the original public native ref.

The canonical ledger is the existing passwd-home/.co-task-host/capacity.db.
Before any CapacityLedger constructor, require the existing real private parent
and regular uid-owned0600 single-link file. Missing/replaced targets refuse;
do not initialize/reset a ledger. Use public admission.gate for the actual cwd,
and public CapacityLedger/PooledAdapter with that same exact canonical path and
devin.acp key. All ordinary CO calls continue sharing its12 slots. Only public
exact NeverStarted or StopReply.CONFIRMED releases this wrapper's own lease.
Generic terminal state, timeout, close, parent death or local wait alone do not.
No direct SQL/state edits, private method/field changes, alternate pool or engine.

Create one public AttemptRef/Job/ExecutionConditions/ExecuteRequest and one
DevinTextHost(DevinHostConfig(...), expected_response=None). The native workspace
is an empty owned child directory, separate from protected journal/ledger/state.
Job.output_candidate=False, context={}, capability devin.text.only, plan mode,
no session MCP/client filesystem/terminal tools. Conditions bind exact model,
workspace and local environment/control-evidence refs. Protected targets include
the call journal and canonical capacity ledger outside that native workspace.

Construct one public DevinAdapter with unchanged host.transport and original
host.verify_text_cessation. Stacked verify_host calls host.verify FIRST, then
opens NativeTextBuffer exactly once at phase=session immediately before prompt.
Stacked observe_model calls host.observe_model FIRST on every update, preserving
current_update, then forwards the full fields to that buffer. Adapter's original
outer-session check owns correlation; do not substitute a transport or pretend
the callback itself contains the outer envelope. Ignore preprompt/thought/user
text; reject over-cap/nontext/malformed or unbound output. Buffer finish occurs
only after the original verifier has validated completion plus trailing frames
to EOF and waited its exact owned CLI. No text returns before that ending.

Prepare/fsync request/prompt/profile/runtime/pin hashes and immutable native
attempt refs. Conservatively journal possible entry and call on_enter(attempt_ref)
once BEFORE PooledAdapter.execute. PAL callback commits its own marker before
native I/O; its failure means no execute. The bridge also fsyncs its own marker.
Any parent-death/uncertain marker/send gap stays unknown; no marker implies no
provider entry only when this live wrapper knows execute never occurred.

Execute at most once. Public events/status loop has an elapsed60-second deadline
and a short bounded poll; RPC handshake timeout is not the whole-call deadline.
At expiry/error, request supported stop once and retain its original outcome;
never resume/respond/reexecute. Await only bounded owned cleanup. No parent
stdout/raw-body echo. Capture max32768 UTF8/2048 chunks; the original ACP line,
frame, poll/drain ceilings are retained, and raw artifacts are bounded locally.

Success needs original State.COMPLETED, original end_turn cessation receipt and
matching StopReply.CONFIRMED, effective model exactly swe-2-high, no tools or
permissions, original correlation/EOF/wait, plus NativeTextBuffer.finish and
NativeReturned.validate for the original C15/profile/attempt. Persist that exact
known ending before returning. Normal-looking dicts or mocked transports never
acquire live authority. Failures after possible entry raise a fixed unknown
exception; cleanup is separate from a usable output. Limits remain native_handoff,
not OS containment, complete credential inventory, descendant or provider-global
cessation, or proof of no internal provider retries. Counting is one ACP prompt.

## Native Primary lifetime to implement after pure values

NativePrimaryHost is explicit and cannot be constructed by supplying this
non-callable provider to the default mock PrimaryHost. Reuse existing MEM/TSK/
WIRE/C14 owner logic and local MockHostSession only for local ownership/budget;
do not use that lock as native cessation. Its native session/turn/call rows carry
the distinct profile. preflight occurs before reserve; TSK reserve/consume once.
No waits inside SQLite transactions. SOL alone changes the shared host module.

Public constructor in pal/primary_host_v5.py is
NativePrimaryHost(connection, *, guard, memory, tasks, request_scope, provider).
provider is a trusted non-callable object with exact NativeProfile-valued profile,
preflight() and invoke(request, *, on_enter); no generic mock invoke parameter.
All existing PrimaryHost mock constructor behavior stays fixed. preflight runs
after bounded snapshot/source validation, before model reserve. on_enter receives
the original native attempt mapping once and commits its cross-binding/source
gate before any external execution. A NativeReturned without that hook is held.
Only a matching NativeNeverEntered may settle not_entered; wrong binding or any
other exception after invoking the provider is unknown, never mock raised.

The side table name is v5_pri_native with columns call_id/request_hash/
profile_json/attempt_json/phase/ending_json/ending_hash. profile_json is exact
canonical NativeProfile.to_json. phase is prepared/entering/unknown/returned/
not_entered, attempt_json null only before entry. The existing C15 call hash binds
both call and native side row for native profiles, remaining exactly call-only
for mock. Missing native side or an extra mock side is unavailable. Native
returned evidence is text-free NativeReturned.validate; not-entered ending is
closed {kind:not_entered,request_sha256,profile_sha256,evidence_ref}, checked by
NativeNeverEntered. ending_hash binds that exact canonical ending JSON. Unknown
has no ending/output hash. Side/call/profile/status/phase converse is mandatory.

get_turn returns existing closed status/effect_refs/reply/error shape. Native
unknown uses status=held with empty effect_refs and no model body/error details;
active entry before known ending may remain pending. Same held turn run is a
read only result. A fresh explicit turn has its own current profile/counters;
profile mismatch does not permit executing an old pending turn. Recovery of
native admitted/entering first records unknown and holds; pending/preparing
without any C15 call can fail locally. Returned-before-intent may fail locally;
applying uses only original owner lookup, never redispatch. Existing mock turn
recovery remains interrupted, and its rows never gain native authority.
Native local-adoption failures appear in recovery.failed_turn_ids, never in
interrupted_turn_ids. Mock-only recovery retains its original three-key shape.

A PRI-owned mandatory side row binds call_id/request/profile/qualification,
original attempt, entry state and exact returned evidence/hash. Ending side row,
C15 returned/output hash and turn phase/hash commit atomically. Unknown is a
nonterminal admitted turn, held on rerun/restart with no reinference/refund/
dispatch. Generic native callback exceptions never become mock raised or
interrupted. A different explicit turn can proceed under its own allowance and
actual capacity; corrupt rows and active foreign mock turns still fail closed.

Startup validates both-side hashes/profile/phase. Unknown/admitted native calls
stay held even after the local HOST lock becomes free. Returned/applying uses
only original-key owner lookup; found settles, unavailable holds, not_found
closes local adoption failed. Returned-before-intent may close local adoption
failed, preserving returned cessation. No original external request is replayed.
Controls/source-stop remain short; stopped/stale sources fence reply/effects.
Current-answer, full exposed closure and current WIRE bounds remain unchanged.

## Fixed verification and actual entry limits

Independent pure-value tests cover valid binding/immutable snapshots, closed
keys/exact types/caps/UTF8/digests/profile/request/attempt/receipt mismatch,
missing ending, fixture label, persisted evidence tamper and no raw text.
Independent wrapper tests exercise installed public hooks with explicit doubles:
no generation at construction, original verifier/observer ordering, one entry/
execute, known never-started, ordered dynamic collection, bad/missing ending,
timeout/stop/no retry, hold/no forced release, fsync failure, per-call isolation
and raw/minimized separation. These doubles prove fixtures only.

SOL separately verifies Native Primary with real temporary owners and process/
connection/control/source-stop/rollback cases, preserving full mock regression.
An independent context reviews each final source it did not author. All source
and fixed-test hashes are bound before a actual invocation; full checks must
finish successfully BEFORE dependent execution or a claim that they passed.

N transport qualification is MAX1 new synthetic dynamic request, no PAL effects,
own original request/attempt and native profile; not a retry of T's request and
not adoption of its UNKNOWN output. Root checks actual current auth/Free/slots,
source pins and independently reviewed fixtures immediately beforehand. This
case's purpose is ACP dynamic-output/correlated ending qualification. A failure
is retained with no automatic retry/fallback. Further real integrated calls are
not authorized by this technical freeze: Root first records the actual N result,
then freezes the finite acceptance cases/allowance within existing owner scope.

Return exact diff/source/test hashes, commands/exit/results and remaining issues.
Passing this slice establishes a bounded connection prerequisite, not real
Expert semantic behavior, full service activation or authentic human usefulness.

## C083 observed failure and bounded source correction

The original N MAX1 invocation at source190fcc4 entered and is UNKNOWN. Its
supported stop returned ERROR without evidence; one shared Devin slot remains
executing. Preserve the original request, entry, workspace and failed result.
No reclassification, forced release, resume, cancellation or original-request
retry follows from a later diagnostic or source repair. Full1155 PASS and the
separate five actual owned-process fixture cases do not qualify the provider.

Independent read-only constructor fixtures reproduce a concrete version-boundary
mismatch. Public AcpTransport invokes `devin version`, comparing its stripped
stdout exactly before ACP spawn. The wrapper supplied semantic `3000.11.3`;
actual metadata is `devin 3000.11.3 (9c803229faa4)`. The original OperationReply
was not saved, so this reproducible mechanism does not identify the unique cause
of that original call or create a NeverStarted receipt retroactively.

SOL adopts Astra's minimal correction within NATIVE-ACP01/1: retain the closed
pin schema and semantic version, add the fixed full transport-version constant
`devin 3000.11.3 (9c803229faa4)`, check the original `version` metadata against
that exact value in _fresh_pin, and pass the full constant to original
DevinHostConfig.expected_version. The wrapper hash binds the constant and the
executable hash binds the actual binary. A different build is refused and needs
reevaluation. No original CO transport, verifier, runtime or state is edited.

Add bounded local original-observation retention before cleanup. After execute,
validate OperationReply's exact type/ref/status and save attempt_ref/status/reason
plus a matching NeverStarted evidence ref or null, without resume_state or another
request copy. Preserve only the status already obtained by the ordinary loop.
On failure, save the cached state or null, public protocol_diagnostic or a fixed
unavailable marker, and the original bounded host.observation. Do not poll status
for diagnosis: status pumps protocol and can send during bootstrap. Save the
supported stop's original outcome once, then close. A diagnostic write failure
stays UNKNOWN and cannot suppress the single supported cleanup attempt or cause
another execute. Raw observations stay exclusively local; public summaries carry
the necessary verified facts and hashes. No arbitrary exception/native text is
converted into cessation authority.

Separate fixed fixtures precede this source correction; exact source review and
finished full verification precede any later entry. The original N allowance is
consumed. A new candidate's distinct finite qualification requires its own explicit
Root freeze after this checkpoint/design assessment; this amendment authorizes
source preparation only, not another actual prompt under the old case.

C083 correction receipt: exact candidate808b05f/SHAac1250 is independently
APPROVED with fixed35 and Root full1161 PASS30.939s/exit0. Local execute.json
closed keys are {attempt_ref,status,reason,never_started_evidence_ref}. Local
diagnostic.json closed keys are {attempt_ref,last_status,protocol_diagnostic,
host_observation}; last_status is null or the cached closed {attempt_ref,event_id,
state,evidence_ref}. It never adds a status call. Persistence/protocol diagnostics
failures preserve UNKNOWN and one supported stop, without reinference/refund.
Original raw receipts remain private. This establishes source preparation only;
no new actual native qualification has run under the corrected candidate.
