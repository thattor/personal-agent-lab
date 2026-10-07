# C036 independent harness review

Source: read-only subagent `astra_acceptance_review`, after the first C036 extension
and before any actual regression call. Product files are unchanged from1a14de9.

P2 findings, reproduced with in-memory records (no provider/filesystem mutation):

- A planned request/conditional answer can verify as completed with captured
  local_draft, controller PASS, skipped answer and finished(attempts=0), even if
  no call-start/return/proposal evidence exists. Completion accounting only checked
  the aggregate attempt value, not one successful call per accepted turn.
- A second capture for the same tuple overwrites the first. A none capture judged
  PASS followed by an unjudged local_draft capture could justify a skip using the
  unjudged replacement action.

Minimum correction within the already-adopted SWE accounting contract: reject
duplicate captures, bind judgments to the preceding captured value, and verify a
unique successful call sequence for every accepted tuple in newly planned runs.
No product behavior, semantic oracle, historical result or provider budget changes.
The original226-test suite passed but did not exercise these malformed histories;
do not treat that green suite as proof the findings were absent.

Implementation path/budget/conditional-answer checks had no other substantiated
blocker in this review. This is review evidence, not actual model qualification.

Focused re-review after repair: both findings cleared, no remaining substantiated
blocker. New malformed-history tests retain the red reproductions;32 focused tests
PASS3.028s and full228 PASS21.995s. Completed newly planned runs require one ordered
hash-bound successful lifecycle per accepted tuple, unique call sequence, no discarded
return and no extra/unplanned lifecycle. Duplicate captures are rejected; skip reads
the captured value bound at the prior PASS. No actual regression call occurred yet.
