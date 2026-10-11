# PRI01-MEM independent fixed acceptance

Frozen scope/base: `65bb8bb251f9cae197c4533c9e26fd218026b1fb`.
Only the new test module and this note are authored here. No implementation,
Primary, recovery, provider, old/live DB or service changes.

`tests/test_memory_primary_v5.py`: 13 methods, 10652 UTF8 bytes.
SHA256: `a994265b0f433fda4fd491de4d5464d345436efe27d494a4a3d0a9b01139b38c`.

## Fixture and dependencies

Standalone isolated discovery inserts the repository root explicitly. No other
TestCase imports or test-file dependencies. Runtime inputs are
pal/memory_v5.py, pal/intake_v5.py, pal/contracts_v5.py and pal/sanitize.py.
Actual fresh in-memory MemoryStore and IntakeStore share the same autocommit
connection. Intake source_gate delegates to actual MemoryStore.source_gate;
events/invalidation delegate to actual Intake methods. Wrappers count callbacks,
never invent source availability. IDs/time are deterministic host fixtures.
No dependent work is created: the tested stop acknowledgement has actual event
and empty affected-work invalidation. Root owns later dependent-work integration.

## Fixed matrix

- Empty, exact metadata projection; newest durable order across both roles;
  same-session selection, stopped rows excluded before limit, 50 bound and exact
  truncated flag. No content projection or literal search fallback.
- Closed request types/UTF8/nonempty identifiers and strict integer limit,
  including bool, missing/extra fields and invalid range.
- Original stop receipt after later activity and fresh MemoryStore/IntakeStore
  reconstruction from in-memory SQLite backup; stopped C11 model use remains denied.
- Missing stop key versus append-only namespace; malformed canonical input,
  original initiating session, stored key mismatch, malformed receipt, wrong Ref
  kind/record/result binding, missing source row and SQLite table fault.
- SELECT reads preserve total_changes, complete durable dump, callback counts,
  and caller transaction. Traces reject transaction commands/writes. A caller's
  uncommitted usable change remains visible and rolls back normally.
- Injected SELECT KeyboardInterrupt propagates without closing caller transaction.
  No fake mutation/rollback proof: ordinary reads own no write or transaction.

Corruption probes target existing MEM-owned schema (not a proposed new schema).
Stored-body absence is tested; no new requirement to rehash a body for a metadata
lookup is invented beyond the frozen scope. SQLite fault probes and backup are
metadata-unit evidence, not filesystem/process-restart proof.

## Baseline validation

Command:
`/opt/homebrew/bin/python3.13 -I -S -B -m unittest discover -s tests -p test_memory_primary_v5.py -v`

Observed: 13 methods, 24 errors, all AttributeError for absent list_recent or
get_stop_reference_by_key. Subtest errors account for the higher error count.
Fixture append/stop construction succeeds; no fixture error counts as feature RED.
Log: `/private/tmp/pal-pri01-mem-fixed-red.log` (local, not committed).
AST parse and git diff --check PASS. No feature behavior PASS is claimed; many
assertions remain unreachable until implementation. No skip/stub implementation.
SWE must run unchanged tests plus existing MEM tests; a separate context reviews
source. Root owns file restart, actual Primary/dependent-work/full integration and
usefulness proof. Overall PRI01 is still unfrozen.
