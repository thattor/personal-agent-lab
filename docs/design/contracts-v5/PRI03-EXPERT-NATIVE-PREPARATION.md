# PRI03 native Expert prerequisite — proposal only

Exact read base: `190fcc4e0540984f50ca1ca165ec99116c4a055c`.
Inputs: current pal/mock_runner_v5.py (also contains MockInvoker; there is no
mock_invoker_v5.py), tasks_v5.py, native_call_v5.py, primary_host_v5.py; current
PAL-contracts-v5 C12/C13/C15, TSK02, ASK01, ART01 and READ01 scopes. The current
external wrapper's PRIMARY-only request boundary is a dependency, not an Expert
provider API. Root owns consultation, adoption and any finite actual-call budget.
This note makes no code, test, DB, provider, CO, canonical or migration change.
Native Primary source approval is not actual N qualification; its real result
was pending at this preparation boundary.

## Existing useful connection

MockInvoker is defined at mock_runner_v5.py:31–104. It owns a process-local
lock/set before TSK admission, refuses existing call IDs, checks get_call.may_enter,
then calls a Python callback. Callback return/exception maps to returned/raised;
end writes retry at most three times. This is an in-process mock lifetime, not a
native provider seam. Native callbacks must not be passed to it.

The existing runner already connects real owners: claim -> current context ->
register/read sources -> model reservation -> admission -> Action parse ->
begin_step -> report/lookup/ask/compose owner -> finish -> fresh verification ->
complete. Context construction at mock_runner_v5.py:491–550 excludes stopped
optional records and any historical Step whose complete provenance is unavailable.
pending_inputs reaches C12 only when both answer body and ask Step are eligible.
It does not read artifacts/verification bodies back into model context. Preserve
that boundary; READ01 user/history dispatch does not authorize native re-input.

TSK public primitives already enforce the important currentness checks:

* claim/get_execution_context/register_sources (tasks_v5.py:775,1096,1128) expose
  current WorkRef, lease, next index, remaining budgets and full Step provenance.
* reserve_budget/expert consumes work and host model ceilings, with step headroom;
  admit_call (1166–1194) checks canonical call ID, owned lease, required subset,
  registered superset and current source gate, then binds that model reservation.
  Do not add a second consume/reserve in the provider. begin_step owns step debit.
* begin_step (1234–1258) accepts only returned calls, current authority and parsed
  Action against original supplied refs. report/lookup/compose/ask are supported;
  operate and model verify Action remain unavailable in this slice.
* authorize_artifact_save (1299–1346), ask/_ready_to_close (1505,1652), complete
  (1537) and release (1995) require ended calls and current ownership. ART stores
  actual full call record dependencies, not just selected Action source_refs.
* Current VER operates through public owner callbacks; every attachment changes
  the exact artifact set and requires fresh current VER before complete. Structural
  MET is not semantic success. report is not completion.

These owners, keys, schemas and transactions should remain the only business
state engine. RUN owns no SQL. A native Expert must earn a TSK-ended returned
state before any of those existing paths can adopt its output.

## Concrete missing lifetime binding

TSK end_call accepts only {call_id,outcome} (1197–1210). Its call row currently
has no native profile, original C15 request hash, dynamic output hash or cessation
record. get_call (1213–1231) reports status/authority but neither request identity
nor output. Reusing it unchanged for native would allow an unqualified status
string to authorize ART/ask/complete.

RECOVERY01 _recover_owned changes all orphan admitted calls to interrupted
(tasks_v5.py:485–493), on evidence of the correctly lifetime-held local mock lock.
That inference is invalid for remote/native work. _old_calls and other integrity
readers currently validate mock call/Step/reservation/claim bindings only.
A side record alone is insufficient unless every path treating a call as ended
also validates that record and distinguishes the call's profile.

NativePrimaryHost already demonstrates a small shape to adapt, not copy as a
second owner: preflight before reserve, prepared side record, one on_enter marker,
exact NativeReturned validation, atomic ending+call hash+phase, and unknown on
unqualified exceptions (primary_host_v5.py:999–1122). TSK must own the Expert
variant because it alone owns the lease/call/Step and release/recovery transaction.
No writes to PRI tables or another owner's private schema.

## Recommended minimum API delta (for Root to freeze)

Introduce an explicit NativeExpertRunner / trusted native invoker construction
with a non-callable provider and immutable NativeProfile. Preserve MockRunner,
MockInvoker and their public callable API/default profile exactly. Extract only
shared context/action-dispatch helpers if necessary; avoid subclass overrides
that accidentally inherit mock exception/end/recovery behavior. A native runner
may orchestrate the existing public owners but cannot use a bare native callback
as a mock Expert.

Prefer three narrow TSK-owned operations rather than widening old end_call:

1. admit_native_call takes the existing admission fields plus the exact closed
   C15 request and immutable profile binding. It atomically performs the same
   canonical lease/WorkRef/index/reservation/source checks, consumes once and
   creates a mandatory native side record in prepared state. Equal replay is a
   receipt, never dispatch permission; another body/profile conflicts.
2. enter_native_call(call_id, attempt_ref) atomically rechecks current authority
   and the original full source closure, then records entering exactly once.
   It is the provider's on_enter hook, before any possible prompt send. Lost
   commit response remains held; a retry of inference is forbidden.
3. end_native_call(call_id, trusted ending) validates either NativeReturned for
   the exact request/profile/attempt or exact NativeNeverEntered. Commit evidence,
   output hash and TSK returned/not_entered together. Same ending replays; changed
   ending conflicts. Generic exceptions are never raised/not_entered/interrupted.

These are proposed shapes, not adopted names or code. A single explicit native
variant of the existing commands is also possible, but must not weaken mock
closed schemas or make profile strings/JSON lookalikes confer authority.

TSK side data minimally binds call ID, claim WorkRef including epoch, lease/index,
reservation, profile/qualification, exact request hash, ordered supplied refs,
original native attempt, entry phase, immutable ending and output hash. Bind both
sides with hashes and profile discriminator. Deleting/replacing either side,
wrong-role reservation, wrong attempt/model, bool index, or partial ending makes
all adoption/release/recovery consumers unavailable before writes. No external
SQL lookup to check this; use TSK-owned helpers inside existing transactions.
Hashes provide trusted-local consistency, not hostile-host or remote attestation.

The native call's raw output also needs an explicit owner decision before freeze.
Full C15 says MOD retains raw results and same-call replay; existing TSK mock rows
retain no raw output. Minimum bounded option: TSK-owned native result body/hash
(or an explicit owner receipt API with same-TX validated binding) stored atomically
with returned, read only for the original call, and source-gated before reuse.
RUN must not create a private durability layer, and an ending hash alone is not
recoverable Action content. If raw retention is deferred, label this a bounded
C15 subset: restart can fail local adoption of known-ended/no-Step output without
reinference, but cannot claim full C15 saved-result replay. This is a real scope
choice, not a reason to silently reconstruct text from native logs.

## Provider role and output separation

NativeDevinText currently permits primary/primary_proposal and omits work_ref;
Expert needs expert/expert_action plus the exact claimed WorkRef. Explicitly extend
its closed request validator for this one pairing, preserving PRIMARY's schema.
Bind the entire C15 request/profile/attempt; canonical source_refs must describe
all actually exposed C12 record bodies and eligible historical provenance, not
only model-cited refs. C12 is the user message payload; host system text fixes
Action-only output and scope. Parse returned text with parse_model_action using
actual supplied refs. Primary's proposal parser is not an Expert parser.

NativeProfile/NativeReturned (native_call_v5.py:110–189) can carry the transport
binding independently of role; that does not mean the current qualification
covers new Expert prompts. Updating wrapper bytes changes its qualification
hash. Root must separately qualify the exact new profile/source and bounded
Expert case before real entry. Keep PAL stdlib core free of CO imports; reuse
only the external wrapper's original public ACP verifier/observer/transport/pool.
No Stage-T correlated export accepted as N cessation; no model-supplied proof.

## Controls, unknown, persistence and restart

Same-process: known bound return must be recorded even after pause/change/stop
fences adoption. This permits safe old-owned release without restoring authority.
Recheck required and supplied sources before begin/finish/save/ask/complete;
changed epoch or revision refuses new effects. Lost ending-write response allows
bounded same-input local persistence retry only, never provider retry/refund.
Unknown stays admitted, consumes allowance and keeps the Expert slot occupied;
cancel/pause/source-stop can record their latest intent but cannot manufacture
cessation. Once a genuine ending is stored, release resolves latest control as
existing C13 requires. Ordinary yield cannot discard unfinished returned output;
fenced output can be abandoned after actual ending.

Startup: profile-qualified known ended records may settle through existing strict
old lease/claim/Step bindings and latest-intent logic. Native admitted/unknown is
held with zero settlement writes: no epoch bump, abandoned Step or interrupted
substitution merely because a new process acquired the lock. Completed historical
facts remain unchanged; stopped sources fence reuse and save/adoption.

Important mismatch with Primary's per-turn policy: Expert has the one global
active execution lease. finish_startup explicitly refuses any active lease
(tasks_v5.py:363–374). Therefore an unknown orphan Expert prevents startup ready,
new Expert claims and current ready-dependent model reservations, including native
Primary. Minimum honest first slice retains this held state while permitting
structured controls/source-stop/read-only inspection through existing nonexecution
paths (238–302). Do not claim unrelated native inference stays ready. Separating
Primary ingress readiness from Expert occupancy, or allowing another Goal while
native is unresolved, is a larger explicit contract change; not this minimum.

Started compose with a confirmed ending may use the existing public ART lookup
and RECOVERY02 typed adoption checks without resaving. Ensure native ending is
validated before entering that path; mock-named recovery events/results need an
honest profile-aware wording/receipt without breaking prior replay. Fresh VER is
required after adoption/epoch/set changes; historical verification is not current
authority. Unknown producer or lookup unavailable holds. Started operate remains
held/unimplemented. No resume/load/cancel-by-PID or reexecution of an old request.

## Meaningful independent fixed cases before source

1. Reject native provider under MockRunner/MockInvoker profile; mock tests unchanged.
2. Preflight refusal before model reserve: zero provider entry/charge; last reserved
   unit valid; no duplicate provider consume and step debit only on begin_step.
3. Exact request/profile/claim/index/reservation/source binding, replay and one-sided
   corruption; one admission under two connections and no replay-driven reentry.
4. on_enter current-source/control recheck, failure/commit-response-loss, and no
   duplicate attempt. Pause/change/stop barriers before and after possible send.
5. NativeReturned valid/invalid/foreign attempt, NativeNeverEntered exact mismatch,
   generic exception/timeout/parent death: only actual typed ending ends the call.
6. Atomic side record/status/output/receipt rollback; bounded local retry without
   second actual call; output persistence loss keeps slot held.
7. Current and old-revision release after actual ending obey latest intent;
   unknown cannot free the lease even under cancel or source-stop.
8. Native unknown restart never reaches mock interrupted; finish_startup remains
   held and controls/read inspection work. Legacy/mock recovery stays unchanged.
9. Real temporary-owner ask->answer/pending links and compose->ART attach->fresh
   VER->complete->READ01, with native fixture endings clearly labelled fixtures.
10. ART commit/lost reply and started compose restart recover original receipt
    only; missing native binding or stopped producer sources cannot adopt.
11. Returned malformed Action is known-ended failed adoption, never repair
    inference; operate/verify Action remains unavailable; report cannot complete.
12. Full context closure excludes stopped historical Step/answer, not just raw
    stopped body; no artifact/verification re-input or uncontrolled extra roles.

## Remaining decisions and limits

Root must freeze native TSK profile/side APIs, raw-result ownership versus honest
subset, recovery event identity, held-startup UI/result shape and exact finite
real Expert case after actual N qualification. The smallest useful case is one
C12 compose over an existing approved Goal, then real ART/structural VER/readback,
with no model-driven verification or external operation. It proves a connection,
not authentic usefulness, semantic completion or the entire personal assistant.
This note adopts none of these proposals and requests no new routine permission.
