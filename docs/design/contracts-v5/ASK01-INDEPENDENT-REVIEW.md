# ASK01/1 independent source review

Final verdict: **APPROVE**, bounded to frozen ASK01/1 and the exact author sources
below. Reviewer: native Sol6.1 context `int00_sol_review`. TSK source was authored
by native Astra, with fixed TSK acceptance tests authored by a different Sol
context. RUN source was authored by native Sol context `art_native_sol`. This
reviewer authored the fixed RUN acceptance tests but did not author either source
implementation. Passing those fixtures alone was not used as source approval;
independent code inspection and additional counterexamples produced both findings.
Root owns integration, actual-owner connection tests and canonical evidence.

## TSK

Original source `7caaa2adc7c01cf2db576d23f3ca990b64464ac2`: **REQUEST_CHANGES**.
P1 at `pal/tasks_v5.py:888`: the new question-ID mint callback had no transaction
ownership guard before subsequent owned writes. In a fresh temporary SQLite
fixture, a trusted `id_factory('question')` that executed COMMIT and returned a
valid ID caused ask to return unavailable while finished Step, open question,
waiting_input, inactive lease, event and replay persisted through autocommit.
The cause was continuing writes after loss of the transaction, not evidence of
host-code sandboxing or a promise to undo a callback's own COMMIT.

Final source `3b076752cd2699421cba91e8401413a2f343d514`: **APPROVE**.
The limited rereview checked the diff introducing a savepoint, current-TX and
`total_changes` checks before the first owned ask write. Independent execution
confirmed COMMIT, ROLLBACK, COMMIT+BEGIN, ROLLBACK+BEGIN and WRITE callbacks return
unavailable with no DB delta, leave no open transaction, and allow normal retry.

Executed with `/opt/homebrew/bin/python3.13 -E -s -B`:

- Original source: `-m unittest discover -s tests -p test_tasks_ask_v5.py -v`:
  17 PASS; `test_task_completion_v5.py`: 22 PASS;
  `test_task_artifact_binding_v5.py`: 16 PASS.
- Original independent temporary-DB probes: reopen receipt succeeded; deleted
  question, changed question text and future Step epoch failed closed without
  writes; maximum-epoch source stop rejected without writes. The mint failure
  above was reproduced. These unchanged probes were not repeated on the fix.
- Final source: `-m unittest discover -s tests -p test_tasks_ask_v5.py -q`:
  17 PASS. Root's `tests/test_tasks_ask_integrity_v5.py` loaded via
  `importlib.util.spec_from_file_location`, with author source and fixed fixture
  paths explicitly asserted: 1 method / 5 subcases PASS. This was execution by
  the reviewer, not reliance on an author's test receipt.

An initially guessed plural artifact-binding filename matched zero tests; it
provided no evidence. The correct singular filename was then executed as above.

## RUN

Original source `a7ceb54eb00c6ded2ea1ad9dc7c6ec1fa2cc3e9a`:
**REQUEST_CHANGES**. P2 at `pal/mock_runner_v5.py:333–359`: historical linked ask
Step validation checked binding/action/status but did not enforce the closed Step
shape. Independent owner-double probes adding `error=1`, `error='ask failed'`, or
`unrecognized='hidden'` each allowed reservation and one Expert call, passing the
malformed Step and pending association to C12. The gap was RUN owner-response
validation; the separately reviewed actual TSK question reader rejects this
corruption, so no actual-TSK corruption bypass was claimed.

Final source `f0efa09bb5927030c9bf4c26f79516252a4c0a37`: **APPROVE**.
The limited rereview checked the added exact six-field linked ask Step shape.
Root's three regressions confirmed rejection before reservation/inference, an
unavailable result and no failed release.

Executed with the same Python flags:

- Original source: `-m unittest discover -s tests -p test_mock_ask_v5.py -v`:
  15 PASS; `-m unittest discover -s tests -p 'test_mock_*v5.py' -q`:
  77 PASS; the three independent malformed-Step probes reproduced the gap.
- Final source: `-m unittest discover -s tests -p test_mock_ask_v5.py -q`:
  15 PASS. Root's `tests/test_mock_ask_integrity_v5.py` loaded via
  `importlib.util.spec_from_file_location`, explicitly asserting author source
  and fixture paths: 1 method / 3 subcases PASS.

## Limits

Both final author worktrees were clean and HEAD unchanged after the read-only
reviews. No source/canonical edits, remote/model/provider calls or real DB access
were performed. Disposable probes used temporary SQLite or synthetic owners.
Final rereviews were limited to the reported findings and their corrective diffs;
there was no new broad-suite run. Actual TSK/RUN connection, demo and full
regression are Root-owned evidence, not independently executed claims in this
note. No semantic answer sufficiency, restart adoption, service activation or
whole-product acceptance is implied.
