# Milestone review: PARALLEL-SCOPE-1 §C (co-update-045)

## Scope
Independent read-only assessment from the supplied snapshot: final helpers/tests, product.diff, verification.json, targeted-after.log, integration-check.json, parallel-intervals.json, SPEC, contracts v5, freeze script/tests. Nothing changed or activated.

## Helper consistency
- **EXE02-request/1** (`pal/github_read_request_v5.py`): pure; imports only `dataclasses` and `quote` (:16-17). Capability allowlist (:109); exact dict/key set (:116-121); foreign repository denied (:126-127); strict int issue number ≥1, ≤63 bits (:131); path rejects empty/dot/dotdot segments, backslash, C0/DEL, surrogates (:71-86); lowercase 40-hex ref (:89-94); segment quoting (:141-144); bounds 1..30 s, 1..1048576 bytes (:146-153); fixed 7-element argv (:155). Matches C07 initial limits and Result codes; fixed messages (:30-40). Residual: direct `ReadRequest(...)` is unvalidated (:57-63); EXE01 must accept only `prepare_read` output.
- **ART01-content/1** (`pal/artifact_content_v5.py`): strict str/media checks (:59-66); encode error raised outside the handler, nothing chained (:67-73); inclusive 1048576-byte limit (:74-75); sha256/byte_count over exact bytes (:80-81); frozen slotted value, content/data hidden from repr (:42-50). No Ref, ID, source check or DB; consistent with C08.
- Contribution: both are reusable, tested boundaries for INT-02/C08 that add no running capability.

## Strict-key correction
`any(type(key) is not str …)` (`pal/github_read_request_v5.py:118`) closes a gap where a str subclass equal to `repository` passed set equality (:119). Test: `tests/test_github_read_request_v5.py:192`. The pre-fix failing log is cited in verification.json, not supplied; treated as linked evidence.

## Freeze gate
product.diff has no `scripts/primary_qualification.py` hunk; verification.json records `production_freeze_validator_changed=false`. `validate_freeze` (`scripts/primary_qualification.py:146-165`) still fails closed on file-set mismatch, malformed hash, missing/mismatched identity, content drift and unreadable manifest. `tests/test_primary_qualification.py:829-838` hash-checks the historical trial manifest (`baa73183…` = `old_trial_freeze_sha256`), reads it only as history and asserts the current validator rejects it. Later freeze-bound runs need a fresh freeze; this follows from the existing gate, not a new gate.

## C08 hash/bytes preview
Helper `sha256`→C08 `hash`, `byte_count`→`bytes`. integration-check.json records hash, 40 bytes, text/markdown, 0 real provider calls and 0 saved artifacts/receipts/completions. Mock text not supplied, so the hash was not recomputed. Bare vs prefixed stored `hash` is ART01's decision.

## Parallel-call evidence
Tasks 2363ba… (A) and b0fd78… (B): five overlaps, 9.5–96.2 s, recomputed from timestamps; maximum 2 concurrent. These are local admission-to-cleanup intervals, not remote compute proof.

## Tests
- 39 CO component tests PASS (21 request, 18 content; targeted-after.log).
- Root full 316 host result (`host_full_exit` 0) is linked evidence, not rerun here.
- Host verification shows the five `final_source_hashes` match the reviewed workspace; `component_base` differs from this BASE but is not a gate.
- CT, E2E, real provider: NOT_RUN.

## Blockers
none

## Optional hardening (not gates)
Length check before encoding very large content; executor note that the issues endpoint also returns pull requests; task IDs in overlap entries; assert the freeze rejection reason.

## Smallest next dependency
Resolve the unresolved INT00/1 task's shared WorkRef/Ref/Action/Result types. After INT00, EXE01 prepare/execute with its Operation ledger can consume ReadRequest (INT-02, CT-04/05/14), and ART01 save can consume ArtifactContent. No substitute types are created here.

## Verdict
- Preparation slice: MET.
- PAL completion, service wiring and user value: UNMET. No approvals or capabilities added.
