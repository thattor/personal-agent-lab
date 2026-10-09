# RECOVERY01/1 — frozen managed mock startup and orphan settlement

SOL adopts this bounded scope after exact CO Claude Opus5.5 consultation
(REFINE, then adopt). Its F1–F11 are resolved below; original report is retained.
This is a useful first C13 dependency, not full recovery or product acceptance.
Normative owner source base before new code: `175cdc6db5d9948379335f638e957a6a29e16204`.
The CLI/assignment base includes this frozen scope; no old PAL source or DB.
Shared contracts v5 C02/C04/C08/C09/C10/C13/C14/C15 remain in force.

## Scope, owners and isolation

HOST owns `pal/mock_host_v5.py`; TSK owns `pal/tasks_v5.py`; RUN owns
`pal/mock_runner_v5.py`. SOL owns shared contracts, actual connection, canonical
records and integration. Separate contexts own immutable HOST and TSK tests.
ART/VER/MEM/intake/shared Python owners are unchanged. No migration of existing
live/old DB, providers, escaped threads, forked execution, subprocess callback,
external effect, EXE activation, PRI execution or semantic acceptance.

Only trusted synchronous in-process mock callbacks constructed by this host are
qualified. This is not a Python sandbox or behavior detector. A caller boolean,
PID, runner text, elapsed time or bare lock acquisition never qualifies arbitrary
execution. A legacy/in-memory store remains a local test seam; it cannot recover
or create interrupted. An earlier checkout ignoring enrollment is outside the
trusted operator/version guarantee; never run it against an enrolled candidate.

Read only assigned actual v5 owners, shared scope/examples and fixed tests.
Write only assigned module/test paths in isolated worktrees. Return exact commit,
diff/source hash, focused results and remaining problems; no self-acceptance.
Root integrates only reviewed bytes and verifies the actual temporary connection.

## HOST01/1 exact Python seam

`MockHostSession.open(database_path)` returns a context manager/object. It
acquires nonblocking exclusive POSIX flock on the permanent canonical sidecar
`<canonical-db-path>.pal-v5.lock` before owners open. It creates the DB file if
absent, under the lock. File DB only; memory/temp/SQLite URI and unsupported
platforms refuse. Resolve the supplied local path once. Sidecar is never unlinked
on close; require no-follow sidecar, regular file and one hardlink. DB must also
be a regular file with one link. Bind both paths/device/inodes and creator PID.
FD is non-inheritable. Keep a strong process registry of live guards keyed by
canonical DB, so same-process duplicate, forged instance, GC or atexit cannot
release another lifetime. No forced unlock, PID kill or automatic lock retry.

Read-only properties: `database_path`, `session_id`, `runner_id`, `phase`,
`db_uuid`, `orphan_lease_id`. Fresh session/runner identities use stdlib UUID;
`phase` is owned→startup→ready→closed. UUID/profile is persisted by TSK, not HOST.

- `check_connection(connection, ready=False)` validates exact live registered
  object, PID, open FD, path/inodes and PRAGMA database_list's main filename
  against the bound canonical DB. Reject wrong/blank main, aliases/replacement
  and after-close/forked use. ready=False means readiness is not required; it is
  not startup permission. ready=True also requires ready. Raise RuntimeError for
  these bounded host refusals; TSK translates them to unavailable/conflict.
- `operation(ready=False)` is a reentrant context permit for short owner
  transactions. It prevents close, but does not create DB/lease authority. An
  invocation's nested TSK operations must not deadlock.
- `activity()` requires ready, is acquired before admission, and remains held
  through callback cessation and the end-record attempt, including BaseException
  paths. Release in finally. An operation/activity never authorizes remote work.
- `mark_registered(db_uuid, orphan_lease_id)` is called only by TSK after a
  committed/reconstructed registration. owned→startup; exact same binding is an
  idempotent retry, different binding refuses. It cannot mint/replace enrollment.
- `activate()` is called only by successful TSK.finish_startup; startup→ready
  consumes recovery eligibility. No ordinary caller/model activation authority.
- `close()`/context exit refuses any outstanding activity or operation permit.
  Check ownership/PID; close successfully marks closed, unlocks/closes FD and
  removes the exact registry member. No __del__/GC/atexit unlock path. A forked
  child cannot use the guard; an inherited FD may keep the lock, failing closed.

Database/inode checks are accidental-alias protection, not hostile filesystem
proof. Local POSIX fixture proof does not establish network filesystem behavior.

## TSK01 recovery exact seam and enrollment

`TaskStore(..., startup_guard=None)` adds the trusted optional seam. The read-only
`TaskStore.startup_guard` exposes that passed object to RUN only. Exact
MockHostSession class plus registry identity required; no duck-typed proof.
Validate the connection before initialization with a supplied guard. Add separate
tables for singleton DB UUID/profile (`managed-inprocess-mock/1`), append-only
session registration and lease→session/claim-WorkRef binding. Do not alter the
existing lease table or enroll an existing active lease retroactively.
Read UUID inside BEGIN IMMEDIATE for registration/recovery, comparing a bound
guard UUID when present. Binding includes the claim epoch, not current epoch.

`register_host()` → Result `{session_id, runner_id, orphan_lease_id}`.
Only owned/startup, valid guard/DB. Atomically enroll/register this nonce and
capture the sole active lease ID (or null). Retry by the same nonce reconstructs
the original registration/snapshot, including after commit/reply loss. Mark guard
registered only after commit. Missing/malformed enrollment or old active lease's
managed ownership never becomes qualified by this registration.

`recover({key, lease_id})` → Result, closed nonempty-string input. No caller
nonce/status/desired state/cessation boolean. Requires valid startup guard and
registration. Distinct `recover` replay namespace: same key/input replay precedes
current snapshot/live state checks but still needs current valid guard/DB;
different input conflicts. A prior settled receipt can be read at a later valid
startup without restoring execution authority. No guard/ready-phase new recovery
refuses. A rejected/held recovery stores no replay, so retry remains legitimate.

New recovery requires expected lease==this registration's captured orphan and
its prior registered managed session, DB UUID/profile and exact claim WorkRef.
It must not belong to the current session. Unmanaged/missing/corrupt proof is
unavailable with no writes. Missing lease is not_found; closed lease under a new
key conflicts; input is invalid_input. SQLite/owner faults unavailable; BaseException
rolls back owned transaction and propagates. BEGIN IMMEDIATE, no model/I/O wait.

Success settled value:
`{disposition:"settled",work_ref,state,control_status:"none",recovered_lease_id,
interrupted_call_ids:[str]}`. Inspectable hold value:
`{disposition:"held",work_ref,state,control_status,lease_id,step_id,
reason:"artifact_tail"|"external_tail"}`. Hold changes no DB rows/events/replay,
retains occupancy and stays startup/not-ready. It is distinct from corruption.
The main draft path therefore remains a whole-C13 blocker until the next frozen
ART adoption slice; never hide this as general recovery PASS.

`finish_startup()` → Result `{session_id,runner_id,status:"ready"}`. Verify own
registration/UUID and no occupied unresolved lease inside transaction, then
activate after commit. Repeated same-session ready check can return its receipt;
no reactivation/recovery eligibility. Conflict while held, no fallback claim.
Empty valid startup changes no work/state event or budget.

For an enrolled DB, every execution authority path requires ready guard AND
lease.session/runner/UUID matching that guard: claim/reclaim, admission, begin,
finish, ask, end, release, work-attached model/step reservation and source
registration/adoption. Include ART authorize_save and VER save-authority context;
fact/history inspection stays readable. Claimed runner_id must match guard.runner_id.
Guardless connections may create/read/control/source-stop; they may not execute
or reserve workless model budget against enrollment. Lifetime validity alone
does not authorize startup recovery after ready. Closed guard blocks even a
returned-but-not-adopted begin_step. Controls/MEM do not wait on model/activity.

## Atomic validation and disposition

Validate before owned settlement writes: flags, latest/old revision relation,
questions and bidirectional artifact set; all calls/reservation/Step links and
their exact claim-epoch WorkRef. Nonempty IDs, canonical C15.call ID, strict
bounded nonnegative SQL/wire indexes, known Action/status and
`required(old) <= full call.sources <= registered(old)` are mandatory. Mutually
consistent empty/forged IDs or sources still fail unavailable. Earlier leases'
finished/abandoned Steps are immutable history; dangling started links refuse.
Reservation-only crashes are consumed history, not corruption/refund/rebinding;
validate reservations referenced by calls, not a fictional call for each reserve.

Internal `interrupted` is created only by recover, after old managed lifetime
proof. It means execution ceased, entry/result unknown. It is terminal without
output, never returned. Any interrupted call with a Step is corruption. end_call
still accepts only returned/raised/not_entered; on interrupted it conflicts.
Deliberately update every status allowlist (admission, old-call validation,
release, questions, get_call/RUN tails); get_call may_enter=false for interrupted.

| Valid saved orphan tail | First slice |
|---|---|
| admitted, no Step | interrupted; settle, fence and close |
| returned/raised/not_entered, no Step | preserve status; settle; lost output is not success |
| returned + finished/abandoned Step | preserve result/history; settle |
| started report/lookup/verify, returned call | abandon uncommitted observation; settle |
| started ask, returned call | consistent uncommitted ask abandons; atomic saved ask means finished Step/history; half-state unavailable |
| started compose | held artifact_tail, no save/adoption/replay |
| started operate | held external_tail; no EXE-recover or abandonment invented |
| unlisted/unknown/corrupt/unmanaged | unavailable, no writes, occupied |

After validation/tail classification premint bounded event identity under the
existing transaction-ownership guard. No new token/boolean can bypass it. Mark
eligible admitted interrupted, abandon only safe unfinished owned Steps, close
lease, preserve budgets/reservations/source availability. Latest terminal
completed/cancelled/failed state/epoch stays; latest nonterminal fences epoch+1
once (overflow unavailable). State cancel > paused/pause flag > valid open
question waiting_input > queued. Superseded never revives; old failed cannot fail
replacement. Clear applied pause/drain flags; append one current C14 state event
and replay, atomically commit. Share the private latest-intent logic with release
where it safely preserves existing behavior; no divergent CHANGE state machine.
Recovery physical cleanup does not MEM-regate original sources. New use/adoption
does gate full producer provenance. Source-stop question closure and unrelated
optional-stop answers remain intact. Same-key replay adds no epoch/event/charge.
No old callback dispatch/reservation reuse; fresh inference has a new call/lease
and remains under cumulative finite Goal/host ceilings.

## RUN01/3 connection

Managed MockRunner uses guard.runner_id and its invoker activity permit; legacy
runner keeps its existing fresh identity. RUN does not register/recover/activate
implicitly or own persistent recovery state. Host startup calls explicit TSK APIs
before run_once. Preserve callback-end retry bounds and all BaseException exits.
New epoch verification key is new; old VER never completes it. Existing completed
ART is history and no body/save/receipt/model invocation is repeated on restart.

## Fixed examples and completion conditions

Before implementation, separate tests bind this file and exact assignment base:
real two-process live/SIGSTOP contention; process-death admitted interruption
then exactly one fresh callback; same-process duplicate, forked child use/FD hold,
wrong/blank DB, symlink/hardlink/path replacement, outstanding permit close and
after-close execution refusal. Temporary SQLite only; no existing DB argument.

TSK cases: registration/claim/admit/return/begin/finish crash boundaries; reserve
only preserved; same-runner text other session refused; status/link/source/index
corruption no writes; report/lookup/verify vs compose/operate hold; ask committed
reply-loss vs half-state; ART history/held receipt; no old VER completion; latest
cancel/pause/change/source-stop ordering through two connections; exhausted
budget still settles without refund; transactional prewrite/abort/BaseException
rollback; recover/registration reply-loss replay and exactly one epoch/event.
Immediate structured controls remain usable while callback holds the lifetime.

HOST and TSK tests precede source; SOL adds actual managed MEM/TSK/RUN/ART/VER/C14
subprocess connection/demonstration. Required affected regressions/full suite and
separate source review use exact integrated bytes. Return diff, test results,
corruption refusal, unresolved compose/operate and trusted-profile limits. No
provider/UI/whole-goal PASS. Follow next with precise ART recovery adoption, then
PRI; technical sequencing does not require another human permission request.
