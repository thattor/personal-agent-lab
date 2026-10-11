# Independent RECOVERY02 ART source review

Verdict: APPROVE for frozen RECOVERY02/1 ART callback only.
Reviewed returned CO SWE source SHA256:
`1e37f0ed0435f97c54166210b1ac2746ce52edb271482030ce646a3e388c3ef1`.
Isolated review base e2ba3e00244f8ba75b9444870bc3c6cd8f95e823.
Exact source copied as a review dependency; no source/test edits or CO writes.
Only this independent note is committed. Reviewer authored the prior fixed tests,
not the source. Static source inspection was performed beyond test results.

## Findings

No blocking defect found. The additive method enforces the exact supplied active
isolation_level=None connection before public parsing. Closed request and strict
ComposeAction.from_json reject other Actions/extras; prepare_content preserves
UTF8 bytes/media. Canonical C08 input is compared as a dumps string, retaining
source order and duplicates rather than reducing them to a set. The shared key
helper remains unchanged from Root's base.

Missing expected replay is definitive not_found only when the unique original
Step has no body. Existing body without that key is unavailable. A found different
canonical input conflicts before adoption. _saved_receipt binds receipt to replay
artifact_id and exact content hash/count; _loaded checks immutable bytes/UTF8/media,
metadata and exactly one matching original replay. Lookup separately compares
original WorkRef/Step and receipt projection, so dangling/foreign bodies refuse.
Only full conservative stored producer refs are gated and projected; no content,
authorize_save, id/clock, replay creation or owned write is added.

The existing _gate/_guard provides caller-owned savepoint and total_changes
checks. Writes roll back only callback savepoint; Exception becomes bounded
unavailable. BaseException propagates after owned cleanup. Callback COMMIT or
rollback/replacement destroys the savepoint and refuses; committed caller data
cannot be restored, and tests expressly retain that qualification. SQL faults
before gate own no savepoint/transaction and preserve caller state. No ordinary
BEGIN/COMMIT/ROLLBACK is added to lookup. Trusted callbacks remain a cooperation
contract, not protection against coordinated hostile local schema forgery.

## Independent execution

Unchanged fixed file SHA256:
`65abe1f22bd54e752f697aac8f937a7d772b3a706f55e9b0f5a2a59d899f3077`.

- `/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_artifact_recovery_v5.py -v`: 16 PASS, 0.018s.
- `/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_artifacts_v5.py -v`: 20 PASS, 0.037s.

Local logs: /private/tmp/pal-art-recovery-review-fixed.log and
/private/tmp/pal-art-recovery-review-existing.log. git diff --check PASS.
These are independent actual SQLite ART protocol results, distinct from CO's
reported fixed16 PASS. They do not establish TSK adoption/binding validation,
managed host/process restart, Root's connection4, full C13, Primary/provider or
product usefulness. Root integrates exact reviewed bytes and owns those next
checks; this approval does not accept the overall goal or unknown CO operations.
