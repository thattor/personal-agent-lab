# COMPLETE01/1 TSK owner implementation

This isolated native implementation consumes the adopted COMPLETE01-SCOPE and
Opus/SWE dispositions. It changes only TaskStore and its focused owner tests;
VER, ART, MEM, RUN and canonical records remain separately owned.

TaskStore accepts optional verification_inspect, validated as callable at
construction. The existing control API accepts the closed complete command from
the scope. Canonical control replay precedes current authority and collaborator
availability. New completion uses exact WorkRef authority, then a same-connection
readonly VER inspection. Its savepoint is rolled back and released on all failure
paths, including BaseException. Trusted callbacks are not sandboxed: a callback's
COMMIT cannot be retroactively undone.

The typed result is closed and reparsed, with record-only dependencies and
artifact-only ordered results. Check reasons are UTF-8 JSON strings bounded to
1024 characters; evidence must belong to the inspected artifact/dependency set.
Condition IDs must match fixed stored Conditions exactly and in order. Different
Goal/revision is conflict; epoch/set changes are stale. Required refs must be
included and every dependency registered; the MEM gate is repeated before accepting
valid/MET. Invalidated with matching TSK truth and usable sources is unavailable.
Callback errors are bounded and sanitized; missing verification stays not_found.

Calls must have recognized statuses and be ended; returned calls require their
own finished Step with matching call/index/WorkRef binding. Started Steps and
unadopted output prevent completion. TSK atomically stores completed, closes the
lease, clears flags, emits one result event with ordered artifacts plus verification
Ref, and saves replay. Epoch and budgets do not change.

Completed source-stop notices preserve state/epoch/flags/set, including max epoch.
They use the frozen historical progress text, the work's session and only its
intersected stopped refs. Completed works are omitted from work_refs, which remains
actual epoch invalidations only. Existing cancelled/failed handling is unchanged.
Release preserves terminal states and still requires an active matching lease and
ended calls; a release after complete is denied because the lease is inactive.

## Evidence and limits

Python: /opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests
with each -p pattern and -v:

- test_task_completion_v5.py: 17 PASS; /private/tmp/pal-complete-tsk-focused-final.log.
- test_task_artifact_binding_v5.py: 16 PASS; /private/tmp/pal-complete-tsk-binding.log.
- test_verification_context_v5.py: 8 PASS; /private/tmp/pal-complete-tsk-context.log.
- Earlier test_task*.py run: 67 tests, 66 pass and one superseded legacy assertion
  at tests/test_tasks_v5.py:551. It expects completed-source stop unavailable;
  COMPLETE01 explicitly requires success. That file is outside this owner's write
  scope. Root was notified for integration adaptation. Log:
  /private/tmp/pal-complete-tsk-regression.log. This is not a full regression PASS.

New tests use real temporary SQLite TSK persistence and explicit readonly ART/VER
contract doubles. They cover successful state/lease/event/budget/replay, closed
input, authority/error precedence, corruption, source gates, readiness, owned-write
rollback including KeyboardInterrupt/SystemExit, savepoint cleanup preserving an
outer transaction, two-connection pause ordering, completed max-epoch notices,
shared completed/running invalidation and notice rollback. Actual connected
MEM/ART/VER/RUN acceptance is Root-owned and NOT_RUN here. No independent review,
provider operation, semantic evaluation, model verify Action, restart recovery,
UI activation, user value or whole PAL completion is claimed.

Initial focused failure log retained at /private/tmp/pal-complete-tsk-initial.log.
Two test-fixture mistakes caused its error/failure: passing unsupported key to the
shared start helper, and expecting stale from an artifact subset whose unchanged
evidence referenced an absent artifact (already malformed). The fixture now uses
create then claim and makes the subset result structurally valid before testing
set comparison. Next boundary tests must isolate the intended precedence with a
valid earlier-layer fixture. No runtime criteria were weakened to pass these tests.
