# P002-LIVE-v1 controller coverage audit

Audited source baseline: 11a5bb6 (runtime source unchanged from 0ae5e97).
The frozen matrix remains NOT_RUN. This mapping does not mark any live case PASS.

| Case | Existing deterministic evidence | Remaining actual-provider evidence |
| --- | --- | --- |
| K1 | `test_citations.py` exact sanitized record/note matching and rejection before artifact effects; claim source snapshots are host-owned. | Model uses supplied Mika/date/time/place, asks no unnecessary question, and adds no unsupported facts. Literal citation validation alone cannot prove these semantic properties. |
| A1 | `test_runtime_envelope.py::test_restart_bound_answer_enters_executor_and_completes_same_goal`; `test_http.py::test_explicit_question_answer_http_rejects_wrong_binding`; actual Runtime process-death recovery in `test_runtime_question_crash.py`. | Actual grouped essential question, visible bound answer UI, then same-Goal completion using supplied facts. Scripted proposals do not prove question selection. |
| G1 | `test_template_intake.py::test_generic_and_unmarked_template_requests_do_not_enable_preview`; mock transport compatibility in `test_runtime_envelope.py`. | Real generic draft completes without unnecessary factual questions or invented concrete details. Host template eligibility is not proof of model sufficiency judgment. |
| T1 | Explicit immutable template eligibility and runtime preview test in `test_template_intake.py`; `test_preview.py` literal placeholder, preview receipt, unverified outcome and completion exclusion. | Real provider selects the frozen preview contract and preserves declared literal placeholders. Eligibility permits a preview; it does not force model selection. Any expectation conflict must be reviewed and versioned before execution, never weakened after a failing result. |
| P1 | `test_runtime_envelope.py::test_two_partial_answers_end_in_one_incomplete_preview`; atomic exhaustion and concurrent dispatch tests in `test_preview.py`; two-answer bound in `test_questions.py`. | Real grouped question/follow-up with partial answers, no invented place, honest exhausted host preview, and no third open question. |
| F1 | Waiting-context forget in `test_questions.py`; forgotten answer metadata-only/no prompt source in `test_citations.py`; preview fencing and retained historical bytes in `test_preview.py`; read-only stale status in `test_http.py`. | Fresh owned host excludes the stopped given record from exact claimed sources and reconstructed provider prompt; model asks for required missing facts without reusing the stopped facts. Historical raw read is separate from source usability. |

Cross-cutting evidence: `test_native.py` covers concurrent finite call caps, failure accounting, proof expiry/clock changes, one-use proof markers, tool-free CLI/environment and owned child termination. These do not establish a new harness-wide deadline across multiple hosts or process restarts. That contract is still in the running official SWE review.

UI evidence in `tests/ui/question-flow.cjs` executes shipped JavaScript against synthetic DOM/HTTP; it proves explicit bindings and draft retention, not real-browser rendering or human usefulness. Actual browser observation and N1-07 direct human evaluation remain separate gates.

Preflight rerun: `live-preflight-full.txt` retained the restricted execution's 10 HTTP setup errors, all at loopback `socket.bind` with EPERM. No assertion failure established a product regression. The identical suite is rerun through approved escalation; its result is recorded separately in `live-preflight-full-authorized.txt`. No code, criterion, old database, or production host was modified to bypass the bind restriction.
