# PRI01/1 refinement consultation — proposed choices, no code activation

Root requests actual Opus5.5 resolution of the first PRI report's F1–F12 after
Astra inspected complete current TSK. Read PRI01-TSK-SEAMS.md, original proposal,
retained first Opus report, shared C01–C15, integrated MEM methods and the verbatim
counter/transaction excerpts. Neither report may claim omitted code inspection.
RECOVERY02 adoption source is being implemented and is an activation dependency;
this independent consultation need not wait for its tests. Root owns final freeze.

Value remains request → same Goal question/answer/change → saved draft/fresh check
→ readback → immediate control/source-stop. Whole usefulness and finite separately
qualified real-provider proof follow the mock connection; no new service/auth/cost,
live DB migration, P001 adoption or model completion authority. The existing
managed-inprocess-mock/1 profile does not qualify CLI subprocess callbacks.

## Proposed exact refinements to first report

R1. Resolve F2/F5 by actual text exposure. TSK returns all matching latest account
Goals including terminal/cross-session, with source-gated summary/question text,
full dependency_refs and text_withheld. Withheld entries retain IDs/state/refs,
but have empty text. Adoption provenance unions original turn, every actual C11
record exposed and all deps of text-visible candidates, plus permitted selected
record refs. Never omit an uncited exposed source. Hidden refs are not selectable;
answer/change against a text_withheld target refuse denied. Explicit structured
pause/resume/cancel remains metadata-only owner control. Case withheld historical
A + unrelated request B must not force stopped A into new B. Visible A that stops
after exposure must deny new_work/change; visibility flip is stale. Is this safe
refinement preferable to literal all-candidate F5 over-invalidation? Do not silently
call original F5 a bug or downgrade full-exposure provenance.

R2. Minimal C02.list_candidates closed {session_id,limit,goal_ids?}, strict1..20;
goal filter <=20 distinct nonempty UTF8 strings. query is explicitly unavailable
in this slice, not silently ignored. Output closed {works,truncated}, each
{work_ref,brief_summary,expert_id,state,open_questions,dependency_refs,text_withheld}.
Summary purpose512 UTF8 bytes, question1024; safe codepoint prefix, no ID/dependency
truncation. Root proposes total result <=131072bytes or limit. Latest-event seq
descending then goal_id for stable order; withheld count toward limit. One owned
read transaction, readonly guarded gate; corrupt data/protocol yields unavailable,
ordinary denied/missing/unavailable sources withhold all derived text. Required
and full open-question call inputs must be included in validated registered deps.

R3. Use EXISTING v5_tsk_host model counter, not another budget. Workless reserve
{key,kind:model,role:primary} returns {reservation_id,remaining:{host:int}}. Requires
exact managed ready registered session, strict NULL lease/work/idx, one TSK-owned
reservation→session binding. Atomic host model used+1 only, no Goal usage/Step
headroom/lease/refund. consume checks complete reservation/session before replay;
same-session same binding replay, different binding conflict, foreign session
unavailable/denied. Expert and Primary compete for the same last model unit.
TSK owns original readonly successful create/control receipts using actual
C03.create/control namespaces; no current-state rewriting or source regating.
Variant/binding validation must reject corrupt receipt, never substitute not_found.

R4. PrimaryHost surface: submit({client_key,session_id,text}), run_turn({turn_id}),
get_turn({turn_id}), recover_turns() and structured control({client_key,session_id,
work_ref,command:pause|resume|cancel}). Trusted constructor supplies same guard/DB,
MEM/TSK owners, fixed Grant request_scope and synchronous bounded mock callback.
No public proof flag or fake Goal/lease. Input text <=16384UTF8bytes, output JSON
<=32768, reply<=8192; fixed context candidate limit10/recent records6/total32768
bytes. Always include current turn body. Drop oldest optional recent records to
fit, explicitly records_truncated; never silently drop candidate IDs/deps. If the
mandatory candidate+turn input exceeds cap, fail limit before budget/callback.
No model wording rubric or language target oracle.

R5. submit uses MEM.append key dumps(['PRI01.append',session,client_key]); MEM's
sanitized equality decides retry identity before PRI lookup. One durable raw
record/turn; PRI stores original Ref/hash, not raw secrets or copied input bodies.
Unique(session,client_key) and a short durable CAS pending→preparing with session
and nonce precede reserve/consume. Only the winning live invocation continues;
uncertain admission commit never grants callback entry. No timeout/takeover.
admitted/returned/applying are durable metadata phases; public pending covers
active phases. Snapshot ref/hash/fingerprint before entry and after return;
fingerprint is first-report F3 ordered IDs/revisions/open questions/withholding/
truncated, excluding state/epoch. Recheck again before dispatch, owner decides
actual state/revision in its own transaction. No re-inference/rewrite on stale.

R6. Callback owns no open SQLite transaction. guard.activity spans admission,
callback cessation and ending-record attempt. Raised/not-entered are distinct;
BaseException records known ending where possible, releases activity and propagates.
Retry only identical durable ending of known local output, never callback. PRI
model wire remains exactly {reply,proposal}; closed supported tags none,new_work,
answer,control(pause/resume/cancel/change),memory(stop_reference) per first report.
answer.record/change.origin is the current turn record; new_work origin host-bound;
all target IDs/question revisions must match snapshot, selected refs disclosed.
Unsupported continue/attach/remember/correct explicitly unavailable, not fallback.
No model grant/IDs/complete authority. Wrong-but-listed target is a semantic risk,
not cured by membership; host acknowledgement names actual owner-confirmed target.

R7. Before dispatch persist exact normalized intent, owner request and trusted
request_scope using dumps(['PRI01.effect',turn_id,kind]). Dispatch public idle-owner
method outside PRI TX. Known owner failure is durable failed and suppresses model
reply; uncertain owner outcome remains applying. Live owned continuation may only
retry that identical owner request. Reconciliation uses public original receipt;
startup after qualified old process death never calls the effect again. not_found
means interrupted, corrupt/unavailable stays held. All original synchronous local
SQLite paths must have ceased; no provider cessation inference.

R8. recover_turns in startup after TSK recovery and before finish_startup interrupts
old pending/preparing/admitted/returned without applying intent, and reconciles
applying receipts. Return {interrupted_turn_ids,committed_turn_ids,held_turn_ids}.
PRI has its own readiness: any unreconciled foreign-session live row blocks new
PRI callback/turn execution; controls remain available. Root's trusted host startup
orders both recoveries before TSK activation; no TSK private PRI SQL/readiness
callback or second host engine. A skipped PRI recovery fails closed; it does not
silently recover after ready. Is this sufficient for the trusted operator profile?

R9. One terminal PRI row and namespaced C14 result/error event atomically via
TSK.append_event on same active connection. key dumps(['PRI01.turn',turn_id]);
refs original record plus owner effect refs; omit work_ref. Owner state events
remain distinct. No new MEM assistant reply or C14 reply as model context (F10).
get_turn returns only confirmed receipt/reply/error. Structured control is separate
connection, no Primary/model mutex/MEM append/budget; stable PRI01.control key.

## Required response and proof limits

Return closed PAL.design-review/1 JSON for PRI01/1 with verdict ALIGNED/REFINE/
BLOCKED and six string sections value/responsibilities/contract_alignment/
evidence_limits/findings/recommendation. <=16000UTF8bytes. Precisely resolve R1 and
any contract contradictions, not a blanket second review of all code. Freeze
minimum mandatory fixed cases; Root retains original F1–F12 refinements and
does not create a human approval gate for technical method choices. No tests,
source hashes or full-source approval can be claimed by the tool-free reviewer.
