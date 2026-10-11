# RECOVERY02 ART fixed acceptance

Base `b0b02998a8db2548bafb3ca4feb5c70565ad2d4e`; frozen RECOVERY02-SCOPE takes
precedence over proposal. Only this note and tests/test_artifact_recovery_v5.py
are authored. Source, contracts and existing tests remain unchanged.

Test module: 16 methods, 11851 UTF8 bytes.
SHA256 `65abe1f22bd54e752f697aac8f937a7d772b3a706f55e9b0f5a2a59d899f3077`.
Runtime dependencies: pal/artifacts_v5.py, contracts_v5.py,
artifact_content_v5.py, artifact_integrity_v5.py. No other TestCase imports.
Explicit root sys.path supports isolated discovery. All databases are fresh
:memory: SQLite. Actual ArtifactStore saves the original ComposeAction through
shared parse_model_action, including duplicate source refs. Trusted authorizer
and source-gate fixtures assert connection/request/tuple contracts; they model
ART protocol only, not TSK/managed-host/process provenance.

Coverage:
- Pure artifact_save_key exact canonical output and invalid identity rejection.
- Exact closed lookup and full conservative producer projection, original epoch,
  hash/length, no body/authorize/id/clock or durable changes.
- Genuine absent key/body versus body without key, dangling receipt and foreign
  body Step/WorkRef. Found mismatched canonical input is conflict.
- Content/media/ordered/duplicate source identity, including legal empty action
  source list differing from saved input. Empty sources are not invented as bad
  ComposeAction input; the stored full producer list remains nonempty.
- Strict shapes/types/UTF8; wrong/idle/non-autocommit connection preconditions.
- Bytes/hash/length/UTF8/media/metadata/replay projection corruption.
- Denied versus missing/unavailable/malformed/throwing gate; SQLite read fault.
- Caller-owned transaction and writes retained. Mutating gate returns unavailable
  with only owned savepoint rollback; total_changes need not decrease after
  rollback, so that fault checks durable dump rather than false zero-change proof.
- Hostile COMMIT returns unavailable but committed caller data remains; no false
  rollback claim. KeyboardInterrupt/SystemExit propagate with callback savepoint
  removed and caller savepoint/transaction intact.

Validation command:
`/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_artifact_recovery_v5.py -v`
Observed baseline: 16 methods, one existing helper PASS, 33 errors (subtests), all
AttributeError for absent lookup_saved. Save fixtures succeed. No fixture error is
counted as feature RED. Log `/private/tmp/pal-recovery02-art-fixed-red.log`.
AST parse and git diff --check PASS. Callback behavior/corruption assertions beyond
first missing method remain unexecuted until separate source implementation.
No skips/stubs/source substitute. SWE must preserve this fixed file, run it and
existing ART tests; separate context reviews exact source. Root owns actual
TSK/ART/VER/RUN/host connection, file SQLite/restart/process proof, shared identity
integration and final adoption. No C13/Primary/provider/product acceptance.
