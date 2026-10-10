# PRI01 proposal — bounded mock turn ingress

PROPOSED, NOT ADOPTED. Source snapshot e22c03611f98365ce70a3b56a5d5147b965aa085. Root owns shared contract changes. This investigates existing C01/C02/C03/C04/C05/C10/C14/C15 now; execution follows the pending recovery/startup-lock freeze and implementation. Note-only; no activation. P001 remains PROPOSED.

## Value and first useful flow

Small useful mock flow: save context → request work → receive an essential question → answer/change the same Goal → saved draft/checks → inspect → stop source and see historical/current usability. This exceeds the rejected draft-only screen. Mock callbacks do not prove authentic usefulness. Speech/controls remain available during Expert work.

First freeze supports proposals none, new_work, answer, change and pause/resume/cancel, plus explicit record reference-stop. Defer C03 continue/attach and derived memory remember/correct until their owner methods exist; unsupported proposals must return visible unavailable/invalid_input, never silently become new_work or none. C04 questions come from RUN/TSK, not a Primary invented question ID. A Primary reply may ask for an essential fact without creating work; later Expert questions use durable C04. Semantic conditions remain unknown; PRI cannot complete work or replace VER evidence.

## Actual seams and missing owners

| Contract | Available implementation | Necessary first-slice addition / restriction |
|---|---|---|
| C01 submit/get_turn | No v5 Primary/Turn owner or primary proposal parser | Small PRI-owned turn/invocation ledger and closed parser; no second task engine. |
| C02 candidates/get_work | TaskStore.get_work({goal_id,revision?}); no public candidate listing | TSK-owned bounded latest candidate listing under frozen C02 shape. PRI must not read private TSK SQL or fabricate a registry. |
| C03 create | IntakeStore.create(request, *, request_scope:Grant), inherited by TSK; short owned transaction | Trusted host supplies request_scope. Public original receipt lookup absent. C03 attach absent: defer. |
| C05 append/read/search/stop | MEM append sanitized exact input replay; C11 purposes; search limit1..50, literal same-session records, summaries empty; work_ref search unavailable | Reuse without inventing note memory or cross-work search. Explicit stop_record supported; remember/correct absent. Original receipt lookup absent. |
| C04/C10 | TSK ask/answer/change/pause/resume/cancel/complete; ask get_question_by_key only | Read-only original create/control/stop receipt lookup needed; ask lookup is not generic turn lookup. Model complete excluded. |
| C14/readback | EventReader.get_events; HostReader; inspect_session/render | Existing result/status readback; PRI final receipt/notices must not duplicate owner state events. |
| C15 mock invocation | MockInvoker bound to TSK lease/reservation, Expert role | Cannot reuse with a fabricated Goal/lease for ordinary conversation. Freeze minimal PRI-specific one-call ownership/budget seam. |

create/control/stop have no public get_by_key. Internal replay tables, ART lookup and C04 lookup do not meet C01 receipt recovery; this is a dependency.

## Proposed public and trusted interfaces

Keep exact C01 submit{client_key,session_id,text}/get_turn{turn_id} and declared statuses/reply/effect_refs/error. Callbacks are trusted constructor dependencies, not wire fields. Freeze exact value/error shapes/bounds before tests; no raw exception/path output.

Trusted host supplies current Grant ceiling and resolved request_scope; mock policy decisions are explicit fixture assumptions, not semantic authority proof. Model Grant/capability/approval/cost fields fail. create uses host intersection; change retains latest-prior ceiling. No regained allowance or external approval.

Suggested closed model output: {reply:str,proposal:<tagged closed object>}. Tags reuse C01 semantics: none; new_work{brief}; answer{work_ref,question_id,record_ref}; control{work_ref,command}; memory{operation}. control allows only pause/resume/cancel and change{brief,origin_record_ref}; memory allows only stop_reference{source_ref}. All other tags/extra keys/unknown fields fail before effect dispatch. PRI parser only; EXP unchanged.

For answer, record_ref must be the current saved user record. For change, origin_record_ref must be that record; derived/reused records must all be explicit context_refs. new_work origin is host-bound to that record, never model-minted. Target WorkRef/question/source refs must be members of the disclosed snapshot and allowed reference sets, with exact type/closed shape. No latest-work guessing, ordinal interpretation or fallback to arbitrary identifiers. Historical artifact/verification refs may be shown through user_view but are excluded from the first Primary model input/reuse set; their display is not new authority.

Membership proves exposure, not semantic correctness or complete provenance. Primary interprets; trusted host validates operation/repository/source obligations. Wrong-but-listed target and omitted dependency cases are required. Before provider proof freeze bounded host target/provenance policy; ambiguous intention asks without mutation, never an invented language oracle.

## Durable turn and finite invocation

1. Validate closed UTF8 input and fixed host byte bounds. C05 append uses host-namespaced session/client_key; persist turn_id, accepted-input identity/hash and record_ref. MEM compares sanitized input: freeze C01 consistently; never persist raw secrets merely to distinguish redacted inputs.
2. Unique (session_id,client_key): same accepted input returns same turn; altered input conflicts. Save pending snapshot/call identity in short PRI transaction. Repeated submit never starts another call.
3. Gather bounded C02 works/questions, C06 search without work_ref, exact C11 {ref}, purpose=model_context. Always include saved original. Persist metadata/ref/hash, not copies that bypass MEM stops. Bound candidate/record/total bytes, mark truncation; omitted candidates are not proof of uniqueness.
4. Recheck availability/candidates before entry; persist admitted call and finite host Primary budget, invoke once outside transaction. No escaped mock work. Save returned/raised separately from adoption. Ordinary failure makes no guessed effect; BaseException propagates after cleanup, preserving uncertainty when durable ending is unavailable.
5. Persist parsed proposal and exact owner request/key before dispatch. Recheck source/target/authority, call public owner, then save receipt and reply. Show only host-confirmed effect; none is conversation. Owner errors visible; model cannot claim work accepted/completed before commit.

PRI owns only its tables. Existing create/control/stop require idle autocommit; do not nest them under PRI BEGIN. Durable applying intent plus public receipt lookup covers the commit gap. Root must freeze a narrow owner-owned transaction seam if atomic adoption needs more than current owner checks; no PRI private SQL or model wait inside a transaction.

## Snapshot races and source-stop

C02 work summaries/open questions can carry record-derived text. Candidate listing must establish current usability of their registered dependencies before returning model-visible text, or exclude unavailable text with a visible disposition; otherwise PRI leaks stopped source through brief_summary/question text even when every C11 body is gated. This owner-side privacy obligation must be in the C02 freeze, not a PRI private-SQL filter.

Owner snapshots are separate. Recheck before entry and after return. Changed chosen revision → stale; mismatched/closed question → conflict/stale; stopped input → denied; transient/corrupt owner → unavailable. Epoch-only drift needs operation-specific rechecking, since C10 tolerates epoch. Owner transaction finally enforces state/revision/source; prechecks are not atomic authorization.

Persist bounded candidate-set fingerprint: added/changed candidates can invalidate unique semantic selection even if chosen row is unchanged. Recompare before adoption; stale/ambiguous stops without rerunning that turn. A new user turn can select current target. This conservative mock policy needs review; no latest-revision guessing, automatic retry or stale proposal rewrite.

If a used optional source stops after input exposure, reject adoption rather than merely drop it from proposal context. Already delivered model input cannot be recalled; prohibit subsequent input/use and current adoption. Original receipts replay as historical facts even after stop; replay does not authorize body reuse or a new operation.

## Effect replay, interruptions and immediate controls

Effect key is canonical dumps(['PRI01.effect',turn_id,proposal_kind]); one effect per ordinary turn. Persist exact normalized owner request plus trusted request_scope if applicable. Propose closed get_create_by_key/get_control_by_key/get_stop_reference_by_key({key}) returning original receipt/not_found. Root freezes names/namespaces; no private replay SQL.

Lost reply: recover original effect receipt without model call, grant refresh, new origin/Condition/event or body reuse. not_found permits saved request only when known never started and current authority holds. An uncertain applying operation requires reconciliation; absence/transient lookup does not prove cessation. unavailable/ambiguous stays visibly pending/interrupted. Original receipt is history, not permission to reuse stopped input.

Pending recovery must coordinate one host owner for DB, with PRI calls separate from Expert lease so speech is not blocked. Restarted pending/admitted turns are interrupted; never re-invoke same client_key. Returned proposal reconciliation needs adopted receipt/recovery rules, not assumed process-death cessation. No lock API adopted here.

Structured controls use a separate closed host endpoint (shape to freeze): saved original, stable client_key, explicit WorkRef/allowed command, no model/lexical parsing. Same receipt/source rules; no Primary mutex or callback wait. C10 pause/cancel drains Expert. Reject unknown/foreign target, complete/external command and changed request under same key.

TSK/MEM publish authoritative C14 effects atomically. PRI reply/error notifications require durable outcome and deterministic outbox/event key, not duplicate work/state events. EventReader/read consumer use user_view for drafts/history/current usability/errors. Escape display controls; never parse reply as state. get_turn receipt recovery and C14 ordering are distinct.

## Fixed acceptance before source and remaining decisions

Freeze approximately: duplicate concurrent submit one record/turn/call; key-input conflict; callback runs with no transaction; no inference on same-key response loss/restart; malformed/extra/out-of-set/wrong target proposals; stopped original/context/candidate text before entry and adoption; candidate-set/revision/question races; same-Goal answer/change exact provenance; new_work request_scope/no grant enlargement; provider-commit/PRI-commit gap lookup and ambiguous retention; immediate structured cancel while callback is held; history/structural-only/no complete; C14/readback with visible failures. All first tests are actual temporary SQLite plus clearly labeled mock callbacks; later provider proof is separately frozen, finite and uses existing no-extra-charge availability. No full quality corpus or new provider quota implied.

Root freezes C02 source-safe listing, PRI identity/bounds/budget, receipts, atomic adoption/outbox and recovery interface before source. These are technical decisions, not new human approvals. Authentic usefulness requires one later owner judgment on improved working output. No new login/payment/service is required for mock preparation. Existing access/refusals/unknown calls and D045 evidence policy persist. No release/P001/product acceptance.
