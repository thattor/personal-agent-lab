REFINE

# ASK01 SWE consultation — saved ask → waiting → answer on current TSK/RUN/MEM

Basis: `pal/tasks_v5.py` (TSK02/1 + COMPLETE01/1), `pal/mock_runner_v5.py` (RUN01/2), `pal/memory_v5.py` (MEM01/1), `pal/contracts_v5.py`. ASK01-PROPOSAL is not frozen; the items below are the technical resolutions Root must fix before code. No schema change to existing tables; TSK owns one new table. MEM/ART/VER are untouched.

## Wire shapes (no new Ref kind)

`question_id` is an opaque TSK-minted string (`question-<uuid>` via `_mint`). It never appears as a Ref; RefKind is unchanged. Checkpoint `open_question_refs` and C02 `open_questions` carry question ids/text, not Refs.

C04 (host-only, on TaskStore):
`ask({key, work_ref, step_id, question, missing_fact, source_refs:[Ref]})`
Reply value `{question_id, state:'waiting_input', work_ref}` — the C04 contract shape, also the stored replay receipt and the `get_question_by_key` result.

C10 extends the existing closed command object:
`control({key, work_ref, command:{kind:'answer', question_id, answer_record_ref}})`
`answer_record_ref` must be a record Ref, else invalid_input. Reply `{work_ref, state:'queued'|'paused', control_status:'none'}`; `open_question_id` is reserved (omitted in this slice since the single open question is resolved).

Read-only lookups (TSK-owned, no writes):
- `get_question_by_key({key})` → original ask result value, or not_found.
- `get_open_question({work_ref})` → `{open_question: null | {question_id, question, missing_fact, source_refs:[Ref], step_id}}`. Goal/revision checked, epoch ignored; no open question is a normal `null`, not an error.

## Schema ownership

TSK owns `v5_tsk_question(id TEXT PRIMARY KEY, goal TEXT NOT NULL, revision INTEGER NOT NULL, step_id TEXT NOT NULL UNIQUE, question TEXT NOT NULL, missing_fact TEXT NOT NULL, sources TEXT NOT NULL, status TEXT NOT NULL, answer_ref TEXT)` plus `CREATE UNIQUE INDEX ... ON v5_tsk_question(goal,revision) WHERE status='open'`, mirroring `v5_tsk_one_lease`. Statuses: `open|answered|closed` (`closed` covers source-stop; `superseded` is future change work). Replay rows use the existing shared replay table under commands `C04.ask` and `control`.

## ask: check order, then one atomic write

Inside `_transaction('C04.ask', key, request, op)` (BEGIN IMMEDIATE):

1. Shape: `_obj`/`_work`/`_refs`; invalid_input. `source_refs` need only be Refs ⊆ the adopted call's supplied refs (no kind restriction beyond stored reality).
2. Replay: identical canonical input → original receipt; different input, same key → conflict.
3. `_authority(work)`: exact current WorkRef including epoch → stale; active owned lease mismatch → denied; state!=running or pause/drain flag → conflict. State/control ordering sits after replay, before stored-state reads.
4. Step: missing → not_found; must belong to (goal,revision), be `started`, have `action.kind=='ask'`, and `dumps` of `{question, missing_fact, source_refs}` must equal the stored action fields → else conflict; corrupt wire → unavailable.
5. The step's call is `returned` and bound (guaranteed by begin_step; re-validate → unavailable).
6. `_gate` on the call's stored sources; stopped required input → denied/unavailable as today.
7. One-open-question rule via the partial unique index → conflict.
8. Atomic writes in the same transaction: step wire → `finished` with `result_refs:[]`; question row `open`; work state → `waiting_input`; exactly one C14 event kind `question` carrying the question text and source refs; replay receipt. There is no separate finish_step; calling finish_step on an ask-kind or non-started step → conflict, so double finish is impossible.

The lease stays active through ask and is closed only by the following release.

`begin_step`: add `'ask'` to the supported kinds (no collaborator needed; compose keeps `artifact_inspect`).

## release preserves waiting

Extend the preserved-state set in release from `('completed','cancelled','failed')` to also include `'waiting_input'` and `'paused'`. All admitted calls must still be ended (existing check holds: the ask call is returned and adopted). Latest intent wins: a cancel committed between ask and release leaves `cancelled`; a control pause on waiting_input sets `paused` directly and is preserved; drain flag → `queued`; otherwise the outcome applies; flags clear on success as today. RUN uses `outcome:'yield'`, reason `'waiting for answer'`. A crash in the ask→release window leaves an occupied lease: orphan occupancy stays blocked on reopen, consistent with existing no-recovery semantics.

## answer (control kind 'answer')

Owner command: `_current(work, epoch=False)` — goal/revision only. Order:

1. Shape then replay (shared `_transaction`, same command path as other controls).
2. Work not_found/stale.
3. Question: exists by question_id, belongs to (goal,revision), status `open` → else conflict; unknown id → not_found.
4. State gate: allowed only from `waiting_input` or `paused`; terminal/running/queued → conflict.
5. Answer record gate: kind record (else invalid_input); existing in-transaction MEM check (`_check_sources`) → not_found/denied propagate; a stopped answer record is denied, never silently adopted.
6. Same-transaction writes: question → `answered` with `answer_ref`; `_register` the record ref into `v5_intake_source` (conservative optional registration: later source-stop invalidates dependents, and the body reaches the next call via `optional_refs`); state waiting_input→queued, paused stays paused; one state event; receipt. Same-key replay returns the original; a new key on a resolved question → conflict.

`resume` is the only other site touching open questions: paused → `waiting_input` if an open question remains, else `queued` (state table).

## invalidate_by_refs (source stop)

Add `waiting_input` to per-state coverage and affected handling: matching registered deps → epoch+1 and state→`queued` (no lease), and close the open question (`closed`) when the stopped set intersects registered deps or the question's own `sources` — C05 requires checking question sources too. Paused rows keep paused but close an intersecting open question; an unaffected open question on paused work stays resumable to waiting_input. Completed history handling is unchanged.

## checkpoint / C02

`_claim_wire`: `open_question_refs` = list of open question_id strings for (goal,revision); empty today stays `[]`. `get_work` and the candidates response add `open_questions:[{id,text,revision}]`. `last_finished_index` unchanged.

## MockRunner (Unit B)

After a parsed `ask` action: `begin_step` → `persist(tasks.ask, {key: dumps(['C04.ask', work, step_id]), ...action fields})` → `release('yield', 'waiting for answer')`, returning the released result plus `question_id`. No finish_step and no result_refs for ask. Bounded lost-response behavior: on persistent ask unavailable, call `get_question_by_key` once to recover a committed receipt; success → release normally; not_found or still unavailable → `yield_or_retain('ask persistence unresolved')` retaining occupancy. Replay keys are fixed; no re-invocation, no second begin_step, no new inference on unknown outcomes; the existing 3-attempt limit applies.

The answer needs no new RUN path: after answer→queued, the next claim's `get_execution_context` exposes the registered record in `optional_refs`; `_read_context` supplies its body to the next call. If stopped meanwhile it is named in `excluded_refs`, never silently used.

Carry-over (C076): verify/complete authority refusals (conflict/stale/denied) are nonterminal — return to the bounded loop; only persistence-unavailable yields/retains. The same rule applies at the ask seam and must be encoded in the next RUN edit, not via extra release paths.

## Cases

- Success: ask commits question+finished step+waiting+event atomically; release frees the slot; answer → queued; next claim's context contains the answer record; same keys replay receipts with no new effects.
- Fault: failure inside the ask transaction rolls back everything (no half-finished step/question); lost reply recovered by key; persistent unavailable retains occupancy and returns unavailable.
- Pause: pause(waiting)→paused; answer while paused saves and stays paused; resume → queued (no open question) or waiting_input.
- Cancel: committed before ask → ask conflict, release→cancelled; after waiting → cancelled preserved by release; answer on cancelled → conflict.
- Source stop: question or dependency ref stopped → question closed, waiting→queued with epoch+1; paused stays paused; completed history untouched.
- Replay: identical key+input → original result, zero new events; same key different input → conflict; answer replay after a later terminal state returns the historical receipt only.

## Units, acceptance, required resolutions

Unit A (TSK owner): schema, ask, answer branch of control, release/invalidation/resume/get_work/checkpoint extensions, both lookups, tests — all in `pal/tasks_v5.py`. Unit B (RUN owner): ask dispatch and bounded lost-response recovery in `pal/mock_runner_v5.py`; starts only after Unit A's seam is frozen. Contracts owner records the wire shapes above.

Acceptance: real temporary-SQLite MEM/TSK run of ask→waiting→answer→claim→context-contains-answer, every case above with controls committing during the mock wait via barriers (no sleeps), and proof of no double finish_step.

Required to freeze: the ask/release lease split, checkpoint field typing (id strings), the closed-question status name, answer registration as optional ref. Future/excluded: C10.change and superseded flow, restart recovery, real models, semantic checks, PRI/UI rendering beyond the C14 event, EXE adapters, auth/cost/live DB, unknown-call actions.