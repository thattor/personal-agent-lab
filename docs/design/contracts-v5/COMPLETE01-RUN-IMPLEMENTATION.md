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
