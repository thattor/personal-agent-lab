# PRI01-MEM/1 — frozen read-only Primary prerequisites

SOL adopts only these two additive MEM methods after exact PRI01 Opus5.5 REFINE
consultation (F7/F10). Overall PRI01 remains unfrozen; this independent owner work
executes no Primary and needs no pending recovery code. Source base before this
addition: a699d78f9cbd30f143285c0a408842fa4cdc30a3. Assignment pins the commit
containing this scope. Python standard library only.

## Ownership

MEM owns pal/memory_v5.py. A separate context owns fixed
tests/test_memory_primary_v5.py. SOL owns shared scope, integration and final proof;
a separate source context reviews the implementation. Read current MEM01-SCOPE,
C05/C06/C11, memory_v5, contracts_v5, intake_v5 and sanitizer as needed. Existing
append/stop/read/search semantics and schema stay unchanged. No TSK/PRI/ART/RUN,
services, old/live DB, provider, authentication, cost or CO runtime/state changes.
Return exact diff/commit/source hash, fixed/related tests and remaining limits.

## Exact methods

`list_recent({session_id,limit}) -> Result[{record_refs:[Ref],truncated:bool}]`.
Closed request; session nonempty UTF8 str; limit strict int1..50 (bool invalid).
Select currently usable same-session raw records, newest durable seq first;
fetch limit+1 so stopped rows cannot displace older eligible rows. No role filter:
these are existing MEM raw records, not new PRI reply records. No body/summary,
derived memory, literal-query trick, cross-session search or model selection.
Empty result succeeds with empty list/false. PRI separately reads each Ref through
C11 model_context and rechecks use before entry/adoption; metadata grants no body
use. One SELECT snapshot, no writes/transactions/callbacks. May read within a
caller transaction without changing its ownership.

`get_stop_reference_by_key({key}) -> Result[{affected_refs:[Ref]}]`.
Closed nonempty UTF8 key; return original successful C05.stop_reference replay
unchanged after source-stop or later dependent work changes. Missing key is
not_found. Malformed canonical input/receipt, wrong stored key/command binding,
invalid Ref, missing source body or result inconsistent with its original stopped
record is unavailable. Stored input includes its original initiating session;
validate it, do not replace it with current config/caller session. MEM01 receipts
contain exactly the one original record Ref in affected_refs. The current record
may be stopped and is not regated. No stop application, invalidation, event,
source-gate, sanitizer, replay write, error persistence or transaction start/end.
Lookup repeats equal receipt; new use still requires ordinary owner/source checks.

Bad public input returns bounded invalid_input; SQLite/corrupt stored data returns
unavailable. Diagnostics contain no raw exception/path/body/SQL. Preserve caller
transaction on every read path. BaseException propagates; no owned write exists.

## Fixed acceptance before source

Use actual fresh MEM and intake/event/source-gate collaborators, including active
caller transactions. In-memory SQLite qualifies this metadata unit; managed file
restart is separate later evidence. Require newest order, strict bounds/extras/UTF8,
stopped/other-session filtering, exact truncation, no body leakage, no row/event/
replay mutation or callback invocation. Stop lookup equals original receipt after
later changes/reopen, never repeats invalidation/event. Missing/malformed input,
corrupt receipt, wrong key/source binding and missing body refuse unchanged.
Run unchanged fixed tests, affected existing MEM tests and independent exact-source
review. Full suite/actual Primary connection and whole usefulness remain pending;
unit green closes no PRI/recovery/product acceptance.
