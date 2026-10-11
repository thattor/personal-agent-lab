# COMPLETE01/1 RUN — MockRunner host finalization

Owner: RUN host slice only (`pal/mock_runner_v5.py`). TSK `complete` authority,
VER storage and real SQLite integration remain separate owners; no canonical
records, schema or protected files changed.

## Diff summary

- `MockRunner(..., artifacts=..., verifications=...)`: `verifications` without
  `artifacts` raises `ValueError`; `verifications=None` keeps the bounded
  draft-only behavior unchanged.
- `finalize` seam: `get_work` `current_artifact_refs` -> canonical
  `C09.verify` key -> strict receipt validation (verification-kind ref, nonempty
  checks with exact keys/status) -> canonical `C10.complete` control. Runs after
  each finished compose and at entry — after the existing started-Step and
  next-call readiness checks — when the last finished Step is compose and its
  artifact is the current set tail.
- Outcomes: all-MET plus valid C10 -> completed result (status, state,
  control_status, work_ref, lease_id, verification receipt, steps, call_ids,
  excluded diagnostics) with no release; non-MET and C10 conflict/stale/denied
  resume the bounded loop; persistent verify unavailable -> yield_or_retain;
  persistent/ambiguous C10 unavailable and malformed receipts fail closed
  without release or inference repair. Exactly three identical bounded retries.
- Release results carry the last verification receipt; no verify Step is
  fabricated and verification refs never enter model context or Step results.

## Test result

Isolated acceptance (independently authored, immutable):
`python3.13 -I -S -B -m unittest discover -s tests -p test_mock_completion_v5.py -v`
— executed by the coordinator's sandboxed verifier; 16 tests.

## Limits

CO verified covers only this verifier command — never whole-product completion.
Excluded: model verify Action, semantic evaluation, provider/EXE/UI, restart
recovery, external effects, auth/cost changes, production persistence, and old
unknown-call retries.

## Root integration correction after the CO result

The original CO result39213ad4 passed its immutable16 protocol fixtures. Actual
SQLite consumers then failed8 methods/10 cases: RUN passed `{work_ref}` to C02,
whose public request is `{goal_id,revision?}`. The fixture ignored the request,
and the dispatch supplied the slice text without the full C02 provider contract.
Root corrected the call and preserved that original failure log and CO hashes.

Independent Sol review9f31ba9 also reproduced unknown VER errors causing a terminal
failure, and loss of previous finished-step diagnostics at retained-lease reentry.
Root now treats unknown/malformed local owner replies as unavailable without new
inference or a terminal failure, validates fixed check IDs/status/evidence and
strict WorkRefs, and reports saved Steps plus actually observed current-lease calls.
Six added integrity methods failed19 subcases with2 errors before repair; the
original16 plus actual8 and integrity6 now pass30 locally. This is not an
independent approval or full regression; those remain separate source-bound gates.

Prevention: include exact public request/response examples for each new consumer
edge in future CO inputs, retain independent real-owner connection tests, and
exercise unexpected owner outcomes independently of the happy-path fixture.
