# PRI01-TSK/1 — frozen source-safe candidates, receipts and Primary allowance

Root adopts these independent TSK prerequisites from completed actual Opus5.5
PRI01 F1/F2/F7 and Astra's full-source PRI01-TSK-SEAMS proposal. Additional Opus
refinement hit its session limit; no report was received or adopted. This owner
scope needs no inference/PRI activation or new service/auth/cost. Base assignment
includes RECOVERY02's approved TSK611e0550 and this scope. Full PRI usefulness,
real-provider profile, broader C02 queries and future P001 remain separate.

TSK alone owns tasks_v5.py and its private tables. Separate Sol owns fixed tests,
Astra source, a separate context reviews exact bytes. Root integrates and owns
common contracts/final connection. Same-file TSK work is serial after RECOVERY02.
CO cannot read the complete TSK file because it exceeds64KiB; the existing
authorized native route is used, without another engine/state or partial-source
claim. Python stdlib only. No old/live DB migration or counters/receipt rewriting.

## Source-safe C02.list_candidates

`list_candidates({session_id,limit,goal_ids?}) -> Result[{works,truncated}]`.
Closed nonempty UTF8 session, strict int1..20, optional list of <=20 distinct
nonempty UTF8 Goal IDs; empty filter means empty result. Query is not implemented:
explicit query field returns unavailable, never silently ignored. Other extras,
wrong types/duplicates/bounds are invalid_input. No session ownership filter:
single-account latest non-superseded revisions, including completed/cancelled/failed.
Order newest matching work-bound C14 seq descending then Goal ID, count limit+1.
Each closed entry: `{work_ref,brief_summary,expert_id,state,open_questions,
dependency_refs,text_withheld}`; question `{id,text,revision}`. Summary is purpose
at most512UTF8 bytes, question1024; safe codepoint prefixes, no ID/ref truncation.
Total output <=131072UTF8bytes otherwise limit. No body/read fallback/private
MEM SQL. Empty works/truncated false succeeds, withheld still counts.

One owned read transaction on an idle isolation_level=None connection covers row
selection, typed immutable Brief/Grant/latest-state validation, questions, full
registered record dependencies and readonly gate. Required origin/Brief refs and
all open-question producing-call refs must be registered; preserve dependency
order and uniqueness, validate existing question/history invariants. Use all
registered record refs as conservative text dependencies. Gate them under existing
same-connection savepoint/total_changes checks. An ordinary denied/not_found/
unavailable source response withholds ALL summary/question text (empty strings),
retains IDs/revision/state/full deps and text_withheld=true. Source-gate protocol
violation, exception, mutation/commit, SQL or corrupt stored data is unavailable;
BaseException cleans owned read TX and propagates. available yields original safe
prefix text and false. No writes/events/replay/model/lease/budget, caller's active
transaction is refused rather than committed or taken over.

## Original successful receipt lookup

`get_create_by_key({key})`, `get_control_by_key({key})` return original successful
Result unchanged, not current state. Closed nonempty UTF8 key; missing namespace
key not_found, bad public input invalid_input, malformed/contradictory stored
input/result/body binding or SQLite failure unavailable. Read-only, may run in a
caller transaction, no BEGIN/COMMIT/gate/authority/config refresh/event/application.
No raw exception/path/SQL/body diagnostics; BaseException propagates.

Use actual C03.create/control namespaces. Check byte-canonical input, stored key,
strict input command/Ref/WorkRef/Brief/Grant and strict successful receipt fields.
Create binds original session/origin, revision1 row, immutable saved Brief/Grant
and Expert identity; ignore today's epoch/state and changed host config. Draft
conditions compare descriptions/check kinds against stored minted Conditions,
not invented IDs. Result WorkRef's original epoch may be older than durable row.
Control supports actual existing pause/resume/cancel and closed answer/change/
complete variants as historical reads; PRI never proposes complete. Validate
original target and result Goal/revision (change creates exactly next revision),
referenced immutable question/change/verification identity and typed result shape
where stored TSK evidence exists. Do not compare historical state to today's row,
re-gate stopped refs, inspect current VER usability, or query another owner's SQL.
Human command input epoch is intentionally not a current-authority assertion.
Corrupt is never safe absence. Historical receipts grant no new use/effect.

## Session-bound workless C15 branch

`reserve_budget({key,kind:"model",role:"primary"}) ->
{reservation_id,remaining:{host:int}}`. No work_ref field at all; explicit null
or unsupported workless kind/role invalid_input. Require actual enrolled ready
managed guard/session even on legacy store (otherwise unavailable/conflict).
Existing work-attached Expert/Step branches stay unchanged.

In the ordinary TSK transaction validate the existing finite model host row
(strict ints0..SQLiteMAX, used<=ceiling), safe premint reservation then increment
ONLY that shared v5_tsk_host model used. Store reservation with lease/work/idx
NULL, kind=model, role=primary, binding NULL and a TSK-owned reservation→session
binding. No second counter, Goal usage, Step check, fake Goal/lease, lease occupancy,
refund or double charge. Model0/exhausted gives limit; Step0 permits conversation.
Expert and Primary atomically compete for the same final model unit.

Before reserve replay/consume replay inspect qualified workless shape and complete
session binding; NULL lease alone is never proof. Own session UUID/profile/runner
must be registered ready and match reservation binding. Foreign-session replay or
consume refuses denied; unmanaged/missing/corrupt binding is unavailable. Same
reserve key/input/session returns original receipt and no debit; changed input
conflicts. `consume({reservation_id,call_or_operation_id})` binds once: repeat same
binding succeeds, another binding conflicts, no new counter. Primary owns the
call ledger and generates call ID from Turn, not model. Crash before PRI stores
reservation is consumed history, never refundable or callback entry permission.

## Fixed acceptance before source

Actual fresh managed file SQLite/HOST/MEM/TSK/ART/VER for session/reservation;
actual C03/control/question receipts, readonly active caller TX, changed configs
and stopped/corrupt sources. C02 cross-session/latest/terminal/order/truncation,
safe prefixes, withholding all text/full deps and malformed snapshots/gate faults.
Receipt exact historical equality after changes/stop/reopen; missing/corrupt/
wrong namespace/key/command/target binding and no callback/write. Workless model
zero/last unit/Step0, no Goal debit, replay/consume bind-once/foreign/new session,
corrupt row/session, premint/write fault/BaseException rollback, Expert contention.
No Primary mock/model execution here. Independent exact-source review and Root
full regression/Primary connection follow; prerequisite green is not whole PRI.
