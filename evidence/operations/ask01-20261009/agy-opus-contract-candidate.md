CANDIDATE
# ASK01 contract-reconciliation plan: one step

## Step 1: instructions (under 1000 bytes)
Write only `ASK01-SCOPE-CANDIDATE.md`. Use the exact text under "Draft" below. Its first line must be CANDIDATE and it must stay under 2200 words. Do not write code, tests or other files. Run no tools, services or agents. Make no claim that tests passed. Root owns the freeze and adoption. Any change to the technical meaning goes back to Root as an unresolved item.

## Draft (ASK01-SCOPE-CANDIDATE.md)

CANDIDATE
# ASK01/1: one saved question, saved answer and resumed draft (scope candidate)

**Status.** This is a candidate for Root to freeze at BASE a58cde7. It is not authority to implement and it claims no tests. It reconciles three inputs against the actual `tasks_v5` / `mock_runner_v5` / `memory_v5`:
- ASK01-PROPOSAL;
- ASK01-SWE-CONSULT (REFINE);
- the Opus READ01 NEXT ASK (REFINE).

**Value.** The flow is: mock ask → `waiting_input` (no lease) → saved user answer → a later explicit run → compose → verify → completed → readback. It uses stdlib, temporary SQLite and a mock Expert only. Existing owner authority covers it; there is no new gate.

## 1. Decision: atomic ask closure (adopted)

This replaces the SWE consult's "ask leaves the lease active; release preserves waiting_input". C04.ask closes the already-ended current lease in its own transaction, the same way C10 complete does. No release follows a committed ask.

Why this is sound against the actual invariants:
- **Cessation.** Ask requires the step's call to be `returned` and adopted, so `end_call` has already been recorded. Any `admitted` call → conflict.
- **Started steps.** The only started step allowed is the ask step itself, and ask finishes it.
- **Latest intent.** Ask requires the exact epoch, `running`, and no pause or drain. A cancel, stop or pause committed before the ask makes the ask fail, and the ordinary release then applies the existing precedence. Intents committed after the ask see `waiting_input` with no lease.
- **Old epoch.** Ask never closes an old-epoch lease. Ordinary release keeps its old-owned-epoch path.
- **release is unchanged.** After a committed ask, release returns denied because the lease is inactive, so it cannot overwrite `waiting_input`. The preserved-state set is unchanged.

**Invariants.**
- An open question exists exactly when the state is `waiting_input` or `paused`.
- A `waiting_input` or `paused` work never holds an active lease.
- Claim takes queued work only, so claim never sees an open question, and `checkpoint.open_question_refs` is always `[]` at claim.

**Fallback split (only if Root rejects atomic closure).** Ask keeps the lease and the `running` state. `release('yield')` then maps to `waiting_input` when this lease created an open question, with precedence: cancelled → close the question; pause → paused; drain → close the question and queue. Answer and control must reject while the lease is active. This is not preferred: it adds a waiting-with-lease window and more release branches.

## 2. TSK persistence (Unit A)

**New table** `v5_tsk_question`:

| Column | Type / constraint |
|---|---|
| `id` | PK |
| `goal`, `revision` | |
| `step_id` | UNIQUE |
| `question`, `missing_fact` | |
| `sources` | JSON |
| `status` | CHECK open/answered/closed |
| `answer_ref` | JSON NULL |

- Add a unique partial index on `(goal) WHERE status='open'`.
- `question_id = _mint('question')`. It is opaque and never a Ref; RefKind is unchanged.
- No existing table changes.
- Replay uses the shared table under the commands `C04.ask` and `control`.

**Step handling.**
- `begin_step`: add `ask` to the supported kinds. Its sources must be within the call's supplied refs; the existing validator enforces this.
- `finish_step` on an ask-kind step → conflict, checked after the existing not_found/stale checks. Double finish is impossible.

### C04 ask

`TaskStore.ask({key, work_ref, step_id, question, missing_fact, source_refs})` → `{question_id, state:'waiting_input', work_ref}`.
- `work_ref` is the exact current WorkRef; the epoch is unchanged.
- This same value is the receipt and the `get_question_by_key` result.

Precedence (BEGIN IMMEDIATE; the first failure wins):
1. **invalid_input:** strict shape; `key` and `step_id` are ids; `question` and `missing_fact` are str; `source_refs` are Refs.
2. **Replay:** identical canonical input → the original receipt. This holds even after a later terminal state or stop; the receipt is history. Different input → conflict.
3. **`_authority(work)` with exact epoch:** not_found → stale → denied (no active lease, or a lease for another work) → conflict (state is not `running`, pause flag, drain flag).
4. **Step checks:**
   - unknown step → not_found;
   - corrupt wire or call row → unavailable;
   - saved goal/revision or wire `work_ref` differs from `work` → stale;
   - call lease differs from the active lease → denied;
   - any of these → conflict: status not `started`; kind not `ask`; request fields differ from the stored action; call not `returned`; `call.step` differs from `step_id`.
5. **Lease readiness (same as complete):** another admitted call, another started step, or a returned call without a finished step → conflict. An unknown status → unavailable.
6. **`_gate(call sources)`:** not_found / denied / unavailable.
7. **Existing open question for the goal** → unavailable (invariant breach).

Writes, all in one transaction:
- step → `finished` with `result_refs:[]`;
- question row `open`;
- state → `waiting_input`;
- lease `active=0`;
- flags `0/0`;
- exactly one C14 event, kind `question`, with text = question and refs = `source_refs`;
- the receipt.

No budget is spent or refunded. Any failure rolls back everything.

`get_question_by_key({key})` returns the stored `C04.ask` success value, or not_found.
- Strict shape; otherwise invalid_input.
- Read-only, with no authority check.
- A found receipt is history, not current state.

### C10 answer

`control({key, work_ref, command:{kind:'answer', question_id, answer_record_ref}})` → `{work_ref, state:'queued'|'paused', control_status:'none'}`.
- `open_question_id` is omitted.
- Object commands dispatch by `kind`: `complete` (unchanged), `answer`, anything else → invalid_input.
- Host key: `dumps(['C10.answer', record_id])`.

Precedence:
1. **invalid_input:** closed keys; `question_id` is an id; `answer_record_ref` is a Ref of kind `record`.
2. **Replay:** a later terminal state still returns the historical receipt. Different input → conflict.
3. **`_current(work, epoch=False)`:** not_found → stale (revision).
4. **Question:** unknown or another goal → not_found; older revision → stale; status answered or closed → conflict.
5. **Open question but state is neither `waiting_input` nor `paused`** → unavailable.
6. **`_gate((answer_record_ref,))`:** not_found / denied / unavailable. A stopped answer is never adopted.

Writes:
- question → `answered`, with `answer_ref`;
- `_register` the record as an optional dependency of the current revision;
- `waiting_input` → `queued`; `paused` stays `paused`; epoch unchanged;
- one `state` event, "question answered", refs = [answer];
- the receipt.

A new key on an already answered question → conflict.

**How the answer reaches the next call.**
- `pending_inputs` does not change and stays `[]`.
- The next claim's `get_execution_context` lists the answer in `optional_refs`, and `_read_context` supplies its body.
- If the record has been stopped, it is named in `excluded_refs` and never used silently.
- The finished ask step, carrying the question text, appears in the C12 steps under the existing provenance rules.

### Other controls
- **pause:** `waiting_input` → `paused`, plus a state event. Other states behave as today.
- **resume:** `paused` → `waiting_input` if the goal has an open question, otherwise `queued`. The pause flag is cleared.
- **cancel (nonterminal):** existing behavior (cancelled, epoch+1), plus the open question is closed in the same transaction. A later answer → conflict.
- **Budget:** answer, resume and pause never reset it.

### invalidate_by_refs (source stop)

Keep check-all-before-write, the coverage check, and the completed/cancelled/failed handling. The match set is registered dependencies ∪ the open question's sources.

| State | Matched | Result |
|---|---|---|
| `waiting_input` | yes | close question, epoch+1, `queued`, event |
| `paused` | yes | epoch+1, stays `paused`, close any open question; resume → `queued` |
| `running` | yes | existing epoch+1 + drain; a pending ask then fails stale |
| any | no | unchanged |

- Allow `waiting_input` in the state guard; a maximum epoch is still unavailable.
- A source stop never resumes paused work and never reopens terminals.
- A source stop never drops required-source checks: if requeued work has a stopped required source, the existing `register_sources` fails it once at the next claim.

### C02 / checkpoint
- `get_work` adds `open_questions:[{id,text,revision}]` for the current revision, overwriting any intake value. The demo/host consumer uses this to find `question_id`.
- `checkpoint.open_question_refs` holds open question id strings; it is always `[]` at claim.
- No `get_open_question` getter.

## 3. RUN (Unit B, starts after Unit A is frozen)

**Ask action.** After the existing `begin_step`, call `persist(tasks.ask, ...)` with a request built from the stored step:
- `key = dumps(['C04.ask', step.work_ref, step_id])`;
- `work_ref = step.work_ref`;
- the remaining fields from `step.action`.

Outcomes:
- **ok with a valid receipt** (`{question_id, state:'waiting_input', work_ref==work}`): return success `{status:'waiting', question_id, state, work_ref, lease_id, step_id, steps, call_ids, excluded_refs, excluded_step_ids, verification?}`. No release; the turn ends.
- **unavailable after 3 attempts:** call `get_question_by_key({key})` once, within the local 3-attempt limit.
  - A valid receipt → the same success.
  - Otherwise `yield_or_retain('ask persistence unresolved')`. If the ask had committed, release is denied → unavailable and the waiting state is preserved. If it had not, release refuses an ordinary yield and occupancy is retained.
- **any other error** (conflict/stale/denied/not_found/invalid_input): call `release('yield', 'ask refused', code)`.
  - A fenced cancel/pause/drain applies the existing precedence and abandons the ask step.
  - Otherwise release refuses, and RUN returns the original ask failure with occupancy retained.
  - Never use the `failed` outcome; never start new inference.
- **ok but malformed receipt:** unavailable, no release.

**Retained-tail ask.** At retained-lease entry, before the generic started-step check: if the only started step is the tail, its kind is `ask`, and its call is returned and adopted, reissue the identical ask (same key and request) without invoking the Expert. Then apply the same outcome handling. An active lease means the ask had not committed.

RUN needs no new answer path.

**C076 correction (same edit).** In `finalize`, a verify conflict/stale/denied returns `None` (nonterminal) instead of calling `failed(...)`. Context authority and release fencing then settle any newer intent. A persistent verify unavailable stays `yield_or_retain`. Completion handling is unchanged.

## 4. Occupied-window scenarios (must pass)
- **S1.** Pause, cancel or stop between `begin_step` and ask (mock held at a barrier): ask fails conflict/stale; release → paused/cancelled/queued; the ask step is abandoned; no question exists; nothing is refunded.
- **S2.** The same controls after the ask commits: there is no lease. pause → paused; cancel → cancelled with the question closed; stop → question closed and queued.
- **S3.** Work A is running and holds the lease; work B is waiting; a shared ref is stopped. Atomically, A is drained and B is closed and queued. B cannot be claimed until A releases.
- **S4.** B is paused with an open question; a stop leaves it paused and closes the question. resume → queued; answer → conflict.
- **S5.** Answer racing stop, cancel or pause on two connections: commit order decides. The loser gets conflict, or paused is kept.
- **S6.** Answer record stopped before the answer → denied. Stopped after the answer → queued with epoch+1, the record is excluded at the next claim, and the question stays answered.

## 5. Acceptance (essential)
- **A1.** Real temporary SQLite with MEM/TSK/ART/VER:
  1. intake → `run_once` (mock asks) → `waiting_input`, lease inactive, finished ask step, one question event, `get_work.open_questions` populated;
  2. MEM append of the answer → answer → queued;
  3. `run_once`: context contains the answer body → compose → verify MET → completed → READ01 readback.
  Budgets stay cumulative throughout.
- **A2.** An injected failure at each ask/answer write rolls everything back; BaseException propagates.
- **A3.** Replay and conflict for ask, `get_question_by_key` and answer, including after completion: historical receipts, zero new events.
- **A4.** A lost ask reply is recovered by key with no second Expert call. A persistent unavailable retains occupancy. A retained-tail ask replays without inference.
- **A5.** Scenarios S1–S6.
- **A6.** Pause, answer while paused, and resume in both directions; cancel closes the question.
- **A7.** Every precedence row; `finish_step` on ask → conflict; release after a committed ask → denied with the state unchanged; the one-open-question invariant.
- **A8.** C076: a verify conflict/stale/denied never releases `failed`.

Use barriers/Events, never sleeps. Prior suites stay unchanged.

## 6. Ownership

| Owner | Files / work |
|---|---|
| Unit A, TSK (SWE-2 High, isolated workspace) | `pal/tasks_v5.py`, `tests/test_tasks_ask_v5.py` |
| Unit B, RUN (SWE-2 High, separate workspace, after A is frozen) | `pal/mock_runner_v5.py`, `tests/test_mock_runner_ask_v5.py` |
| Optional AGY Sonnet 5.5 helper | `tests/test_ask_connection_v5.py`, against the frozen seams only |
| Root/SOL | freeze ASK01-SCOPE, contract notes, `scripts/demo_ask_v5.py`, integration, full suite, evidence |
| Independent Opus | review of integrated code and design; not an author |

No two owners edit the same source file.

## 7. Excluded
- C10.change / superseded, attach;
- general or restart recovery, orphan clearing;
- UI/PRI, real provider, semantic checks, EXE/external sources;
- auth/cost/payment, live DB/migration, publication;
- unknown-call actions or retries;
- a question Ref kind;
- READ01 consumer changes for question events;
- a repeated human gate.
