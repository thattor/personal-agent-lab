# Durable host target selection — Issue4

Exit audit followup: `selection-snapshot-full.txt`92 tests PASS and
`snapshot-version.json` bind the small consistency repair after624fc96. Read-only
code comparison found projection invalidated the entire offered snapshot while
application checked only the chosen target. Both now use the same whole-snapshot
check; a claim on Cedar invalidates the question even if a stale click names Birch.
No relaxation or new behavior scope. Original91-test/version evidence retained.
GitHub Issue4 CLOSED/COMPLETED readback is `issue4-readback.json`.

Official Opus and SWE-2 High contracts and reconciliation are preserved here;
fresh auth/no-extra-charge receipts precede each actual consultation. Adopted
D-024 predates implementation. No paid fallback or additional connection used.

`selection-final-full.txt`: 91 full tests PASS. `version.json` binds source,
fixture hashes and Python/platform. `node --check pal/web/app.js` exited0;
this is syntax verification, not live browser evidence.

N1-03: `selection-targeted-final.txt` and `selection-final-full.txt` execute the
original nine-case0–3 mixed-state matrix. Zero wrong-target mutations;
immutable acceptances unchanged. Unknown target/selection and foreign source
have a generic fixed rejection; stale epochs/recovery do not apply operations.
More than3 matches require a narrower cue rather than guessing. Concurrent
different-key selections yield one applied and one already-resolved result;
duplicate-key replay returns the original result and changed payload conflicts.
Original-request/target-source forgetting hides every label and blocks selection.
Correction uses the original text-bearing user record, not the button record.
`correction-source-green.txt` proves forgetting that source fences execution.
HTTP integration exercises natural request, guarded projection, exact selection
payload, dedupe and immutable other-target state. Fixed outcome/question replies
commit atomically with ingress; no provider call is required for these replies.

N1-04: six actual SIGKILL runs in `test_target_selection` cover selector creation
and selected correction, each mid-transaction/before-commit/after-commit.
Reopen/replay preserves bindings, exactly one correction revision/selector,
no duplicate Goal/artifact/report, stored fixed replies and idempotent outbox.
Schema tests separately kill the migrator before/after commit and preserve v1
rows and recoverable version/schema atomicity. Full existing crash/fencing suite
also passes. No manual canonical-state repair occurs.

Red/first-failure logs retained. The first parser matched `その` as literal cue
`そ` plus `の`; ordered explicit deictic recognition fixes this, with the frozen
matrix and full-width separator regression guarding it. No failing candidate
was served to the existing host.

This proves bounded synthetic host behavior and HTTP integration. N1-06 actual
official-provider UI and N1-07 direct human usefulness remain separate gates.
Production/old-soak DBs, running host and prior human attestations are untouched.
Schema2 cannot be reopened by the old schema1 binary; test only in disposable
DBs first, and use a new owned candidate for subsequent live UI validation.
