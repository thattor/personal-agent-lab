# PRI01 TSK prerequisites and admission seam

PROPOSED ONLY. Input `c068a9c6dcd0a3846ada0a420a930941d2bb007f`;
TSK SHA256 `8f20d02d132b3a70a811919a262b928b0904cc30de8479a977c0c204b95c1670`.
Consultation: `evidence/operations/pri01-20261009/opus-design-review.json`
(REFINE); it omitted counter/transaction internals, inspected here. Root owns
freeze. Only this note changes; current v5 reads only, no external calls.

## 1. Owners

`intake_v5.py:164–192,322–357`: create canonical includes trusted request_scope;
`C03.create` success is atomic, replay precedes gates, failures are unsaved.
`tasks_v5.py:271`: execution guard precedes replay; namespace is `control`.
`:484–516`: finite shared `v5_tsk_host(kind=model,ceiling,used)` already exists;
v5_tsk_usage is cumulative Goal usage. `_reserve` also needs Step headroom.
`:665–687,231–269`: workless reserve is unavailable and consume assumes a lease.
`:608,1124`: get_work exposes full Brief/question text without a source-safe
listing. PRI must not use it as model context or query private TSK SQL.

Add source-safe list_candidates, original create/control receipt lookups, and
session-owned workless reserve/consume. PRI owns turn/call/adoption phases, never
Goal or budget state. MEM's frozen prerequisites are independent; actual ART
recovery adoption precedes PRI activation. 

## 2. Candidates

Proposed `list_candidates({session_id,limit,goal_ids?}) -> Result` with closed
input, strict limit1..20, nonempty IDs, deduplicated optional goal filter.
Session is conversational context, NOT a Goal ownership filter: this single-
account DB lists all matching latest revisions, including completed/cancelled/
failed. No superseded row, history substitution or implicit latest-target choice.
Unsupported query must refuse explicitly.

Result `{works:[{work_ref,brief_summary,expert_id,state,open_questions:
[{id,text,revision}],dependency_refs:[Ref],text_withheld:bool}],truncated:bool}`.
New provenance/withholding/truncation fields require shared adoption. Propose
summary512/question1024 UTF-8 bytes, safe codepoint excerpts. Never truncate IDs
or dependencies. Bounds are freeze choices, not semantic authority.

One owned read transaction on an idle connection covers latest rows, validated
Brief/state/questions/dependencies, readonly source gate, order and limit+1.
Reuse same-connection gate/savepoint/total_changes checks. No writes or replay.
Malformed stored data, gate protocol violation or SQL fault returns unavailable;
ordinary source denied/not_found/unavailable withholds text. BaseException cleans
up the owned transaction and propagates.

Dependencies = registered record refs plus full open-question producing-call
refs; validate required-origin/Brief inclusion and existing question invariants.
If any dependency is unusable, return empty summary/question text and
text_withheld=true, preserving IDs/revision/state/refs. No stopped fallback title.
Dependencies never truncate; excess frozen count/bytes returns limit.

Order by latest work-bound C14 seq across Goal revisions, then goal_id; existing
`intake_v5.py:36–38` stores seq/WorkRef. TSK derives its own ordering without PRI
reading SQL/event text. Withheld items count toward limit; empty is []/false;
truncated is not proof of uniqueness.

## 3. F2/F5 exposure choice requiring Root disposition

Literal Opus F5 unions dependencies of EVERY disclosed candidate. With F2's
withheld candidates still visible as IDs/state, one stopped historical record
then prevents every new_work/change, even an unrelated request. This is safe
but concretely over-invalidates; do not silently call it a source bug.

Proposed refinement, NOT adopted: distinguish text from metadata exposure.
Host snapshot keeps full refs; adoption union contains turn record, every C11
record actually exposed, all deps of text-visible candidates and model-selected
permitted records. Never omit an uncited exposed source. Withheld IDs/state add
no source-derived text, so unrelated new work need not inherit hidden stopped
sources. Diagnostics alone never authorize selecting hidden refs.

Cases: visible source stops after inference → union/gate rejects new_work/change;
withheld A at entry + unrelated B → literal F5 rejects, refinement permits B;
visibility flips → fingerprint stale without re-inference. Byte-omitted text adds
no content dependencies but truncation/exposure must be recorded. Hidden refs
cannot be selected from diagnostics. Wrong-but-listed target remains a semantic
risk; receipts must name the actual target from safe owner data.

F3 hashes ordered `(goal_id,revision,open_question_ids,text_withheld)` plus
truncated, excluding epoch/state. Compare after return and immediately before
dispatch. Activity reordering may conservatively stale it. Owner TX decides
state/revision; a new candidate after the last check remains a semantic race,
not something this fingerprint atomically authorizes.

## 4. Original receipt lookup

`get_create_by_key({key})` and `get_control_by_key({key})`: readonly original
successful Result or not_found; strict closed input, corrupt data unavailable.
No source gate, grant refresh, latest projection, event or reapplication. May read
inside caller transaction without taking it over, like PRI01-MEM lookup.

Use actual `C03.create`/`control` namespaces. Validate saved canonical request,
key, command variant and typed result. Create validates original request_scope,
revision1/Brief/Grant; control validates original target Goal/revision (change
returns replacement) and immutable referenced facts. Never compare historical
state/epoch against today's row. C10 human commands ignore input epoch, so it
cannot be an exact result-epoch assertion. Freeze lookup variants explicitly; PRI never proposes complete. Failures have
no current owner replay.

PRI records exact applying request/scope and effect key before dispatch. Lookup
proves commit, not permission to invoke. Corrupt receipt is not absence; no
promise to detect adversarial rewrites of all trusted local DB evidence.

## 5. Workless Primary reservation, no second budget

Proposed C15 branch: `reserve_budget({key,kind:"model",role:"primary"}) ->
{reservation_id,remaining:{host:int}}`. Require registered ready HOST even for
legacy stores. No fake WorkRef/Goal/lease/Step. Reject null work_ref, extra keys,
other workless kinds/roles. Model zero/exhaustion means limit; Step zero does not
block conversation.

In existing TSK transaction: safely premint ID, validate existing finite model
counter, increment ONLY `v5_tsk_host.used`, insert v5_tsk_reservation with
lease/work/idx NULL, kind=model, role=primary, binding NULL. One small reservation
→session table reuses session UUID/profile/runner proof. No Goal usage, Step
headroom, lease occupancy, new counter or refund. Expert and Primary atomically
compete for the same last host model unit.

`_execution_request.consume` explicitly distinguishes qualified workless rows;
NULL lease alone never proves ownership. Validate complete row shape/session
before replay. `_bind` retains bind-once, verifies this branch before writing;
different call ID conflicts. PRI host derives call ID from turn_id, never model.
Reserve replay must also check original reservation session before returning it:
`_execution()` alone would admit another ready session's old workless key.
Same-session repeats charge once, changed input conflicts, foreign ownership
cannot reuse. Recovery never reserves again; reserve-commit/PRI-ID-save crash
leaves consumed history, not refundable accounting loss.

## 6. Minimal PrimaryHost phases and two-connection admission

Trusted constructor: guard, connection/factory, public MEM/TSK owners, bounds,
request_scope and bounded mock callback. No public proof/permission flag. Surface:

- `submit({client_key,session_id,text})` returns C01 turn_id/status only; no model.
- `run_turn({turn_id})` attempts at most one callback, explicit ready host action.
- `get_turn({turn_id})` reads C01 status/confirmed reply/effect_refs/error.
- `recover_turns()` runs explicitly in startup after TSK recovery and before
  finish_startup. No model call, new reservation or late effect application.

PRI stores UNIQUE(session_id,client_key), turn_id, MEM ref/hash, owner session,
call/reservation IDs, snapshot metadata, phase, applying intent and receipt. No raw
transcript/MEM bodies. Output stays local until normalized intent persists; a
crash between returned and applying is interrupted, not replayable inference.

Submit calls MEM.append with `dumps(['PRI01.append',session_id,client_key])`,
then short PRI insert. MEM compares sanitized input on every retry; never retain
raw secrets to distinguish sanitizer-equivalent input. A gap leaves one history
record; resend repairs it without a model call. Get hash through public C11;
stopped content is not inference input. No private MEM SQL.

Internal phases: pending→preparing→admitted→returned→applying→terminal; public
pending covers live phases. Short BEGIN IMMEDIATE CAS pending→preparing records
session and fresh token. Only the winning live invocation continues. Duplicate
run_turn on another connection returns pending without reserve/callback; no
lease timeout/takeover. Uncertain commit is not entry permission; preserve local
ownership until startup recovery, never let another invocation adopt it.

Gather bounded snapshot; reserve with `dumps(['PRI01.budget',turn_id])` and consume
canonical call ID outside PRI TX. Record admitted with refs/hash/fingerprint;
recheck full sources through public same-DB MEM gate in that short transaction.
Callback has no open TX. guard.activity spans admission through callback ending
and its durable-record attempt. After-admission stop can race entry; no recall
promise. Controls use separate connections, never wait on Primary/model mutex.

Persist returned/raised/not_entered distinctly. Lost ending never re-invokes;
bounded identical persistence retry may save a known local ending. Parse the
closed proposal, normalize one owner request/scope/key and persist applying BEFORE
idle-connection dispatch. Known failure is saved by PRI and suppresses reply.
Uncertain owner outcome retains applying; only the live owner continuation may
retry the identical owner request. Another run_turn cannot take it over.

## 7. Commit gaps, recovery and acceptance

Startup under original managed proof: pending/preparing/admitted or returned
without intent becomes interrupted, never re-invoked. Applying only looks up
owner receipt: success records original result; definitive not_found means no
local commit and interrupts WITHOUT applying; unavailable/corrupt stays unresolved.
This relies on ended synchronous local SQLite work, not providers. Unmanaged
turn ownership refuses. TSK cleanup and PRI reconciliation remain separate.

Terminal PRI row and one namespaced C14 result/error event commit together via
TSK.append_event; omit work_ref to avoid epoch-moved rejection. Do not duplicate
accepted/state/question events. Reply depends on confirmed effect; none still
needs source checks before adopting its model text. Replies/events are user history only, never model context or new MEM replies.

Fixed cases: concurrent duplicate submit/run_turn; sanitizer-equivalent retry;
reservation reply loss/last-unit Expert contention; consume wrong session/role/
rebind; each commit gap; no callback TX; BaseException; immediate control during
callback barrier; historical receipts after change/stop/config drift; cross-session
terminal candidates/withholding/truncation; F2/F5 cases; out-of-set and wrong-but-
listed targets; exact answer/change record; no grant expansion/complete/old VER.

Root choices: bounds/query subset, F5 exposure, receipt variants, unresolved-turn
startup readiness and terminal wire. No silent success/retry for unavailable
applying. PRI waits on freeze and actual ART adoption. No tests/code execution
or product acceptance is claimed.
