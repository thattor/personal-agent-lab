# Task G milestone review — co-update-045 batch 2

## Scope and evidence
Exact supplied source: five pure modules, their tests, the pipeline test, PARALLEL-SCOPE-2 and contracts v5 C07–C09. Root evidence (`verification.json`, `three-way-proof.json`):
- Root full suite: 399 PASS (22.153s).
- Targeted: 122 PASS (18+27+22+28+21+6); the sandbox verifier re-runs only this `test_*v5*.py` subset.
- The SOL corrections are present in the tests: E subclass/hostile code, D t22 size precedence, and F invalid-input results.
- Source hashes were already confirmed by SOL; not a new gate.
- Eight three-task segments totalled ≈262.7s (2026-10-08 22:30:44.988–22:35:12.691 UTC). Local admission-to-cleanup intervals, not remote compute or vendor capacity.

## Module contract findings
- D `github_file_payload_v5.py`:
  - Exact-int bound and exact bytes payload, with raw length checked first (:87-94).
  - Strict JSON rejects duplicates, NaN/Infinity/`1e400` and deep nesting (:105-121).
  - Field and forbidden-field checks (:126-151).
  - Declared size gives `limit` before Base64 parsing (:153).
  - Canonical Base64: CR/LF-only stripping, `validate=True`, re-encode equality (:156-171).
  - Decoded bound, size equality and strict UTF-8 with no normalization (:173-185).
- E `bounded_payload_v5.py`: the corrected constructor checks `type(code) is str` before comparing and sets only `args=(message,)` (:27-36). The bound is checked before mutation (:57-59).
- F `artifact_integrity_v5.py`: order is sha, count, data, limit, length, hash. Over-limit or wrong-length bodies are never hashed (:57-70).
- Pinned repository, 40-hex ref, 30s, 1048576 and codes `invalid_input`/`denied`/`limit` fit C07/C08 and the Result vocabulary. `met`/`unmet`/`unknown` fits C09.

## Synthetic connection
`preview` (`tests/test_v5_read_content_pipeline.py:25-31`) chains prepare_read → PayloadBuffer → decode_file → prepare_content → check_bytes. It also covers tampering, size mismatch, overflow and denied-repository failures.

Gaps:
- `blob_sha` (`"b"*40`) is unrelated to ref `"a"*40`, and nothing binds the response to a commit.
- Expected integrity metadata is derived inside the test.
- Transport is an in-memory Mock/lambda with no timeout or cleanup.
- No issue-response decoder is supplied.

## Practical read/storage contribution
A deterministic, bounded read→content→integrity byte path that EXE02, ART01 and VER01 can wrap. It stores nothing and issues no Ref, receipt or Operation.

## Blocking findings
None.

## Optional hardening
- `FilePayloadError` (`pal/github_file_payload_v5.py:43-47`) and `ReadRequestError` (`pal/github_read_request_v5.py:51-54`) accept any code or message. Only constants are passed today.
- `ArtifactContentError` (`pal/artifact_content_v5.py:33-39`) uses `args=(code,message)` and a custom `__str__`. INT00 Result mapping should normalize the shapes.
- GitHub's large-file `encoding:"none"` gives `invalid_input` (`pal/github_file_payload_v5.py:130-132`), not `limit`. The executor must handle this case explicitly.
- One `max_bytes` value bounds both the raw JSON and the decoded body. With Base64 and escaped line wraps, decoded text is capped near 760 kB, below C07's 1MiB. The scope acknowledges this; EXE01/02 must decide on it deliberately.

## Not established
Commit provenance, canonical metadata, service CT/E2E, real GitHub reads, persisted artifacts/receipts, Goal flow and human value. `product_service_and_human_value` stays UNMET ("UNMET / NOT_RUN").

## Next dependency
INT00 WorkRef/Ref/Action/Result common wire types, needed to wrap these values and errors. Operation (C07 prepare/execute/get, receipt, provenance) belongs to EXE01 after INT00. No approval gate or added task.
