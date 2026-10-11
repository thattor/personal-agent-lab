# ASK01/1 RUN acceptance fixtures

Frozen against base `7ee3ed435026f17ec42ffd58f4e042f031073dcd` and
ASK01-SCOPE.md sections 5–6, including C076. Independent native Sol test author;
RUN implementation is assigned to a different AGY Sonnet context. This file and
`tests/test_mock_ask_v5.py` are the complete test-author change.

The public-owner doubles extend the existing synthetic completion fixture. They
close its unused in-memory SQLite connection immediately; no actual TSK/MEM/ART/
VER persistence runs. C04 requests are closed shapes. Public get_call responses
include call/lease/index/current WorkRef and Step linkage. Historical finished ask
Steps deliberately retain older epochs while current returned-call binding remains
strict. Test assertions specify observable requests, disposition, budgets and model
inputs rather than an implementation algorithm.

The 15 methods cover:

- Exact persisted ask action, canonical C04 key, duplicate selected refs preserved,
  waiting diagnostics, no generic finish or release after valid commit.
- Three identical unavailable attempts followed by one key lookup; second-attempt
  success; unresolved commit retains started Step with yield fencing and no repair
  inference or extra reservation.
- Closed waiting receipts and safe authority refusal, unexpected error and callback
  exception dispositions; none authorizes failed release.
- Retained ask public get_call recheck at the tail index without fresh inference;
  missing/unended/foreign/bool-index/current-epoch mismatches do not call ask.
- Multiple historical question/answer links passed exactly in additive C12 only
  while both answer body and ask Step provenance are eligible. Selective answer or
  question-source exclusion preserves all links in local diagnostics; unrelated
  optional exclusions do not suppress links. Empty eligible sets omit C12's field.
- Corrupt links are refused before reservation/inference; transient answer read
  failure is not treated as deliberate source exclusion.
- C076 verify conflict/stale/denied followed by latest paused execution authority
  never terminalizes work or makes a second inference.

Run command:

```sh
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_mock_ask_v5.py -v
```

The frozen baseline is expected RED: ask currently falls through generic finish,
claim linkage is omitted, retained started Steps are rejected, and VER authority
refusals use failed release. Syntax and whitespace checks are separate from this
behavioral RED. Failures involving missing output fields are expected acceptance
failures, not evidence that the future implementation passed.

Dependencies and limits: `test_mock_completion_v5.SyntheticOwners` and its `value`
helper are existing fixed fixtures. Their basic claim/reservation/read/compose seams
remain in use, with ASK-specific call, provenance and persistence behavior overridden
here. An implementation author may not weaken these acceptance fixtures. Actual
same-transaction ask/answer/control/source-stop behavior, schema, real temporary
SQLite composition, immutable question replay after later controls, cumulative
budgets across new claims, READ01 demo and full regression belong to Root/TSK and
remain NOT_RUN by this test-author change. These doubles are not live/provider,
restart adoption, semantic-answer sufficiency or whole-product acceptance.
