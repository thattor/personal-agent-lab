# RECOVERY01 preparation — C080

Preparation only: no frozen new API, source, test PASS or product recovery claim.
Actual final Opus5.5 CHANGE review recommends scoped C13 recovery/startup lock
before PRI routing. Separate native Astra reads the actual v5 owner code and
confirms the following minimum seams. This record does not invoke old PAL code,
live databases, existing unknown CO/AGY calls, providers or external processes.

TSK owns leases, calls, reservations and Steps (`pal/tasks_v5.py`). A new runner
cannot claim the previous runner's active lease. RUN's MockInvoker thread lock
and in-process owned-ID set prevent repeated local dispatch; they are not a
process startup lock (`pal/mock_runner_v5.py:31`). TaskStore has no recover
method. C13 requires host-start recovery after old-runner absence and owned-call
reconciliation; acquiring a lock alone does not prove external child termination.

First scope candidate: an OS startup lock tied to a canonical database identity,
held from startup through all mock callback cessation, plus atomic TSK settlement
of orphaned leases whose call endings and ownership are already saved and valid.
A PID string, timestamp or declared stopped boolean is not sufficient evidence.
The trusted mock boundary must exclude escaped external work. No PID kill or
forced slot release is proposed. Host lock and TSK recovery interfaces must be
frozen together before implementation; SOL owns their shared contract.

Saved states need distinct treatment:

| Saved state | Required disposition |
|---|---|
| returned and finished Step | Preserve saved results; no callback replay |
| raised or not_entered | May settle only with valid ended/ownership evidence |
| returned, output not adopted | Ending is separate from receipt/result recovery; never claim success |
| admitted | Entry/running/lost ending are indistinguishable; retain uncertainty without new proven cessation contract |
| unknown, corrupt or unbound | unavailable, occupied slot retained, no writes |

The later admitted-call stage may need a distinct interrupted/unknown status and
host-local cessation evidence. That is a proposal, not an adopted enum or a way
to label process death raised/not_entered. EXE recovery is not silently invented
where no operation capability is implemented.

Across revisions, latest cancel wins, then pause, then eligible queued/waiting.
An old failure cannot fail a replacement. Questions, answers and completed
history stay intact. Consumed reservations are neither refunded nor reset.
Source-stop remains in force; physical cleanup and result reuse gates are
separate. Recovery cannot adopt old-epoch VER as current completion. A started
compose may already have an ART receipt: reconcile it or explicitly defer that
case, rather than simply abandoning/repeating the save.

Meaningful fixed cases for the freeze: real two-process lock contention; recovery
refusal while the old owner holds the lock; valid ended orphan recovery; admitted
and corrupt evidence retained; change/pause/cancel commit ordering; unchanged
budgets and source stops; transactional rollback/BaseException and immutable
same-key receipt replay; saved compose receipt prevents a second save/callback.
All use fresh temporary SQLite. Independent tests precede source, and SOL owns
actual integration plus final verification. SWE-2 High remains preferred for
module code through the qualified CO route when a bounded design is frozen.
