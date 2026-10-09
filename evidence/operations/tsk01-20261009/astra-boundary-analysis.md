# Independent pre-code boundary analysis

Native gpt-6-astra, separate context from AGY implementation author; baseline
d8e4465df049b2fae411b19e04990a08928aaa9c. No files changed/tests run/code verdict.

No blocking semantic contradiction in TSK01/1. SOL adopts these acceptance checks:

- Replay must compare original request_scope before grant intersection/deduplication.
  Distinct requests yielding the same Grant still conflict; changed current host
  ceiling/expert/gate cannot rewrite an equal-input stored result.
- Observe same connection, active BEGIN IMMEDIATE and gate-before-intake-write ordering.
  A stopped-source example alone does not prove transaction ordering. Gate commit and
  rollback must produce unavailable without intake effects.
- On an already nonempty DB, an event-stage abort must preserve earlier successful work,
  leave no new work/event/replay rows, end the transaction, and allow repaired retry.
- get_work follows exact C02 fields, omits expert_id, selects revision1 when revision
  is omitted, and returns not_found only for a nonexistent requested version.
- Probe duplicate condition/event/goal IDs from host injection, invalid gate results,
  and sentinel-bearing factory exceptions for atomic rejection and bounded errors.

Root disposition: consistent with fixed scope; no new owner decision, schema feature
or product authority. Test missing cases after the exact authored diff is available.
