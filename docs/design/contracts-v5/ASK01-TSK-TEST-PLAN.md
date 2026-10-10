# ASK01 immutable TSK acceptance inputs

Source base `7ee3ed435026f17ec42ffd58f4e042f031073dcd`, isolated
`codex/pal-ask-tsk-tests`. The test author owns only this note and
`tests/test_tasks_ask_v5.py`; Astra owns the later TSK source. No test self-review
is claimed. Adopted ASK01-SCOPE governs the fixture; Root clarified that ordinary
finish_step on a valid ask is **conflict** after existing missing/stale checks,
and a cancelled work's valid closed question answer is conflict after normal
work/revision/question lookup. These two assertions implement that disposition.

## Seventeen public-owner methods

The fixture uses actual TaskStore + MemoryStore + EventReader on a fresh temporary
SQLite file. Records, intake, claim, registration, model reservation/admission/end
and Step creation use public owners. No provider/model callable, live DB, sleep,
auth/cost or external calls are involved. No additional test-helper dependency:
include current `pal/tasks_v5.py`, `memory_v5.py`, `events_v5.py`, `intake_v5.py` and
`contracts_v5.py` plus their existing imports as ordinary repository inputs.

Acceptance covers:

- Atomic ask: finished empty-result Step, waiting_input, one selected-ref question
  event, unchanged epoch/budgets, inactive lease, denied later release and no waiting
  claim. C02 open_questions has its existing exact id/text/revision shape.
- Answer: optional source registration without required-source changes, unchanged
  budgets, queued/paused transition, ordered question/Step/record claim links,
  non-destructive claim replay and actual checkpoint open IDs.
- Historical ask/answer receipts after answer/cancel/stop, new-key resolved-answer
  conflict, changed canonical request conflict including epoch changes; duplicate
  AskAction refs accepted and retained in input identity.
- Pause/resume around an open question, paused answer, cancel closure/no revival;
  selected and unselected producing-call dependency stop closes and queues;
  unrelated historical optional stop preserves a paused open question and resume
  returns waiting. A legitimate earlier-epoch finished report Step remains valid.
- Multiple answered links remain ordered and stopped answer metadata is retained
  without reopening its question. Missing/foreign question, wrong revision/kind,
  stopped answer, mismatched action and unknown Step fail without key burn.
- Readiness/integrity: actual saved wire/SQL index consistency, bool index and unknown
  status, malformed call WorkRef, and extra admitted/unadopted returned activity.
  Valid old WorkRef in a current-lease call must fail closed; the freeze has no
  distinct error-code disposition there, so stale or unavailable is accepted.
- Post-write Exception/KeyboardInterrupt/SystemExit in ask and answer restores the
  complete durable SQLite dump and leaves an idle connection/key retryable. Faults
  intercept actual Connection.execute mutations at several deterministic write
  positions; rollback total_changes is deliberately not compared.
- A second real connection commits pause/cancel/source stop before ask, then the
  first observes the frozen failure and absent receipt. No timing assumptions.

Small SQL fault/corruption probes touch the **existing** TSK call/Step/usage/lease
layout already present at the frozen source. They do not choose or directly write
new question storage. Deliberately injecting impossible extra call rows tests the
readiness failure boundary; it is not evidence those rows arose through a supported
admission. Public success paths never use SQL Step insertion or fake MEM state.

## Author evidence and limits

Exact command:

```
/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_tasks_ask_v5.py -v
```

Current RED:17 tests fail at baseline begin_step ask returning unavailable after
real MEM/TSK/call preparation. Feature-specific bodies beyond that boundary remain
NOT_RUN. Log: `/private/tmp/pal-ask-tsk-tests-red.log`. AST and `git diff --check`
PASS; no fake implementation or skip is present. Tests insert the repository root
for isolated discovery. This test-only increment does not claim ASK integration,
feature correctness, review approval or product completion.

Root still owns actual RUN/ART/VER/READ continuation, completion/demo, full regression
and independent source review. File reopen, exhaustive mutation-point/race permutations,
maximum-epoch and new-question-row tamper probes can be added by Root when actual
source/layout exists; these seventeen fixed tests are bounded owner acceptance,
not a claim that every failure path has been exhaustively exercised.
