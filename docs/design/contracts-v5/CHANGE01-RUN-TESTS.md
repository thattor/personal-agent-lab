# CHANGE01/1 fixed RUN tests

Author base e0fbdc23602e2a0cf6dc8f2c0590aaae459619a8. Frozen scope SHA256 fdd1fe51f1d8931bb900f21f4dd4b097c1e17ea5cab838b905553b22cbfaf62c. Only new test, this note and uniquely named run-tests logs are owned. RUN/TSK/ART/VER source and existing fixtures are unchanged. No blanket RUN patch is justified by these results.

## Coverage and evidence

11 methods: 10 public-owner-double methods and one actual in-memory MEM/TSK/RUN admission seam. Double methods include subcases for compose/ask/report returned after change; pause→second change→shared-stop and cancel latest-intent settlement; raised cessation; retained started compose/report; retained ask; retained finished compose with verification; admitted call occupancy until return; save/finish/ask/verification change boundaries; next-revision progression with cumulative fixture usage and retained history. Assertions count model entries/reservations, prohibit completion/adoption after fencing, check release's old request and higher-revision response, and order cessation before release. No sleeps, threads, external calls or live DBs.

Retained ask necessarily performs one public ended-call recheck and one stale C04 request; retained finished compose necessarily reads historical C02 and makes one stale VER request. The tests prohibit retries, lookup recovery, new inference/reservation, ART save and complete in those cases. They do not require zero necessary authority checks. This matches current source seams before the ordinary execution-authority check.

The minimal actual-owner case changes during an admitted mock report, then expects old output discarded and latest queued WorkRef returned. Current unchanged TSK rejects the exact frozen command as invalid_input. Final baseline is honestly RED: **11 run, 10 PASS, 1 FAIL**, 0.023s, exit1. Failing assertion reports `invalid_input: invalid task request`; it is not a RUN defect or fixture error. Its later no-extra-inference/historical superseded assertions remain unexecuted until CHANGE source exists.

Exact command:

`/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_mock_change_v5.py -v`

Retained final log: evidence/operations/change01-20261009/run-tests-final-red.log. AST parsing passed; git diff --check passed. Imported fixture modules use aliases, so their TestCase classes are not duplicate-discovered by this new pattern.

## Fixture correction and retained chronology

Initial double run (run-tests-baseline.log) had 9 PASS/1 FAIL: next claim reused the fixed fixture lease ID, triggering MockInvoker's correct no-duplicate call identity fence. Cause was fixture construction, not feature behavior. The correction gives each new fixture lease a new identity and checks callback admission in the current trace segment. The corrected double-only run (run-tests-fixed.log) passes all10. This fixture failure does not count as acceptance RED. Prevention: when exercising a subsequent claim, verify fresh lease/call identity and cumulative counters separately.

The first actual-owner run (run-tests-acceptance-red.log) failed on callback count2 because unsupported change allowed the unchanged baseline to continue. Final test checks the first change receipt before downstream callback-count expectations, making the missing feature cause explicit. All original logs are retained; no preferred timing, skipped assertion or fake implementation was used.

## Dependencies and limits

Fixture dependencies: tests/test_mock_ask_v5.py (AskOwners); tests/test_mock_completion_v5.py (SyntheticOwners/value). The requested test_mock_runner_v5.py and test_mock_complete_v5.py filenames do not exist at this base; actual neighboring completion/execution fixtures were inspected. New imports explicitly add project and tests paths for -I -S discovery. Actual-owner imports use pal/contracts_v5.py, tasks_v5.py, memory_v5.py, sanitize.py and mock_runner_v5.py.

The revision double deliberately models TSK stale gates, latest control precedence and cumulative usage. Its history preservation assertion proves RUN does not touch that fixture history, not real ART/VER persistence or actual budget accounting. Actual ART/VER history, cross-owner races, SQL index/corruption, changed-grant headroom, source availability and multiple-connection ordering remain Root/pure-TSK fixed tests. No whole-suite/product/service/provider/PRI/UI/semantic completion claim. Root will execute this immutable file after TSK implementation and connect actual owner histories separately; independent source review remains separate from this test author.
