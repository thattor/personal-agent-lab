# ASK01/1 — durable question, linked answer and bounded mock continuation

ADOPTED technical contract under D038/D041. Root/Sol owns this freeze.
Baseline product code: ff1a1ccab553173fa4eae17b29fbe0a79b998313. Scope source base
e3bf06f591ade7c7432d99a31e20e2ca02a877be; subsequent c185841 is evidence/role docs.
Consultations: prior SWE2610f221; exact AGY Opus5.5 candidate2d96c06a; native Astra
actual-state reconciliation and additive C12 linkage disposition. Root adopts the
following resolution, superseding conflicting draft text. No code/test execution
by the contract drafters is implied.

Value: mock ask -> durable waiting -> separately saved answer -> explicit next
run -> compose/structural verify/complete -> existing readback. Stdlib and temporary
SQLite only. No new provider/UI/PRI, semantic verification, change/attach, restart
recovery, live DB migration, auth/cost, or unknown-call actions.

## 1. Owner APIs and durable identities

TaskStore owns a new question table and all work/Step/lease/event writes.
MEM owns answer records and usability; TSK never copies answer bodies or reads MEM
SQL. No question Ref kind. Host-issued question IDs are opaque strings.

C04:
  ask({key,work_ref,step_id,question,missing_fact,source_refs})
    -> Result{question_id,state:'waiting_input',work_ref}
  get_question_by_key({key}) -> original C04 receipt or not_found
C10:
  control({key,work_ref,command:{kind:'answer',question_id,answer_record_ref}})
    -> Result{work_ref,state:'queued'|'paused',control_status:'none'}

All shapes are closed; use existing strict WorkRef/Ref/AskAction parsing and UTF-8
rules. source_refs are record Refs from actual call inputs. Preserve arrays for
canonical replay/action comparison; do not introduce a duplicate-ref ban absent
from shared AskAction. answer_record_ref must be record. No caller-provided state.
Host ask key: dumps(['C04.ask',work_ref,step_id]); answer key should include work
Goal/revision, question ID and answer Ref (or a persisted caller turn ID), not only
record_id across unrelated questions. Same key/different canonical request conflicts.

Question storage retains ID, Goal/revision, producing Step identity, exact question,
missing_fact, selected refs, status open|answered|closed and nullable answer Ref.
Producing full call dependencies are validated from TSK's immutable call/Step rows;
if copied into the new row, validate exact equality rather than creating an
independent authority. Enforce unique step_id and at most one open question per Goal.
Validate persisted contracts and linkage on read: corruption is unavailable.
No modifications to other owners' tables or schema are needed.

## 2. Atomic ask; no ask/release window

Input validation precedes BEGIN IMMEDIATE; canonical replay precedes authority.
Same-input replay is the original historical receipt even after answer/cancel/stop.
New ask requires exact current WorkRef, active owning lease, running, no pause/drain,
using existing authority precedence. Unknown Step is not_found. Valid foreign or
old Step binding is stale; structurally corrupt storage is unavailable. Ask must
match the stored ask action's question/missing_fact/selected refs exactly; a valid
non-ask/non-started Step or mismatched requested action is conflict.

Readiness before any write:
- Strictly parse every current-lease call WorkRef and require equality to current
  work, including epoch, for all recognized statuses. Indices are exact nonnegative
  bounded ints, never bool. Unknown call/Step status is unavailable.
- Target Step wire index equals its SQL index and producing call index; its stored
  Goal/revision, wire WorkRef, call lease, call.step and saved Step.call all agree.
  Its call is returned. No other admitted call or unadopted returned output exists.
- The only started Step in the revision is this ask Step. Other returned calls
  have their own finished Steps. Older finished Steps keep legitimate old epochs;
  they are not required to match the current lease epoch.
- Gate the full producing call input set, not just model-selected question refs.
  It must be registered record refs and contain origin/Brief required refs.
  Selected refs must be a subset. Gate failures retain not_found/denied/unavailable.
- No existing open question. Under valid new-ask authority an existing open
  question is corrupt state (unavailable), not permission to replace it.

Atomically finish target ask Step with result_refs=[], save open question,
waiting_input, deactivate this ended lease, clear flags, append one question event
(text=question, refs=selected refs, owning work session), and save replay. Epoch
unchanged. No additional model/step reservation or refund: begin_step owns the
step reservation. BaseException rolls back and propagates; ordinary failure rolls
back with bounded errors. Trusted callbacks are not a hostile-code sandbox.

begin_step accepts ask through existing parse_model_action membership checks.
finish_step explicitly rejects a valid ask with conflict after ordinary missing/stale checks; C04 alone
finishes it. A committed ask requires no release, and a subsequent release is denied
on the inactive lease without modifying waiting_input. Existing release remains
responsible for a fenced, uncommitted ask under pause/cancel/drain.

## 3. Narrow state invariants and answer

Only ASK01-created waiting_input requires one valid open question and no active
lease. An open question may remain on paused work. Do NOT impose a global rule
that every paused work has a question or lacks a draining lease: existing queued
pause and old owned-lease control paths remain valid. RUN does not claim waiting.

Answer uses current Goal/revision, ignoring the request epoch like owner controls.
After replay: missing work/question -> not_found; foreign question -> not_found;
old revision -> stale; answered/closed question -> conflict. Valid open question
must belong to waiting_input or paused and have no active lease for that work;
inconsistent ASK01 waiting/open-question state is unavailable. Gate the question's
required/full producing-call dependencies and the answer record in the same TX.
No semantic claim that the answer is sufficient is made.

Atomically mark answered with answer Ref, register that Ref as optional work source,
waiting_input -> queued or paused -> paused, append one 'question answered' state
event with answer Ref, and save receipt. Epoch/budgets unchanged. Do not add the
answer to Brief or _required: past Steps did not receive future answers.
Same-key repeat returns original receipt even after later terminal state/source
stop. A NEW key for an already resolved question returns conflict, even with the
same record; C10's identical replay promise is satisfied by the original key.

pause(waiting_input) -> paused. resume(paused with open question) -> waiting_input;
resume(paused without one) -> queued. Existing other pause/resume rules remain.
cancel closes any open question in the same existing epoch-invalidating transaction.
Answer cannot revive cancelled/failed/completed work or closed questions.

## 4. Stop semantics, including unrelated optional records

Preserve existing epoch invalidation for every nonterminal work with intersecting
registered refs. Keep current completed-history and cancelled/failed handling.
Question dependencies are required refs UNION full producing-call inputs, not only
selected refs. Missing linkage or required registration is unavailable, not guessed.

For waiting_input with an open question and no lease:
- intersecting question dependencies: epoch+1, close question, queue;
- intersecting registered historical optional refs outside question dependencies:
  epoch+1, retain open question AND waiting_input; it still needs its answer.
For paused with an open question: both cases increment epoch and keep paused; close
question only in the first case. Resume then follows the remaining open question.
Paused without a question retains existing behavior, including retained lease flags.
Running retains existing epoch+1/draining behavior. No automatic waiting release.
Maximum epoch still fails for actual epoch invalidation. All changes and MEM stop
share one transaction; errors roll everything back.

After answer, its record stays registered. Stopping it follows ordinary queued/
running/paused invalidation, never reopens the answered question or revives a source.
Other answered records and question linkages are retained. On later model input,
denied/missing optional answer bodies are excluded explicitly; unavailable remains
an error. Question text/old Step derived from stopped dependencies is also excluded
by existing full step_sources provenance. Required-source stop remains blocking;
queuing is not a claim that the immutable Brief can now execute.

## 5. Public readback and answer linkage

Existing C02 get_work already has open_questions; populate it with
[{id,text,revision}] for the requested stored revision, only status=open. Do not
add or rename fields. Current IntakeStore has no candidates implementation; do not
claim full C02 search or implement it just for ASK01. No new get_open_question API
is needed. checkpoint.open_question_refs contains opaque question ID strings,
never Refs; report actual open IDs rather than hardcoding []. Valid running claims
normally have no open question.

claim.pending_inputs becomes an ordered list of answered question links for the
claimed revision, ordered by producing Step index:
  [{question_id,step_id,answer_record_ref}]
It contains metadata only, including stopped answer Refs, and is non-destructive:
claim/replay does not consume it. This avoids losing an answer on failed inference.
RUN validates each link against its finished ask Step; malformed linkage fails
closed rather than silently becoming an ordinary unassociated answer.

Proposed minimal additive C12 field (Root must adopt in the shared contract):
  pending_inputs?: [{question_id,step_id,answer_record_ref}]
Omit this field when there are no eligible links. Include a link only when BOTH
its exact answer Ref has a usable C11 body in this call's context AND its producing
finished ask Step is included in this call's steps after full step_sources
provenance filtering. This lets the Expert associate multiple answers with their
actual questions without invented body text, a new Ref kind, or extra callbacks.

Preserve all claimed links separately under pending_inputs in local diagnostics,
including those withheld from C12; existing excluded_refs/excluded_step_ids show
which prerequisite was omitted. A stopped/missing answer excludes its body and
link, but does not erase its question history or another valid answer. A stopped
question dependency excludes the ask Step and link, even if the answer itself is
usable. That independently usable answer record may remain in ordinary context,
but no reconstructed question text or association is supplied. If both prerequisites
are available, unrelated historical optional exclusions do not suppress the link.
Transient unavailable remains an error, not evidence of a deliberate stop.

Use the actual selected call context refs for existing admission rechecks. Because
an included ask Step's full provenance is represented in that context, a stop of
its dependencies or its answer after filtering but before admission is fenced by
the normal same-transaction gate/epoch checks. Later stop before result adoption
is fenced again; nothing promises recall of inputs already sent. Do not recompute
or insert links after admission from a different snapshot. No link consumes budget,
changes required refs, authorizes resources, or claims semantic answer sufficiency.
The mock acceptance must assert exact C12 links for multiple questions and their
selective disappearance under answer-source and question-source stops, as well as
retention of the complete diagnostic linkage list.

## 6. RUN persistence and authority

Build ask requests from the persisted Step. At most three same-input local ask
attempts on unavailable, followed by at most one get_question_by_key lookup. A
strict valid receipt returns status=waiting, question_id, work_ref, state,
lease_id, step_id and existing diagnostics (plus pending_inputs/verification when
present). No release after success. If outcome remains unknown, use yield_or_retain;
no inference repairs persistence. A malformed success returns unavailable.
For ask conflict/stale/denied/not_found/invalid_input, try ordinary release(yield)
to settle newer control. If not fenced/ready, retain and report the failure; never
release(failed) merely because ask was refused, and never continue to inference
with a started Step.

Retained-tail resumption is feasible through public get_call: require exactly one
started tail Step of kind ask, use the existing deterministic call ID from lease
and that Step index (not next index), require returned and its bound step_id/work
match, and resend the identical ask before the generic started-Step rejection.
TSK rechecks actual lease/index/source authority. Missing/malformed/uncertain call
stays unavailable/retained; other started Steps keep the existing no-reinference
rule. This is same-runner local continuation, not restart adoption.

C076: VER verify conflict/stale/denied returns to the bounded loop like complete,
not failed(). Existing execution-context authority and release fencing settle
newer controls before inference: get_execution_context conflict/stale/denied uses
release(yield), never the generic failed disposition. Required-source gate denied
remains its existing separate terminal path. Persistent verify unavailable retains existing
yield_or_retain behavior; completion uncertainty retains its existing behavior.

## 7. Essential acceptance and ownership

Real temporary MEM/TSK/ART/VER: ask -> inactive lease/waiting -> MEM answer -> queued
-> new claim with exact question/answer link -> context body -> compose -> completed
-> existing READ01 output. Cumulative budgets; another Goal can claim while waiting.
Test pause/answer/resume, cancellation, same-key history/new-key conflicts, direct
finish refusal, strict call/index corruption, old finished Steps, rollback and
BaseException after writes, lost replies and retained-tail retry without inference.
Two-connection barriers order ask vs pause/cancel/stop and answer vs stop. Test
selected and unselected producing-call source stops; unrelated historical optional
stop must preserve the open question; stopped one-of-several answers remains named
while the other answers remain available. No sleeps or fake provider cessation.

TSK and RUN owners have separate files. Root owns frozen schemas/wire and real
integration/demo/canonical evidence; independent reviewer is not the author.
No implementation self-report constitutes acceptance or product completion.

## 8. Assignment and concrete example

Root is sole shared-contract/canonical/DB-integration owner. Each worker uses an
isolated checkout of the frozen commit. TSK author writes only pal/tasks_v5.py;
RUN author writes only pal/mock_runner_v5.py. Separate Sol contexts own
tests/test_tasks_ask_v5.py and tests/test_mock_ask_v5.py before implementation;
authors cannot edit those fixed fixtures. Root owns scripts/demo_ask_v5.py and
tests/test_ask_connection_v5.py using actual temporary SQLite owners. Independent
review is a different context from each code author. Return exact diff/commit,
commands/exit results and unresolved items. No writes to real DBs or other projects.

Example host association (IDs below are illustrative, issued by the owners):
  pending_inputs = [{question_id:'q1',step_id:'s0',
                     answer_record_ref:{kind:'record',id:'r-answer'}}]
The next claim may use epoch2 after question epoch1, with unchanged Goal/revision.
The ask Step keeps epoch1. The answer body is a fresh MEM C11 model_context read.
C12 includes this same metadata entry only while both s0 and r-answer are eligible.
No C11 content/hash is rewritten to insert the association.

Canonical host answer key used by Root demo:
  dumps(['C10.answer', work.goal_id, work.revision, question_id, answer_record_ref])
The same exact request is retained for replay; changed request epoch under the
same key is a different canonical request and conflicts, despite ordinary answer
authority ignoring epoch. Do not create an epoch-normalizing replay exception.
