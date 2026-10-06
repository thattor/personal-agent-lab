# ACCEPTANCE.md — Stable-0 definition of done

Stable-0 may be declared only when all REQUIRED rows are PASS with evidence and the soak gate is complete. blocked, partial, mock-only, and not_run are not PASS.

| ID | Required | Acceptance | Evidence | Status |
|---|---|---|---|---|
| S0-01 | yes | Normal conversation works without unnecessary Goals; reversible draft intent creates work only when needed | [full tests](evidence/tests/ui-native-full.txt); [live language](evidence/live/2026-10-06-clean/language.json); [browser](evidence/ui/browser-smoke.md) | PASS |
| S0-02 | yes | Slow task execution does not block conversation/control ingress | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-03 | yes | Goal + fixed criteria + Attempt + host receipt complete a local draft end-to-end; model self-report alone cannot complete it | [full tests](evidence/tests/ui-native-full.txt); [live host receipt](evidence/live/2026-10-06-clean/host-evidence.json); [live result](evidence/live/2026-10-06-clean/result.json) | PASS |
| S0-04 | yes | Executor/model cannot mutate canonical Goal/criteria/approval/reference state or invoke unallowed capability | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-05 | yes | Duplicate message/result and stale/late result cause no duplicate completion/report/effect | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-06 | yes | Crash/restart at acceptance/claim/completion/outbox boundaries preserves state and avoids duplicate report | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-07 | yes | Cancel prevents late result from completing Goal; pause/resume and input-resume work exactly once | [full tests](evidence/tests/ui-native-full.txt); [controls](tests/test_controls_memory.py); [SIGKILL pause/resume/input](tests/test_crash.py); [runtime fencing](tests/test_runtime.py) | PASS |
| S0-08 | yes | Correction supersedes old context; forget stops AI reference while retaining raw user-viewable history | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-09 | yes | Secret canary never appears in persisted conversational memory, prompts, logs, or test artifacts after sanitization path | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-10 | yes | One official real provider path works with an already-authorized account and verified no-additional-charge condition | [official access/cost proof and live smoke](evidence/live/2026-10-06-clean/result.json); [actual draft](evidence/live/2026-10-06-clean/draft.txt); [native boundary tests](tests/test_native.py) | PASS |
| S0-11 | yes | Failure/blocked/unverified states are reported; no silent success and no infinite retry | [33-test log](evidence/tests/s2-runtime.txt); [runtime](tests/test_runtime.py), [core](tests/test_store.py), [controls](tests/test_controls_memory.py), [crash matrix](tests/test_crash.py) | PASS |
| S0-12 | yes | UI exposes conversation result and read-only inspect state sufficiently to diagnose Goal/Attempt/evidence | [actual Chrome smoke](evidence/ui/browser-smoke.md); [canonical readback](evidence/ui/browser-state.json); [HTTP tests](tests/test_http.py) | PASS |
| S0-13 | yes | 72-hour soak completes with zero manual canonical-state repair | [fresh soak02 baseline/start](evidence/soak/2026-10-07/start-02.json); [old run invalidation](evidence/soak/2026-10-06/ui-recovery-finding.json) | in_progress (soak02 human_pending) |

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

## S1 evidence — 2026-10-06

[8 deterministic core tests](evidence/tests/s1-unittest.txt), [test source](tests/test_store.py), [versions](evidence/tests/s1-version.json). Covers duplicate ingress/result, single slot, immutable criteria, host receipt gate, artifact immutability, cancel fencing, replay and schema guard. This is partial evidence only; it does not satisfy full fault, capability, memory, live-provider, UI or soak rows. No REQUIRED row promoted to PASS.

## Controls/recovery evidence — 2026-10-06

[20-test full log](evidence/tests/s1-controls-crash.txt), [controls/memory tests](tests/test_controls_memory.py), [18 SIGKILL boundary subcases](tests/test_crash.py). Real disposable SQLite DBs verified atomic create/claim/artifact/completion/control/delivery before and after commits, bounded restart retries, reference-stop and conversational correction fencing, stale input question rejection, secret-canary DB/WAL scan. Runtime/worker/UI integration still required before full rows PASS. Defect diagnosis and shared invalidation fix: [record](docs/DEFECTS.md).

## S2 host runtime evidence — 2026-10-06

33 tests PASS. [Full log](evidence/tests/s2-runtime.txt), 21 real transaction SIGKILL subcases plus worker death between Executor return and host apply. Event-barrier verifies conversation/cancel while Executor remains blocked. Negative result schemas attempt to alter Goal/criteria/approval/reference/evidence and invoke send/shell; host rejects all, no receipt. Native model tools are not yet exposed/enabled. No live/UI/soak claim.

## Native/UI and soak preparation evidence — 2026-10-06

[47-test full log](evidence/tests/ui-native-full.txt). Native real-path smoke PASS used the already-authenticated official Claude Pro connection, three short synthetic tool-free calls, no credits/fallback/new login; adapter and actual versions in the result. The failed auth environment attempt and partial planning-transcript candidate are preserved and do not count as PASS. Host verified the clean 276-byte draft SHA256/revision/epoch/source binding. [Defects and fixes](docs/DEFECTS.md). Browser/HTTP evidence covers normal conversation, local draft, inspect, supported restart, read-only/CSRF/CSP constraints and session receipt.

S0-01–12 now PASS. S0-13 remains not_run until a clean baseline and actual soak start are recorded. The preparation [preflight log](evidence/tests/soak-preflight.txt) is explicitly PREFLIGHT_ONLY. D-016 retains real human-use minimums; a fully scripted soak cannot pass. Human session span uses host observation times rather than a client-supplied timestamp.

## Soak monitor readiness — 2026-10-06

[55-test full log](evidence/tests/ui-native-soak-full.txt), [gate and monitor contract tests](tests/test_soak.py), [separate final preflight](evidence/tests/soak-preflight.txt), [preflight summary](evidence/tests/soak-preflight-summary.json), [fsync hash chain](evidence/tests/soak-preflight-measurements.jsonl), [source/version baseline](evidence/tests/soak-preflight-manifest.json). Preflight proves owned-process restart, a new Attempt completing the same Goal, original/replayed ACK digest equality, one outcome/receipt and read-only invariants. It is explicitly not 72-hour or human-use evidence. Required human participation and review choices: D-016/D-017.

## Actual soak start

Started 2026-10-06T13:41:26.756470+00:00 from clean pushed baseline c887c35d540a55f6f3108d546da3220f0852b76a. Mock adapter, loopback port 58500, 10-second bounded draft delay. Initial read-only checks/secret-canary scan PASS; zero human turns/Goals attested. This start is not S0-13 PASS. Latest mutable measurement/candidate files stay in ignored runtime/soak-20261006-01; commit only evidence summaries/snapshots without raw human conversation. Runtime/probe semantics must remain unchanged during this run.

Session-close full verification: [55-test log while real soak runs](evidence/tests/soak-start-full.txt). Operational hourly follow-up registered; no scheduled execution or 72-hour completion is claimed. The required human attestation remains pending; master Issue #1 stays open.

Read-only goal-continuation check 2026-10-06T13:50:31.174033+00:00: [live-handle/health/baseline checkpoint](evidence/soak/2026-10-06/continuation-01.json), [55-test suite](evidence/tests/soak-continuation-01.txt). S0-13 remains in progress and human_pending; no PASS promotion, no clock reset or canonical repair.

Blocked audit 2026-10-06T13:52:37.644578+00:00: [three-turn human-input blocker](evidence/soak/2026-10-06/blocked-audit.json), [55-test full verification](evidence/tests/soak-blocked-audit.txt). S0-13 remains in_progress/human_pending and is not PASS. Runtime/monitor remain live, baseline unchanged, no repair; controller blocked status does not invalidate or complete the measurement run.

First scheduled operational audit 2026-10-06T14:44:41.652900+00:00: [owned-host/hash-chain/cadence/read-only invariant evidence](evidence/soak/2026-10-06/hourly-audit-01.json). 13 measurements, 15 valid chain records, runtime baseline unchanged, no findings or canonical repair. [Full suite](evidence/tests/soak-hourly-audit-01.txt). This is operational monitoring evidence only; S0-13 remains in_progress/human_pending, no human attestation or PASS promotion.

First direct human attestation 2026-10-07 06:05 JST: [matched receipt and monitor chain anchor](evidence/soak/2026-10-06/human-session-01.json). One human turn / one session; planned unfinished restart armed, not yet proven. [Full suite](evidence/tests/soak-human-session-01.txt). S0-13 remains in_progress with remaining human/time gates, not PASS. Baseline unchanged, no canonical repair.

2026-10-07 human UI finding: recovered restart completed same Goal once, ACK digests matched, artifact opened; stale outage warning remained. [Retained recovery/finding evidence](evidence/soak/2026-10-06/ui-recovery-finding.json). Routine fix verified by [actual JavaScript red/green recovery probe](evidence/ui/recovery/after.txt) and [55-test full suite](evidence/tests/ui-recovery-full.txt); S0-12 remains PASS with corrected UI. S0-13 soak01 invalidated and stopped with fsync reset_required, not PASS. Fresh baseline/run required; prior counts/time/restart proof not transferred.

Fresh soak02 started 2026-10-07T06:08:30.879116+09:00 after UI fix/full suite PASS from clean pushed baseline 37b33dbf8a7d2df1b710e3e8b9d8b4dcffffbc9e. [Start/manifest/initial chain evidence](evidence/soak/2026-10-07/start-02.json). Zero old counts/time/restart proof transferred. Runtime/soak-20261007-02 is the active acceptance run; operational hourly follow-up updated accordingly.
