# RUN01/2 — preserve work on transient local persistence failure

Technical disposition of Opus milestone task6bd433a2799a49d2b27d5c5bc9708e7d F1
under D038. This is the next bounded correction to the accepted local mock slice.
No model re-invocation, new provider, MOD ledger/recovery, ART code or real DB use.

Owner: isolated native Astra, writing only pal/mock_runner_v5.py and
tests/test_mock_execution_v5.py plus RUN01-RELIABILITY-IMPLEMENTATION.md here.
Root owns TSK/ART/common scope/canonical state; separate Sol reviews this change.
Base: the committed scope snapshot recorded in Root dispatch. Read TSK02 scope,
Opus milestone note, current runner/TSK/MEM/contracts and existing connection tests.

An unavailable Result before a model call is admitted must not make a Goal terminal.
Yield the safe lease with a bounded reason; latest pause/cancel/drain intent wins.
No automatic new model attempt occurs within this run. A later explicit run may
claim a new lease if the prior lease was actually released.

After a callback returns, repeat only idempotent local begin_step/finish_step
writes on unavailable, at most three same-input attempts. A commit whose response
was lost must replay without duplicate step/budget/event. Bounded local search/read
retries may be used if needed after a Step starts. No callable retry, sleep loop or
new retry framework. Persistent unavailable after returned output retains occupancy
and returns a bounded failure; it must not falsely declare the Goal failed or release
an unfinished output. This remains blocked for future recovery, not recovered now.

Retried run_once on the same runner must detect an existing admitted/returned/
started unfinished call/Step before reserving another model unit; do not silently
reinvoke, discard it or newly fail the Goal. An original raised callback or invalid
model output may explicitly fail as unresolvable within this slice. Actual cessation
write failure still retains the slot. Current valid control precedence is unchanged.

The invoker's conservative owned-ID retention is acceptable: admission failure does
not authorize same-ID dispatch retry, and a released lease yields a new call identity.
No cleanup of that set may reopen a possibly committed/unknown admission.

Verify real MEM/TSK/mock consumers with deterministic injected one-shot unavailable,
commit-then-unavailable, persistent failure, explicit later safe run, and existing
controls/source-stop/ended-call guards. Assert actual callback count, durable state,
budget, event uniqueness and lease occupancy. Full regression belongs to Root.
Return diff, exact tests/results, findings and remaining recovery limits.
