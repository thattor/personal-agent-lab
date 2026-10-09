# Independent pre-implementation analysis

Base: 666506a438e3bd1a793255875b6acf3ecd8b7989. Both agents read only the current
v5 contract/intake scope and source. Neither changed files or ran tests/external calls.
This is design evidence, not implementation or independent code approval.

Native gpt-6-astra (`/root/int00_astra`) proposed record append/stop/read/search and
a read-only same-connection gate. MEM owns its mutation transaction; TSK owns intake
and the event ledger. The private event writer is not a public idempotent C14 seam.
Require a host sanitizer, host session for memory notifications, exact Ref-kind
routing and no nested standalone transactions. Reference-stop may retain history
but cannot be labelled full C05 without TSK invalidation and derived-note handling.

Independent gpt-6.1-sol (`/root/int00_sol_review`) separately identified immutable
Ref versions, trusted read purpose, record-only retrieval bounds, unsupported owner
closure and old receipt/current authority separation. Its acceptance cases cover
durable exact Unicode/empty append, key conflict, type aliases, stop rollback,
real MEM-to-intake connection, both serialized two-connection orders, old receipt
replay, stopped-candidate exclusion, current-read checks and bounded strict errors.

Both analyses find: future-intake denial alone does not invalidate existing queued
or running work. Deferral is valid only for explicitly unused preparation and is
an execution-activation blocker. SOL's draft now asks whether the first connection
should also implement queued-work invalidation through a TSK-owned public seam.
That question needs a technical design disposition; no owner policy question follows.

Source anchors: PAL-contracts-v5.md lines42,51,81–91,122–125,140–151,211–212;
pal/intake_v5.py lines149–176,208–238,240–283. Shared examples currently lack a
concrete MEM stop/retention case; add the chosen expectation before implementation.
