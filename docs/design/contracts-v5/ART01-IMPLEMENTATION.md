# ART01-store/1 and adopted inspect — native implementation

Author workspace: `/private/tmp/pal-art-native-20261009`, branch
`codex/pal-art-native`, exact prerequisite
`90bcfd369c57e6ad3fea7b0d0b2953670f49358d`. Implements the adopted ART01-SCOPE
and ART01-BINDING callback under D038/C073's explicit native route clarification.
The unknown CO task and its workspace/state remain untouched.

`ArtifactStore` owns only `v5_art_body` and `v5_art_replay`. The caller supplies
an idle autocommit SQLite connection and trusted read-only TSK/MEM callbacks.
Saving validates closed input and exact bounded UTF-8 content before a short
`BEGIN IMMEDIATE`; original canonical input replay precedes current authority.
The TSK callback supplies the complete conservative actual-call record union.
The MEM gate rechecks those dependencies in that same transaction. Immutable
bytes, byte metadata, WorkRef/Step binding, source union, canonical input and
original receipt commit together. A unique Step prevents a second save identity.

Readback verifies exact bytes through `check_bytes`, supported media/UTF-8,
strict metadata, a canonical saved binding and the corresponding receipt/input.
The binding checks detect independent metadata/provenance changes; they are not
a cryptographic defense against a party able to rewrite every SQLite row.
Read owns a short read transaction; inspect participates in the caller's active
same connection without BEGIN/COMMIT/ROLLBACK. Inspect returns the adopted six
fields. Both recheck current source availability. Denied dependencies block
model/verification and inspect, while user history remains with `usable:false`.
Missing/corrupt dependencies or bindings fail unavailable. Historical receipt
recovery returns three receipt fields and never grants body-use authority.

Trusted callback guards use savepoints, active transaction checks and unchanged
`total_changes`. They detect mutation and ended/replaced transactions. They are
not a sandbox: a collaborator which commits can persist its own changes, which
ART cannot claim to have rolled back. Normal ART failures roll back owned
transactions; BaseException rolls back owned save/read transactions and propagates.
Inspect propagates interruption with transaction ownership retained by its caller.

## Author verification

Exact focused command:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_artifacts_v5.py -v
```

17 tests PASS, 0.030s, exit0. Explicitly synthetic callback doubles cover exact
empty/Unicode/CRLF/1MiB content, invalid UTF-8 and oversized input, strict shape/
integer types, canonical object and array identity, replay after stop, Step/key
conflicts, complete provenance, source/authority failures, ID collision, atomic
post-insert faults, KeyboardInterrupt/SystemExit, caller ownership, readonly
inspect/read, independent metadata/body/provenance corruption, callback mutations
and premature commits, temporary-file reopen and competing writer lock.

Full suite also attempted with the same interpreter and `-m unittest discover
-s tests -v`: 558 tests, 11.071s, exit1, 29 errors and 3 failures. All 29 errors
report sandbox `PermissionError [Errno 1] Operation not permitted` during existing
HTTP/probe socket setup; three cancel-probe subprocess tests did not reach
`CHILD_HELD`. This run included the first 15 ART tests, all passing. Two further
ART-only tests subsequently passed in the final focused17. Full acceptance is
not claimed. Full log: `/private/tmp/pal-art-native-full-tests.log` (author staging).
`git diff --check` passes.

## Limits and next owner evidence

Actual MEM/TSK/ART consumer integration is not author-tested here. Root owns
execution of the pending actual connection test, final integrated full regression
and independent Astra review. Test doubles do not establish that connection.
No TSK/Goal state, current artifact set, VER, completion, recovery, model re-input,
provider, UI, live database, auth/cost/runtime or external publication is changed.
Only this note, `pal/artifacts_v5.py` and `tests/test_artifacts_v5.py` are owned.

## Independent-review correction at the same adopted scope

Independent Astra reviewed author commit `1afcfbe` and requested REFINE. Root
confirmed the shared C08 wire: content exceeding 1MiB returns `limit`, and
`ComposeAction` preserves duplicate valid Ref entries. The original ART boundary
incorrectly collapsed all content preparation errors to `invalid_input`, and its
generic Ref parser imposed an extra uniqueness constraint. The first author tests
repeated those assumptions instead of comparing the shared producer contract.
Neither behavior was an adopted restriction.

Corrections preserve `ArtifactContentError.code` (including `limit`) and accept
ordered duplicate input Refs as canonical save identity. Set membership still
checks dependency coverage; callback-provided provenance remains authoritative.
A duplicate-input replay succeeds, while changing the same key to an otherwise
identical deduplicated array conflicts. A regression creates the actual shared
`parse_model_action` ComposeAction and passes its preserved input directly to ART.

The review also found that an inspect gate exception retained ART's callback
savepoint inside the caller's transaction. Cleanup now rolls back to/releases
that owned savepoint on Exception or BaseException, preserving earlier caller
writes and its outer savepoint/transaction. Interrupted inspect still propagates.
If a callback committed/replaced the transaction, missing-savepoint cleanup cannot
undo it and is explicitly not claimed to do so.

Three new public regressions were first run against the original implementation:
20 tests, three expected failures, 0.035s. After the correction: focused20 PASS,
0.033s, exit0 with the focused command above. Red/green staging logs:
`/private/tmp/pal-art-native-review-red.log` and
`/private/tmp/pal-art-native-review-green.log`. No full-suite rerun or additional
source ownership. Previous full author limitation remains as recorded above.

Prevention/next check: for related wire changes, compare failure codes and accepted
collections with the actual shared producer before choosing stricter validation;
retain the size-code and shared Compose duplicate-input regressions. For trusted
active-transaction callbacks, verify owned-savepoint cleanup and caller-write
preservation on both ordinary failure and interruption. Independent rereview and
Root's actual consumer/full integration are still required; this author correction
does not substitute for either.
