# ART01-bind/1 TSK consumer implementation

Native Astra author work against base a47c6009f810cd86380859c8418d8a05f58c14e3,
under frozen ART01-BINDING.md and the R1–R9 SWE consultation dispositions. This is
not CO-generated ART code. The unknown storage task was not read, retried or
reimplemented. ART, RUN, MEM, intake and common contracts are unchanged here.

TaskStore accepts optional `artifact_inspect`. A non-callable non-None value is a
configuration error. Absent inspection support makes compose begin unavailable
before any step reservation or write. Existing save-hook tests supply an unused
readonly inspector stub; that configuration is not storage integration.

The consumer invokes exactly `artifact_inspect(connection, {'ref': artifact_ref})`
on its active finish transaction. It requires an immutable shared Result carrying
exactly artifact_ref/work_ref/step_id/hash/bytes/source_refs, validates metadata,
and uses a savepoint, active-transaction check and total_changes guard. Successful
metadata requires a matching artifact Ref, strict WorkRef, nonempty step ID,
lowercase 64-character hash, exact int byte count in 0..1048576, and nonempty
record-only dependencies. Failed Result codes are retained with bounded messages
and empty refs. No collaborator text/body/exception is echoed. Guard failures
roll back normally; an arbitrary trusted callback that commits its caller's
transaction cannot have that commit retroactively undone. Tests distinguish
transaction-control detection from a sandbox or rollback guarantee.

Compose finish requires exactly one artifact result, no error field and no lookup
truncation/exclusions. It reuses the existing save authorizer to check exact stored
compose action, current work/lease/control, started Step, returned call and call.step
binding. Inspect WorkRef mismatch is stale, step mismatch conflict, Ref/provenance
mismatch unavailable; absent draft is not_found. Dependency equality is by set
against every actual supplied record, including model-unselected sources. Source
usability is rechecked after inspection, without parsing body text or reading ART SQL.

One finish transaction writes the finished C13 Step, an ordered TSK-owned set row,
record dependency registration, a progress event carrying the artifact Ref, and
finish replay. `v5_tsk_artifact_set` has seq INTEGER PRIMARY KEY and goal/revision/
artifact_id/step_id, with unique artifact and step bindings within each revision.
Distinct compose steps append; they never replace older bytes or refs. Failed
writes, exceptions and process interruptions roll back all owned writes.

TaskStore.get_work preserves the existing closed C02 envelope and projects the
validated ordered set; earlier work without rows returns []. Corrupt IDs or set/
Step bindings fail unavailable. get_execution_context permits an unregistered
artifact only as the set-bound result of its finished compose Step. All call input
records must remain registered. The artifact stays in step_sources, keeping that
compose Step excluded by RUN's existing actual-C11-context filter. Artifact refs
are never registered as model inputs. Brief/lookup/register artifact re-input
remains closed until a future explicit owner-kind/dependency design is adopted.

Replay still precedes current authority: a committed finish can be redelivered
after pause/release without another set row, event or reservation. An uncommitted
finish cannot newly attach after pause/abandonment. Receipt recovery is not new
execution authority. No VER rows, verification invalidation or completion path
exist in this slice.

## Author verification

Command:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p 'test_task*v5.py' -v
```

Result: **50 tests PASS**, 0.304 seconds, retained at
`/private/tmp/pal-art-bind-tsk-final.log`: 36 TaskStore tests plus 14 dedicated
binding consumer tests. Tests use actual TaskStore temporary SQLite files and an
explicit readonly inspection contract double. They cover append/reopen/C02,
later report readiness, replay after control/release, exact input shapes, malformed
inspect metadata, full provenance equality, source recheck, wrong step/work/call/
lease, stopped source, callback mutation/exception/transaction end, current-set
corruption, arbitrary artifact provenance, forbidden re-input, and rollback after
step/set/dependency/event/replay writes including KeyboardInterrupt/SystemExit.

Initial `/private/tmp/pal-art-bind-tsk-initial.log` retained two failures. One old
store-stage test still expected unavailable for empty compose finish, now explicitly
invalid_input in the adopted binding scope. The new test reused a permissive
synthetic source gate that looked up artifact IDs as records, producing not_found
instead of the real MEM record-only unavailable outcome. Tests now explicitly
model that owner contract; no production rule was weakened. The next-use condition
is to check the actual owner kind policy when reusing a test gate. Corrected
intermediate evidence is `/private/tmp/pal-art-bind-tsk-after.log`.

NOT_RUN here: actual ART storage/inspect integration, RUN compose/save/get_by_key
response-loss flow, connected MEM source-stop races, full repository regression,
independent review, VER/complete, restart recovery, provider/UI/product activation
or usefulness acceptance. Root owns integration and those dependent checks. These
consumer-double results do not resolve the unknown ART implementation outcome.
