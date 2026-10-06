# ACCEPTANCE.md — Stable-0 definition of done

Stable-0 may be declared only when all REQUIRED rows are PASS with evidence and the soak gate is complete. blocked, partial, mock-only, and not_run are not PASS.

| ID | Required | Acceptance | Evidence | Status |
|---|---|---|---|---|
| S0-01 | yes | Normal conversation works without unnecessary Goals; reversible draft intent creates work only when needed | automated + live language log | not_run |
| S0-02 | yes | Slow task execution does not block conversation/control ingress | deterministic concurrency test | not_run |
| S0-03 | yes | Goal + fixed criteria + Attempt + host receipt complete a local draft end-to-end; model self-report alone cannot complete it | automated + live provider smoke | not_run |
| S0-04 | yes | Executor/model cannot mutate canonical Goal/criteria/approval/reference state or invoke unallowed capability | negative tests | not_run |
| S0-05 | yes | Duplicate message/result and stale/late result cause no duplicate completion/report/effect | deterministic tests | not_run |
| S0-06 | yes | Crash/restart at acceptance/claim/completion/outbox boundaries preserves state and avoids duplicate report | fault-injection tests | not_run |
| S0-07 | yes | Cancel prevents late result from completing Goal; pause/resume and input-resume work exactly once | deterministic + fault tests | not_run |
| S0-08 | yes | Correction supersedes old context; forget stops AI reference while retaining raw user-viewable history | deterministic memory tests | not_run |
| S0-09 | yes | Secret canary never appears in persisted conversational memory, prompts, logs, or test artifacts after sanitization path | automated scan | not_run |
| S0-10 | yes | One official real provider path works with an already-authorized account and verified no-additional-charge condition | capability record + live smoke | not_run |
| S0-11 | yes | Failure/blocked/unverified states are reported; no silent success and no infinite retry | automated tests | not_run |
| S0-12 | yes | UI exposes conversation result and read-only inspect state sufficiently to diagnose Goal/Attempt/evidence | browser smoke | not_run |
| S0-13 | yes | 72-hour soak completes with zero manual canonical-state repair | soak log | not_run |

## Required automated scenarios
At minimum:
1. valid and invalid state transitions;
2. duplicate ingress;
3. duplicate result;
4. delayed stale result after correction/cancel;
5. input waiting/resume dedupe;
6. crash immediately after Goal/outbox commit;
7. crash after Attempt claim;
8. host receipt mismatch / fabricated evidence;
9. unallowed capability request;
10. reference-stop while an Attempt is in flight;
11. secret-canary persistence/log scan;
12. slow Attempt while conversation responds.

## Live provider smoke
Use synthetic/non-secret data. Record provider/model/adapter capability, start/end time, host artifact/receipt, and acceptance checks. Do not record credentials.

A mock pass does not satisfy S0-10.

## 72-hour soak
Start only after S0-01 through S0-12 are PASS.

Minimum workload:
- at least 3 separate sessions across the 72 hours;
- at least 20 user turns total;
- at least 5 Goals;
- at least one cancellation;
- at least one correction or reference-stop;
- at least one process restart while unfinished state exists.

Manual canonical-state repair means directly editing the DB/state files, rewriting canonical rows by ad-hoc script/SQL, or manually fabricating receipts/events to recover. A normal application restart through the supported run command is not state repair.

Pass requires:
- no manual canonical-state repair;
- no lost accepted message or Goal;
- no duplicate user-visible completion caused by replay;
- no stale/cancelled result applied to current state;
- no secret-canary leak;
- every failure/blocker represented in inspectable state.

Nothing can compress the 72-hour wall-clock gate. Continue improving non-disruptive tests/docs during the soak, but any change to canonical state semantics, recovery logic, or persistence resets the soak clock.

## Evidence discipline
Each PASS row must link to a commit, test/log/artifact path, or live-smoke record in the repo. Reviewer opinions are not evidence. Codex must not self-certify Stable-0 until this file is fully evidenced.
