# PRI03-NATIVE-EXPERT/1 — bounded native Expert owner and runner

SOL freezes this source/fixture slice at base6ae725a after the completed actual
AGY `claude-opus-5-5-high` checkpoint review. The report is REFINE; the concrete
resolutions below, rather than all reviewer suggestions, are adopted in D050.
The original preparation note at190fcc4 is retained as proposal history. Current
source is808b05f plus independently fixed stop-order tests; no real Expert entry
is authorized by this source contract.

## Goal and exclusions

Connect a native, typed ending to the existing TSK-owned Expert call, durable
original output, current Action adoption, ART, fresh structural VER and readback.
Preserve existing mock defaults and managed lifetime, C13 latest controls and
RECOVERY02 original artifact adoption. Ordinary provider exceptions must never
become mock raised/interrupted or justify releasing an unknown native lease.

PAL core uses Python stdlib and imports no CO. The external wrapper alone uses
the already qualified public CO runtime/gate/pool/ACP. No second state engine,
RUN SQL, new auth/cost/service, old/live DB, operate/model verify, arbitrary tools,
provider retry, PID cancellation, capacity override, readiness split, unknown
retirement or multi-Goal execution. This is C15 native Expert saved-result and
same-call replay preparation, not a general MOD ledger or whole-product proof.

## Ownership and public interface

TSK alone owns lease/claim/index, reservations, call status, native side data,
ending/raw-output durability, Step binding, release and recovery. RUN orchestrates
public TSK/MEM/ART/VER APIs; MEM owns source availability; ART owns original saved
bytes/lookup; VER owns fresh current structural verification. SOL owns shared
contracts/integration and final source/evidence. Each fixture uses its own fresh
file SQLite DB and temporary managed session. Existing/live DBs are untouched.

Freeze these TSK APIs, with existing Result/ErrorCode conventions:

* `admit_native_call(admission, *, c15_request, profile)`: admission has exactly
  the existing `{call_id,lease_id,work_ref,reservation_id,source_refs}` keys.
  `profile` is exactly NativeProfile, never a JSON lookalike. Return the existing
  `{call_id,status:"admitted"}`. The immutable profile/body is part of replay
  identity; matching admission replay is only a receipt, never permission to send.
* `enter_native_call({call_id,attempt_ref})`: attempt_ref has exactly nonempty
  bounded `{run_id,job_id,attempt_id}`. Recheck authority/controls/source closure
  in the owner transaction, then commit prepared→entering once. Return
  `{call_id,status:"entered"}`. Duplicate entry conflicts, including after a lost
  commit response. Base call status remains admitted until actual ending.
* `end_native_call({call_id}, *, ending)`: accept only exact NativeReturned or
  NativeNeverEntered for the original owned call/profile/request. Return
  `{call_id,status:"returned"|"not_entered"}`. Same ending is local receipt replay;
  changed ending conflicts. Recording an original ending survives later controls
  or source stop, while adoption remains fenced. A bounded local persistence
  retry of the identical ending is allowed; another provider call is forbidden.
* `mark_native_unknown({call_id})`: prepared/entering→unknown; same input replay
  is idempotent. No ending/output/refund/status interrupted or lease release.
  Return `{call_id,status:"admitted",phase:"unknown"}`. The original session owns
  the write even if current authority was fenced. Parent death need not run it:
  prepared/entering recovery has the same conservative held outcome.
* `get_native_output({call_id,lease_id,work_ref})`: current-authority, source-gated
  original-call read. Return C15 `{call_id,status:"succeeded",content,model_id}`
  only for a valid returned native call. Preserve raw bytes at rest when stale,
  stopped or corrupt, but return no body. An unfinished call is unavailable;
  source denial/current staleness uses existing denied/stale conventions.

`get_call` retains existing mock shape. Native calls additionally expose bounded
`profile_id` and `native_phase`, no body/PID/raw error; its generic `may_enter` is
false. Only the native entry API can authorize the trusted provider barrier.
Old `admit_call/end_call` refuse native call identities; a native side record
cannot be settled with a status string or downgraded to mock.

## Closed request, bounds and budget

Expert C15 has exactly `{call_id,reservation_id,role,work_ref,messages,source_refs,
output_kind}`. Fix `role="expert"`, `output_kind="expert_action"`, exact claimed
WorkRef. Index is derived from canonical call ID/lease; it is not an invented
C15 field. Messages have closed `{role,text}` with existing system/user/assistant
roles. The host constructs Action-only system text and a canonical C12 user body.
All exposed current records and eligible historical Step/answer provenance must
be in the exact ordered supplied refs, including uncited exposure. Reject stopped
historical input. Do not put ART/VER audit objects or credentials in model input.

Canonical request UTF-8 ≤65536 bytes; 1–64 messages, ≤64 distinct record refs.
IDs/attempt tokens ≤512 UTF-8 bytes. Use canonical contracts-v5 dumps and compute
request hash inside TSK. Profile is immutable and hash-validated. A candidate
profile digest is not successful real qualification. Native output is bounded
by NativeReturned: 1–32768 UTF-8 bytes, 1–2048 chunks. The entire canonical ending
evidence is additionally ≤65536 UTF-8 bytes. Raw model text never acts as proof.

Preflight occurs before TSK model reserve. Source registration/currentness precedes
reserve. Admission shares every current `admit_call` lease/index/headroom/role/
required⊆supplied⊆registered gate and consumes the one Expert model reservation
once. No additional native counter; no refund. Step debit occurs only at begin_step.
Reserved last unit remains valid. Equal admission/output replay does not invoke.

## Durable binding and integrity

One TSK-owned native side table binds canonical request/hash, exact profile/hash,
claim/lease/index/reservation/ordered sources, original registered session,
attempt/null, phase, original ending/hash, raw text/hash. Base call has an explicit
native discriminator/binding hash so deleting its side cannot turn it into mock.
The binding covers both sides; mock calls retain their original behavior.

Allowed side phases: prepared, entering, unknown, returned, not_entered.
prepared has no attempt/ending/output; entering/unknown have no ending/output;
returned has a matching attempt and validated exact original NativeReturned
evidence/text/hash; not_entered has exact trusted NativeNeverEntered binding and
no text. Unknown may have no attempt if the source/entry barrier failed before
the callback committed. Do not infer provider NeverStarted from this absence.
Typed NeverEntered only carries an actual trusted original refusal, never wrapper
metadata failure, local process cleanup or constructed model proof.

Write ending, ending hash, output/body hash, native phase, base status and their
binding in one transaction. Rollback on Exception/BaseException preserves the
prior complete phase. A lost response can replay only exact local persistence.
Do not copy raw native logs to reconstruct an omitted result.

One profile-aware integrity helper serves all consumers that treat a call as ended:
get_call, begin/finish_step, authorize_artifact_save, ask/_ready_to_close, complete,
release including old CHANGE lease, execution-context/step-sources, _old_calls,
startup/RECOVERY01/02, saved replays and derived history/events. Side missing/extra
on mock, changed request/profile/attempt/model, bool index, wrong-role reservation,
partial ending/output or mismatched hashes is unavailable before affected writes.
Validate relevant completed historical native calls too; completion is not a way
to bypass integrity. A corrupt dependency never becomes new model input or current
ART/VER/completion authority. Existing standalone readers use public owner results;
add no external SQL. Existing mock schemas/receipt identities remain unchanged.

For a native begin_step, parse the stored raw text against the stored full refs
and compare canonical Action bytes with the requested Action, or let TSK parse it.
No different in-memory Action can be attached to an ended call. Malformed Action
is known-ended failed adoption, without repair inference. Operate/verify remain
unavailable; report alone never completes.

## Recovery, controls and honest held scope

Native prepared, entering and unknown orphan calls keep the active Expert lease:
zero settlement writes, no epoch bump, Step abandonment, interrupted substitution,
refund or redispatch from acquiring the local mock lock. The conservative prepared
hold is deliberately adopted; this initial slice does not invent not_entered_local.
The provider requires durable entry before possible I/O, but an absent marker is
not the original native cessation receipt required for this contract.

Validated returned/no-Step may settle the old lease using C13 latest intent with
reason native_returned_unadopted, preserving ending/raw output. It does not parse
or adopt those bytes into a new-epoch Step. Original-call reuse is current-only.
Known ended started compose may use RECOVERY02's typed original ART lookup and
strict native binding before adopting. Unknown producer/lookup unavailable holds.
Do not redo save/model; a new epoch or artifact set needs fresh VER. Old native
status/evidence/completed facts remain immutable; append new recovery evidence.
Profile-aware fixed event text distinguishes native recovery; preserve existing
mock event/replay IDs. Event wording alone never grants recovery authority.

Pause/change/cancel/stop remain immediately recordable on separate connections.
They fence later adoption but do not free an unknown lease. Genuine ending permits
old-owned release under current C13 latest intent. Full source closure is checked
before begin/finish/save/ask/complete, not only cited Action refs.

The one active Expert lease means startup remains held and existing ready-dependent
model reservations remain unavailable. Keep public Result/error codes and existing
managed startup wire; returned held data contains identifiers/phase/reason only,
never raw text/PID/exception. Structured controls/reference-stop/read inspection
remain usable. This is a disclosed degraded state and release-relevant gap; it does
not satisfy normal conversation-while-working. PAL unknown retirement, Primary
readiness separation and new public UI wire are NOT_ADOPTED future proposals.

## Explicit runner and assignments

NativeExpertRunner lives in `pal/native_expert_runner_v5.py`. Public constructor
`NativeExpertRunner(tasks,memory,*,provider,artifacts=None,verifier=None)`; provider
is non-callable with exact NativeProfile and public preflight/invoke. `execute_next()`
accepts no Expert callback. Fixture profiles are clearly test-labelled. It owns
no SQL/private state and never uses MockInvoker or inherits its return/exception/
cessation/recovery semantics. MockRunner/MockInvoker refuse native providers.
Minimal shared context/Action helpers may be extracted by their sole owner with
unchanged mock behavior; don't duplicate the whole business state engine.

* Independent Sol owns new fixed TSK native tests and fixture setup (source locked).
* Astra owns `pal/tasks_v5.py` after those fixed tests exist, plus the necessary
  native-aware existing history consumer if independent tests expose a direct
  bypass. Root assigns any such extra file explicitly; no broad blanket edits.
* Independent Sol/another context owns runner fixed tests, separate from author.
* CO SWE-2 High is preferred for a bounded new runner/helper code assignment once
  the fixed interfaces/tests exist. Its declared verifier does not complete PAL.
* Wrapper remains PRIMARY-only for N2. After N2 outcome, freeze a narrow Expert
  pairing diff with separate tests/review and a new envelope. Its real Expert MAX1
  later serves both that candidate qualification and connection proof.
* Root owns early real-temporary-owner fixture connection/crash verifier and final
  integration/canonical evidence. A separate reviewer checks each final source.

Use isolated branches/workspaces, exact base/fixed hashes, disjoint writes and
separate fresh DBs. Shared contracts and integration remain single-writer Root.

## Verification and actual-entry gates

Independent fixed tests precede source. Cover one admission/charge/entry, receipt
replay vs permission, two-connection races, source/control barriers, original
commit-response loss, exact typed ending/refusal, atomic BaseException rollback,
raw replay/currentness, all-consumer corruption, old-lease latest controls,
prepared/entering/unknown zero-write restart hold, unchanged mock recovery, and
known-ended malformed Action. Use no real provider in these tests.

Early actual-owner fixture route: approved Goal with artifact_saved criterion,
claim→native fixture compose→ART attach→fresh structural VER→complete→READ01.
Add ask→answer/current pending link, stopped historical exclusion, lost ART reply
lookup-only recovery and child SIGKILL/wait/reopen barriers at prepared/entering/
returned/started-compose. Label native endings fixture; numerical/structural MET
is not semantic proof. Preserve original failures and source/test hashes.

Finished Root full suite and independent final source approval are prerequisites
for dependent actual claims. N2 is a separate PRIMARY-only MAX1 freeze after the
cleanup-order correction; it consumes none of N1/T's old allowances. N1/T/CO
unknowns are untouched. No N3 after another UNKNOWN without design reassessment.
Only N2 actual qualified transport plus final Expert source/fixed/full/operator
proof can permit a separately frozen new Expert MAX1. A valid non-compose Action
is known-ended connection, not a successful saved-output case. Exact original
COMPLETED/end_turn/model/no-tools/no-permissions/EOF/wait/CONFIRMED/own-release,
NativeReturned and TSK output hash plus actual ART/fresh VER/readback are required.
One authentic whole-flow usefulness judgment and final release audit remain.
