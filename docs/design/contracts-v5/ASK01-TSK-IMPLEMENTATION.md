# ASK01/1 TSK implementation

Native Astra authored this isolated TSK owner from frozen ASK01-SCOPE at
744ca12c130ce8ca8c7ac7787292c4e871182335. The fixed independent test file is
unchanged: SHA256 5ee0f9fb2a605ea6ef06ff991cb7e028b29ac5de31f0a45f9873c8ea7b26c6a0.
Only tasks_v5.py and this note are authored here. No RUN, MEM, shared wire, tests,
canonical records, migration or live DB writes are included.

## Public behavior and storage

TaskStore adds ask(request), get_question_by_key({key}) and C10 answer dispatch
with exactly the frozen shapes. One new v5_tsk_question table stores TSK-owned
question text/identity/status/selected refs and nullable answer Ref. A unique Step
binding and a partial unique open-question index per Goal prevent duplicate open
questions. There is no question Ref kind and no answer body copy.

Ask validates input before replay, then current authority, stored Step/call binding,
ended lease readiness and all actual producing-call sources. Selected duplicate
refs retain their canonical input identity. Ask atomically finishes its Step,
saves the question, sets waiting_input, closes the ended lease, clears flags,
emits the owning question event and stores replay. It adds no budget reservation
or refund. Ordinary finish_step rejects ask with conflict.

The completion readiness predicate is extracted into _ready_to_close with one
optional asking Step identity. Completion retains its former predicate; ask may
finish exactly that started Step, with every other returned output adopted and no
admitted call. All current-lease call WorkRefs match current work, indices are
strict bounded integers and wire/SQL/call bindings agree. Historical finished
Steps retain their legitimate prior epochs.

Question reads validate both directions: each question has its actual finished ask
Step/returned call, and each finished ask Step has its question. Text/selected refs,
WorkRef, producing lease, index and registered full-call provenance are checked.
Answered records must remain registered; stopped records remain represented.
The historical key getter checks its original receipt against this durable binding
without gating current usability or granting present execution authority.

Answer checks Goal/revision while canonical replay still includes the original
epoch. It gates question dependencies and the new answer in one transaction, then
answers/registers the optional record/emits the event/queues or preserves paused.
A new key for an already answered/closed question conflicts; same-key replay is
history. It never modifies required Brief refs or budgets.

get_work populates the existing open_questions field. claim reports open question
IDs in checkpoint and all ordered answered links in pending_inputs, including
stopped answer Refs. Claim does not consume links. Body and model-link eligibility
remain RUN's C11/provenance responsibility, not a TSK availability fabrication.

Waiting pause and open-question resume preserve the waiting reason. Cancel closes
open questions. Stop increments epochs as before, but closes an open question only
for an intersection with full producing-call dependencies (including required refs).
Unrelated historical optional stops retain waiting/open or paused/open. Answered
questions never reopen; completed history and cancelled/failed handling are retained.
Existing paused works without a question or with a draining lease remain valid.

All mutation uses existing caller/owner transaction boundaries. Exceptions roll back;
BaseException propagates after rollback. Callback COMMIT cannot be retroactively
undone; callbacks remain trusted host code. Only temporary SQLite was exercised.

## Verification and boundaries

Commands used /opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests
-p PATTERN -v. Final results:

- test_tasks_ask_v5.py: 17 PASS (exit 0), /private/tmp/pal-ask-tsk-fixed-final.log.
- test_task_completion_v5.py: 22 PASS (exit 0), /private/tmp/pal-ask-tsk-completion.log.
- test_task_artifact_binding_v5.py: 16 PASS (exit 0), /private/tmp/pal-ask-tsk-binding.log.

Broad test_task*.py initially ran 91: 90 PASS, one superseded legacy assertion at
tests/test_tasks_v5.py:658 expects ask to be unavailable. ASK01 now explicitly
supports it. Tests were not edited. Root was notified to adapt the old unsupported
Action fixture in integration; log /private/tmp/pal-ask-tsk-regression.log (exit 1).
An explicit unittest selection of all other TaskTests passes; exact selection and
result appear in /private/tmp/pal-ask-tsk-existing-applicable.log. This does not
represent an unmodified full-suite PASS or a relaxed acceptance requirement.

The fixed ASK tests execute real temporary MEM/TSK, including post-write faults,
KeyboardInterrupt/SystemExit, stopped selected/unselected inputs, linked optional
answers, old Steps, pause/resume/cancel, replay and two-connection control order.
Initial owner run was already green; retained /private/tmp/pal-ask-tsk-first.log.
Actual RUN+ART+VER+READ01 demo/integration and full regression are Root-owned and
NOT_RUN here. Author execution of independently written tests is not independent
source review. General recovery, real model/semantic judgment, PRI/UI, service
activation and whole-product usefulness remain outside this slice.
