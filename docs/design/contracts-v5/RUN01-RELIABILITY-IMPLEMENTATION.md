# RUN01/2 reliability implementation

Opus F1 identified that RUN01/1 mapped every failed local Result to terminal
Goal failure. This change applies the frozen RUN01-RELIABILITY scope without
changing TSK, MEM, shared contracts or the invoker's ownership model.

Before admission, unavailable now attempts a safe yield with a fixed reason. A
failed release is returned honestly; the runner does not assume occupancy was
freed. An explicit later run can use a new lease/call identity after successful
release. A committed reservation with a lost response stays consumed.

After successful callback return, only begin_step and finish_step are retried:
maximum three immediate attempts, identical request and keyword inputs, and only
on unavailable. Successful replay therefore recovers a lost local commit response
without another model call, step reservation or event. Persistent unavailable
returns a fixed bounded failure and keeps the slot and nonterminal Goal. Lookup
search/read unavailable after step creation also retains the unfinished result;
this slice adds no search retry loop or stored output recovery.

On run entry, the claimed Step list and deterministic next call ID are inspected
before reserving any model budget. A started Step or existing call blocks reentry
without an invocation, extra budget or terminal failure. After an invoker error,
its durable call status distinguishes a known raised callback from an admitted or
returned unresolved call. Unknown status retains occupancy. A known raised callback
or invalid output can still fail explicitly. Pause/cancel/source-stop precedence
continues to belong to TSK; existing barrier tests and a new control-during-retry
case confirm that late adoption cannot override newer intent.

No invoker owned-ID is removed. No callable or uncertain admission is retried.
There are no refunds, sleeps, provider calls, schema changes or general retry
framework. This is local mock reliability, not MOD persistence or C13 recovery.

## Evidence and prevention

The pre-fix test run reproduced the F1 behavior and missing reentry protection:
`/private/tmp/pal-run01-reliability-before.log` (19 tests; 7 failures, 2 errors).
The two errors are assertions attempting to inspect a failure Result where the
old runner instead returned a successful terminal-release receipt. The original
unconditional failure mapping, and lack of a pre-reservation unfinished-call check,
are the concrete causes; this is not inferred from elapsed timing.

The correction separates pre-admission, returned-output and known-cessation cases.
The next regression condition is to inject unavailable at every newly added RUN
owner boundary and check phase-appropriate state, slot, budget and invocation count;
never equate a persistence failure with an unresolvable Goal.

Final author command:

```
/opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_mock_execution_v5.py -v
```

Result: **22 tests PASS**, 0.175 seconds. Log:
`/private/tmp/pal-run01-reliability-final.log`.

Real isolated MEM/TSK consumers cover one-shot failures, commit-then-unavailable
begin/finish receipts, persistent begin/finish/search failures, same-runner reentry,
ambiguous committed admission, lost reservation response, explicit later safe run,
actual callback counts, durable budget/event uniqueness, occupancy and newer pause.
Existing actual mock barriers still cover pause/cancel/source stop while owned,
cessation failure, no duplicate invocation and no transaction across callbacks.

Full regression and independent review belong to Root and are NOT_RUN here.
Persistent returned output remains blocked for future recovery; it is not saved
as a MOD raw response and cannot safely be recomputed. No ART/VER/completion,
real provider or product activation is claimed.

## Follow-up: preserve control-driven release of fenced output

Root inspection found a regression in the first reliability correction: immediate
error returns on persistent unavailable and same-runner unfinished-work detection
also blocked release after a newer pause/cancel/source stop. The call had actually
ended, so C13 permitted the fenced output to be discarded under the newer intent.
The runner had conflated preserving unadopted output with always retaining its slot.

The new `yield_or_retain` path attempts only TSK.release(yield). TSK decides from
its current transaction state: newer control plus ended calls may release; ordinary
unfinished output or an unended admitted call conflicts and stays occupied. No
model call, budget reservation, output adoption or refund occurs in this path.
It is used for persistent post-output unavailable, unfinished-work reentry and
unresolved invocation outcomes. Failure to release returns a fixed bounded error.

The initial reproduction log `/private/tmp/pal-run01-fenced-release-before.log`
had cascading subtest occupancy. The improved test always cleans its temporary
scenario; `/private/tmp/pal-run01-fenced-release-before-isolated.log` independently
reproduces all 12 combinations: begin/finish × in-loop/reentry × pause/cancel/stop.
The corrected command passes **24 tests**, 0.238 seconds, at
`/private/tmp/pal-run01-fenced-release-after.log`. Actual TaskStore/MEM assertions
cover latest state, slot release, one actual callback, unchanged budget and no
progress event. An uncertain admitted call remains occupied even after cancel.
The existing unfenced persistent-failure tests still require retained occupancy.

Next changes to unavailable/reentry handling must run both sides of this boundary:
unfenced output remains held; ended, control-fenced output can release according to
TSK's latest intent. The runner must not duplicate the TSK control state machine.
