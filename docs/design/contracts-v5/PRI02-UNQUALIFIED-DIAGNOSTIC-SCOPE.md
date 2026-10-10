# PRI02-DIAGNOSTIC/1 — bounded local unqualified text retention

SOL freezes this fixture/source correction at520ff5e after C086 Native Sol REFINE
under the D041 approved design fallback. Fresh exact Opus5.5 AGY quota is exhausted,
overages remain OFF, and no new Opus call was launched. This is not an Opus verdict.
Current strict effective-model, cessation and NativeReturned requirements stay.

## Goal and exclusions

Preserve bounded already-captured valid text when a qualification/ending check
rejects it, so a future original failure can be investigated without reconstructing
output or repeating inference. Raw material stays local in the existing private
call journal; publish hashes/necessary facts only. No N3, T2 or real Expert entry
is authorized. No preprompt fail-fast gate is adopted before teardown feasibility
is established. No CO/runtime/state/ledger change, new engine/auth/cost/service,
old/live DB, source metadata rewrite, new invocation or new output adoption.

## Pure buffer API

Add `NativeTextBuffer.unqualified_snapshot()` returning a defensive plain mapping
with exactly these keys:

* version: `NATIVE-TEXT-DIAGNOSTIC/1`;
* authority: `unqualified`;
* phase: `not_begun`, `capturing`, `sealed` or `poisoned`;
* text: joined currently retained valid chunks (empty after poison/before begin);
* text_sha256: SHA256 of that exact UTF-8 text;
* utf8_bytes, chunks: existing counters, including zero;
* request_sha256, profile_sha256, attempt_ref: original immutable bindings;
* requested_model_id: original requested ID, never asserted effective model.

It never changes capture state, opens/seals a buffer or validates an ending.
Existing32768 UTF8/2048 chunk limits and poison-clears behavior stay. Snapshot
cannot be passed as a `NativeReturned` capture or qualify `finish`; no cessation
or authority fields are fabricated. Returning a snapshot after a failed strict
ending is diagnostic only. Caller mutation cannot change the live capture.

## External wrapper

Initialize the local buffer variable safely. On the existing generic entered
failure path, issue the existing supported stop first exactly once, then attempt
one best-effort write of the snapshot to `unqualified-output.json`. Continue the
existing original non-pumping diagnostic and exception/finally behavior unchanged.
Snapshot/write Exception or BaseException cannot delay/repeat/replace stop or
replace a propagating original BaseException. No additional status/events,
execute, retry, ledger release or typed NeverEntered. Known-success and exact
NeverEntered paths retain their original behavior. No output is returned from
the diagnostic record, parsed as an Action or stored as a TSK native ending.

This does not capture all original protocol frames. Poisoned/malformed input is
not retained as valid text. Original N2 body cannot be recovered retroactively.
Source changes invalidate the old wrapper/capture envelope; no new candidate is
qualified by this helper or by the existing N2 receipt.

## Ownership and proof

Independent Sol owns new fixed pure-buffer and wrapper failure tests before
implementation. CO SWE is preferred for the pure `pal/native_text_v5.py` change
when a D041-permitted planner is actually available. The ordinary CO entry has
no preplanned-input route; exhausted Opus quota does not permit a SWE design
planner substitution. Native Sol owns the pure buffer under the approved fallback
for this milestone; Astra owns only
`tools/native_devin_text_v5.py` after fixed tests and the frozen API. SOL owns
shared scope/integration/canonical records. Separate source reviewer follows.
Use isolated worktrees, exact base/tests, no same-file writes or state edits.

Fixed tests cover unqualified/defensive bounds, unchanged poison/strict finish,
diagnostic lookalike refusal, actual mismatched/null/unverified fixture ending,
stop-before-snapshot/diagnostic, best-effort write/interrupt failure, original
exception and one-execute counts. Existing pure buffer/call/wrapper suites and
finished Root full regression remain prerequisites for adoption. All provider
endings in these tests are fixtures. Separately research documented existing
server model-ack fields/timing; missing acknowledgement stays UNCONFIRMED rather
than an invented unsupported or qualified result. Whole goal remains NOT_MET.
