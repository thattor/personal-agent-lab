# PRI01/1 — frozen first managed mock Primary connection

Root adopts the completed actual Opus5.5 PRI01 F1–F12 consultation and Astra's
full-owner reconciliation. Additional refinement task1ec690fc hit a session
limit, outcome unknown, no report/adoption/retry. This freeze is Root's explicit
technical disposition, not new Opus endorsement. It adds the ordinary sentence
→ same Goal question/answer/change → saved draft/fresh structural check/readback
and immediate control/record stop path. Whole usefulness, real-provider profile,
P001, future continue/attach/remember/correct, semantic completion, live DBs and
external services remain separate. Standard library, existing no-extra-cost scope.

Prerequisites: independently approved RECOVERY01/02, PRI01-MEM/1, PRI01-TSK/1,
PRI01-WIRE/1. Fixed host tests precede new pal/primary_host_v5.py source. Root
owns that source/shared contracts/integration, separate Sol fixed tests and exact
source review. Owners retain their tables; PRI never queries private owner SQL.
No second execution engine or fake Goal/lease for conversation. Existing source
authors/reviewers are isolated, no shared DB between their tests.

## Trusted host and public surface

`PrimaryHost(connection, *, guard, memory, tasks, request_scope, invoke,
model_id="mock-primary")`. Same file-backed autocommit connection and actual
MEM/TSK public owners, same exact registered MockHostSession, fixed public Grant,
bounded synchronous in-process mock callback. Guard's db UUID/session/runner and
managed-inprocess-mock/1 identity are persisted in PRI-owned session evidence.
Only this cooperative profile qualifies old-process-lock cessation. Callback
must not escape/fork/launch a provider subprocess; no caller proof flag. Ready
guard plus PRI readiness are both required for inference. Existing host budget
is finite; no additional counter/refund, model0 limits conversation and Step0 does
not. Inference failure is not free. Constructor configuration is trusted input.

- `submit({client_key,session_id,text}) -> Result[{turn_id,status}]`, text exact
  UTF8 <=16384bytes. MEM.append key dumps(['PRI01.append',session,client_key])
  comes first; sanitized equality determines identity. Then PRI UNIQUE(session,
  client_key) record_ref/hash turn admission in its own short transaction. Crash
  gap is history-only record; identical resend completes it, changed sanitized
  input conflicts. submit never infers. No raw input/snapshot bodies are stored
  in PRI; original body remains MEM-owned. Host mints nonempty unique turn ID.
  C11/user_view is used only to validate that returned immutable Ref/body hash
  for admission metadata, including stopped history; it never supplies inference
  context. Model exposure always uses the stricter C11/model_context path.
- `get_turn({turn_id}) -> Result[{status,effect_refs,reply?,error?}]` with public
  pending/committed/failed/interrupted. Pending internal phases are not UI claims.
  Original outcome/effect receipt is history, not new authority. Stored reply is
  returned only when ALL its exposure refs still pass current C11/model_context
  hash/usability validation; otherwise omit reply and attach bounded read error
  while retaining committed status/effect_refs. No callback/effect on a read.
- `run_turn({turn_id})` returns the same get_turn shape. Duplicate active/terminal
  calls never reinfer, reapply or take over. Pending execution belongs to one
  successful durable CAS/nonce and its live invocation, not guard permit count.
- `control({client_key,session_id,work_ref,command})`, command exact pause/resume/
  cancel. Short guard.operation, public TSK.control key dumps(['PRI01.control',
  session,client_key]); no model/Primary mutex/MEM append/Primary budget. Existing
  owner revision/state and replay rules decide, no lexical guessing.
- `stop_reference({client_key,session_id,source_ref})`: exact record Ref and
  MEM.stop_reference key dumps(['PRI01.stop',session,client_key]); same immediate
  no-model path. This explicit endpoint meets F12's structured record-stop seam.
- `recover_turns() -> Result[{interrupted_turn_ids,committed_turn_ids,held_turn_ids}]`
  startup-only, after TSK recovery and before finish_startup. Never effects/callback.

Malformed closed public input is invalid_input, byte excess limit, unknown turn
not_found, unready conflict, bad guard/connection/config/corrupt store unavailable.
Public errors contain only fixed messages/codes/valid Refs, no raw exceptions,
SQL/path/body or guessed success. BaseException propagates after owned cleanup.
Caller active transactions are refused for mutations without being taken over.
History and all reply gates share one read snapshot. A cooperating C11 read's
write is rolled back to its savepoint and suppresses reply, preserving prior
caller writes. Lost/replaced read transaction is unavailable; no successful
history projection is made from that invalid snapshot. These savepoints detect
cooperating-owner faults; they are not a hostile-code containment boundary.

## Source-safe bounded snapshot and Root F5 refinement

C01 inside model request: {record_ref,session_id,candidates:<C02 result>,context:
{summaries:[],records:[C11 results],records_truncated:bool}}. Candidates limit10,
recent same-session usable records at most6 INCLUDING mandatory current turn.
All bodies through C11 purpose=model_context, never user_view/get_work/C14/reply
history. Validate exact C11 Ref/plain UTF8/body SHA256/usability and closed owner
shape. Drop oldest optional records to fit32768UTF8byte snapshot and mark
records_truncated; never drop candidate IDs/deps or mandatory original. Mandatory
over-cap fails limit before budget/callback. Source gate failures never substitute
empty usable body. Context includes no provider credentials or grant authority.

Root explicitly refines literal Opus F5 all-candidate over-invalidation after
Astra showed withheld historical A would block unrelated new B indefinitely.
Exposure closure is current turn + EVERY actually exposed C11 record + ALL record
dependencies of EVERY text-visible candidate + allowed selected record refs,
deduplicated in first-occurrence order. Uncited exposed sources are mandatory.
Withheld candidate IDs/state/dependency metadata have no body-derived text and
are not selectable bodies/fallback titles/answer/change authority. Parser allowed
records are only C11 bodies actually provided. Hidden candidate refs never become
input bodies. A visible dependency stopping before dispatch still denies adoption
atomically in create/change's context_refs gate. This preserves source protection
and adds no model permission; it is not attributed to the unreceived report.

Persist only metadata/ref/hash/exposure set and candidate fingerprint. Fingerprint
is SHA256 of ordered goal_id/revision/open-question IDs/text_withheld plus C02
truncated, excluding epoch/state. Recheck before callback, after return and just
before owner dispatch. Mismatch is stale/no effect/no reinference/rewrite. This
semantic selection check is best-effort, not an atomic owner lock. State/revision/
question/source decisions remain in the final owner transaction. Wrong-but-listed
targets remain a semantic risk; membership does not prove user intention.

## One owned bounded call, intent and terminal outcome

Short CAS pending→preparing records current session/nonce. Only known successful
commit grants the winning invocation continuation. No timeout/takeover/resume of
admitted/returned rows from another run_turn. Own guard.activity covers preparation,
reservation/admission, callback cessation and ending-record attempt, including
BaseException. It is lifetime accounting, not a mutex. No SQLite transaction
across callback. Reserve key dumps(['PRI01.reserve',turn_id]), existing TSK workless
model/primary; consume binds exactly dumps(['PRI01.call',turn_id]). PRI owns C15
ledger status admitted/returned/raised/not_entered/interrupted and binding/session.
Reserve failure/consume failure makes no callback; keep successful charges history.
After reserve/consume, recheck semantic fingerprint and all exposure refs, with
the source check inside the short durable call admission transaction and again
before callback entry. A confirmed admission whose acknowledgement is lost does
not enter callback; record not_entered when the local ending can be confirmed.
Uncertain ending stays pending. No consumed charge is refunded.

invoke receives closed C15 request {call_id,reservation_id,role:"primary",messages:
[{role:"system",text:<fixed grammar instruction>},{role:"user",text:<C01 JSON>}],
source_refs:<full exposure closure>,output_kind:"primary_proposal"}. Trusted mock
returns exact str parsed with PRI01-WIRE; model_id is constructor-assigned, not a
model output field. Call ending stores status/output hash, no raw output JSON.
Ordinary callback raise is bounded failed; BaseException attempts known raised
ending then propagates. Uncertain admission/ending persistence never permits a
new callback; startup reconciles the durable row. There is no output fallback.
Invalid UTF8 callback text is a known returned call with absent output hash and
a failed parsed turn, rather than an invented admitted/unknown call.
PRI-owned companion hashes bind turn/session/nonce, call identity/reservation,
snapshot exposure metadata and saved intent; terminal outcome has its own
canonical hash and closed fixed error shape. One-sided corruption fails closed.
These checks detect accidental record mismatch, not coordinated forgery of a
trusted database. They do not query private owner tables or authorize new effects.

Before dispatch persist exact normalized proposal, original reply, owner request,
trusted fixed scope and effect key dumps(['PRI01.effect',turn_id,proposal_kind]).
New_work uses actual TSK.create with origin=current record and exposure closure
context_refs, intersected trusted request_scope. Change keeps prior authority and
uses exact origin/current record plus full closure. Answer maps proposal.record_ref
to actual TSK command.answer_record_ref. Pause/resume/cancel use selected WorkRef.
Memory stop uses actual MEM namespace and same-session allowed record. None makes
no owner effect. No model Grant/ID/complete or hidden source-selection authority.

Dispatch public idle-owner method outside PRI transaction. A confirmed owner
success can become committed. Definitive coded refusal becomes failed, suppressing
model reply. Exception, malformed response, response loss or unavailable is
uncertain: keep applying, suppress reply, no guessed receipt/re-dispatch. Reconcile
only at qualified startup. Reply validation checks all exposed sources in the
short terminal transaction, so stop cannot commit a newly usable model reply.
If a successful stop itself invalidates exposure, retain its confirmed committed
receipt and suppress reply; fixed host acknowledgement remains available.

One terminal PRI row plus one namespaced C14 result/error atomically through
TSK.append_event(same active connection), key dumps(['PRI01.turn',turn_id]); refs
original record plus valid effect Refs, omit work_ref. C14 text is fixed host
notice only, never copied model reply/body or a model's completion claim. A TSK
WorkRef/question ID is not a Ref kind. Host reply may name the owner-confirmed
Goal ID/revision/state, never invent a purpose from withheld text. Append-event
failure rolls back terminal commit. Owner events remain distinct. No MEM assistant
reply is added and no turn/reply/event text is subsequent model context.
The model reply retains its8192UTF8byte wire cap; model text plus fixed owner
acknowledgement has a separate16384UTF8byte host cap. No content is silently
truncated or taken from a withheld body.

## Startup reconciliation and fixed proof

PRI rows bind original session/runner/db UUID/profile to PRI session evidence;
missing/contradictory/unqualified binding is held. New valid same-DB lock/session
after old owned permits end qualifies in-process cessation only. Old non-applying
pending/preparing/admitted/returned turns become interrupted; unfinished call
becomes interrupted, known ending is retained. Applying uses public original
create/control/stop receipt lookup with its saved exact key. Valid original
success commits history (reply still current-source gated). Definitive not_found
after qualified cessation interrupts, never applies effect. Corrupt/unavailable
lookup stays held. No same-client callback, grant refresh, budget refund or write
to owner history. PRI readiness refuses foreign unresolved turns even if caller
skips PRI recovery and invokes TSK.finish_startup; do not silently recover at ready.

Fixed actual temporary managed SQLite plus labeled mock callbacks: duplicate
submit/concurrent run entry and key conflict; sanitized identity; no callback TX;
Step0/model0/sharedbudget; closed/out-of-set/wrong-but-listed/withheld selectors;
withheld A+newB; stopped original/context/visible-candidate before entry/adoption/
reply/read; fingerprint additions/revision/question versus epoch/state only;
new_work/answer/change provenance/prior Grant; owner error/uncertain applying;
commit-gap startup receipt/not_found/held and no same-key inference; missing session
binding/skipped startup; immediate structured cancel/stop while callback is held;
BaseException lifetime; terminal event rollback/no duplicate/outbox body laundering.
Root then runs actual whole mock path and process barriers, separate exact-source
review, required full regression. Only then finite separately frozen real-provider
proof and one authentic improved usefulness judgment. No overall completion at
owner prerequisite green, no criterion weakening to fit a fixture.
