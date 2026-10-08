# ACCEPTANCE.md — Stable-0 definition of done

## C065 / INT00 preparation evidence (2026-10-09)

Common-wire Opus5.5 consultation, SOL technical dispositions, imported v5 provenance
and five synthetic shared expectations are preserved. Baseline full277 unittest tests
PASS on the approved host/mock environment. Product source and runtime DB are unchanged.
SWE-2 High implementation reached900seconds with unknown result/process outcome;
CO task6a9dea446fa241ceb6ee876bbdb08be9 is awaiting_decision, verified=false.
No code was returned, and no contract implementation verifier or independent code
review ran. These records do not qualify any new CT/E2E/provider integration or human
usefulness row. [Current continuation/evidence](STATE.md#exact-next-action--c065d034).

## C066 / D035 independent preparation evidence (2026-10-09)

PublishedCO0.4.5 is installed and loaded from a fixed payload, all96 file hashes
verified before and after execution. The same qualified state supports two actual
independent ordinary tasks; measured local Native intervals overlap96.164s.
Host cap is12 per Claude/Devin adapter, not a30-way result or vendor quota promise.

EXE02-request/1 and ART01-content/1 are pure unused modules: no external execution,
saving, Ref/ID issuance or completion. CO isolated diffs have separate Opus reviews;
SOL corrected strict keys and the old-current-freeze test assumption; final Opus
milestone review PASS, same five source/test hashes confirmed. Targeted39 and full316
unittest tests PASS (22.074s); synthetic request/mock-text/content preview PASS.
Original failure logs and the repaired review are retained. Three tasks verified,
13 Native calls (12 exact Opus5.5,1 exact SWE-2 High Free), actual maximum2 concurrent.
[Evidence](evidence/operations/co-update-045-20261009/verification.json),
[review](evidence/operations/co-update-045-20261009/milestone-review.md).

This preparation slice is MET. Old INT00 remains awaiting_decision/unknown and
unimplemented; new state/capacity does not resolve it. All service CT/E2E/provider/
reference-availability and overall user usefulness are NOT_RUN. Prior Stable rows
retain their original version/limits; no release or whole PAL completion.

## C067 / D035 second preparation evidence (2026-10-09)

Actual maximum3 independent CO tasks overlap on the same qualified state. Eight
completed local Native segments total262.733616s, not remote compute/vendor capacity.
Prior2 was SOL's small first pilot; no third-call refusal or two-task cap existed.

EXE02-file/1, EXE02-bytes/1 and VER01-integrity/1 are unused pure modules, with
separate Opus reviews, SOL corrections and six synthetic integration cases.
Full399 unittest PASS22.153s; targeted122 PASS. All11 source/test hashes match4ebab5a.
G's Opus assessment finds no source blocker but its document result remains
failed/verified=false. H independently verifies the exact one-line citation fix;
476 tokens, no other text/source change. H checks documents/metrics only and does
not rerun product tests. [Assessment](evidence/operations/co-update-045-batch2-20261009/milestone-review.md),
[verification](evidence/operations/co-update-045-batch2-20261009/verification.json).

Batch2:4 verified tasks,1 failed,23 actual Native calls (20 Opus5.5,3 SWE Free).
Host slots finally0, all96 payload/290 prior-state/13 original-record hashes intact.
This slice is MET for preparation. Old INT00 remains unknown/awaiting_decision;
service CT/E2E, actual v5 provider/storage/Goal flow and human value are NOT_RUN.
No product completion, new grant, current trial-proof renewal or release is claimed.

## Retained Stable-0 completion definition

Stable-0 may be declared only when all REQUIRED rows are PASS with evidence and the final audit is complete (D-019). blocked, partial, mock-only functional evidence, and not_run are not PASS. The original soak criterion remains unmet and historical; it is no longer required.

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
| S0-13 | no (historical D-019) | 72-hour soak completes with zero manual canonical-state repair | [fresh bilingual soak03 baseline/start](evidence/soak/2026-10-07/start-03.json); [terminal chain preserved](evidence/soak/2026-10-07/soak03-functional-development-stop.json) | NOT PASS (stopped for approved functional development; original time/count criterion unmet) |

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

## Historical 72-hour soak — optional after D-019
The original criterion below remains historical NOT PASS; D-019 removes its time/turn/session quotas from completion gates. Preserve runs and never reclassify unmet evidence as PASS.
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

2026-10-07 user-requested bilingual UI: Japanese/English labels and status/controls/errors/inspect headings; internal routing/canonical/receipt JSON remain English. [55-test suite](evidence/tests/ui-bilingual-full.txt), [actual UI refresh probe](evidence/ui/recovery/bilingual-after.txt). S0-12 PASS with presentation change. [Soak02 attested receipt/reset](evidence/soak/2026-10-07/soak02-human-and-reset.json); fresh bilingual baseline/run required under D-016/D-017, no prior time/count transfer.

Fresh bilingual soak03 start 2026-10-07T06:14:18.834450+09:00, clean pushed baseline 1863ef2a3037b335fa6f257a8d6fd95fb44da9dc. [Owned health/manifest/hash-chain and served bilingual UI](evidence/soak/2026-10-07/start-03.json). Previous runs retained; human/time/restart counts start from zero. Hourly follow-up now targets soak03.

Soak03 human participation: [first directly confirmed receipt and monitor anchor](evidence/soak/2026-10-07/soak03-human-session-01.json). S0-13 remains in_progress; one turn/session is not PASS.

Soak03 [first human draft/restart proof](evidence/soak/2026-10-07/soak03-human-restart.json): two confirmed turns / one session / one Goal; restart verified and one host-checked artifact. Remaining human/time/control requirements still pending; S0-13 is not PASS.

Soak03 [four-input conversation/cancel evidence](evidence/soak/2026-10-07/soak03-human-conversation-cancel.json): six confirmed turns, one session, three Goals, cancel fenced with no artifact receipt. S0-13 remains in_progress; correction/time/session/turn gates pending.

Soak03 [human correction and revision fencing evidence](evidence/soak/2026-10-07/soak03-human-correction.json): eight confirmed turns / four Goals / one session; correction verified. S0-13 remains in_progress with fifth Goal, remaining turns/sessions and >=72h human span/time pending.

Soak03 [second directly confirmed session and fifth Goal](evidence/soak/2026-10-07/soak03-human-session-02.json): 10 turns / 2 sessions / 5 Goals, restart/cancel/correction verified. S0-13 remains in_progress: >=20 turns, >=3 sessions, >=72h human span and elapsed soak still required.

2026-10-07 user-requested Opus/Astra reconsideration: [D-018 proposal, NOT adopted](DECISIONS.md). Functional real-provider UI acceptance is recommended before time quotas; existing acceptance definition/status remains unchanged pending one explicit user decision. Mock UI and quality_claim:none smoke do not prove semantic usefulness; no long-term PASS claimed.

## Functional acceptance — fixed before live execution, D-019
Required rows below are additions, not retrospective claims about mock/transport evidence. Synthetic test facts only. Actual public loopback UI/API and official provider route must run; preserve exact input/response/artifact/host receipts, provider/bounds/version and no-extra-charge proof. Automated content checks are not human usefulness evidence. Human evaluates this finite set once; no turn/session quotas.

| ID | Required | Fixed scenario and expected behavior | Evidence | Status |
|---|---|---|---|---|
| F0-01 | yes | Ordinary Japanese conversation gets relevant Japanese answer and creates no Goal. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-02 | yes | Remember synthetic project name Cedar and recipient Mika; later recall returns both using usable source context. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-03 | yes | Create Japanese local thank-you draft for Mika about Cedar, 2 sentences, no sending: actual artifact includes Mika/Cedar, fits requested purpose/constraints, host receipt/hash valid. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-04 | yes | Correct the active draft to project Birch; old Attempt/result fenced, revised artifact includes Birch and excludes superseded Cedar, criteria stay fixed. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-05 | yes | Remember unique synthetic fact; explicitly forget its exact source, retained raw history inspectable but source/note absent from subsequent model prompt; recall does not reproduce unique fact. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-06 | yes | Status response reflects canonical state; cancel blocks late result; pause/resume and bound input-resume work exactly once. Deterministic fault tests plus actual UI control/status evidence, not model state claims. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-07 | yes | Explicit real-provider UI requires fresh official Pro proof and bounded call budget; expiry/exhaustion/auth failure visible, no fallback, mock never silently substitutes live. Default startup stays mock. | [actual functional evidence](evidence/functional/2026-10-07/README.md); [66-test suite](evidence/tests/real-functional-full.txt) | PASS |
| F0-08 | yes | Direct human evaluation of real UI scenario set confirms conversation/recall/draft/correction usefulness; any failure remains inspectable and is fixed/retested. | [scoped original and revised human answers](evidence/final/stable0/human-evaluation.json); [final audit](evidence/final/stable0/audit.json) | PASS |

Final completion: every required S0/F0 row PASS with actual evidence, final full regression suite PASS, exact version/limitations, update STATE and master Issue #1. Long-term observation/sleep/auth refresh reliability remain explicitly unproven unless separately recorded. S0-13 is not a blocking row and remains historical unmet.

D-020 implementation regression: [65 tests PASS](evidence/tests/real-ui-bounded-green.txt) cover proof schema/replay/numeric forms/symlink, concurrent exhausted budget, expiry/rewind/sleep wall age, supervised shutdown during auth and startup contracts; [actual JS refresh PASS](evidence/tests/real-ui-refresh-green.txt). F0-07 structural checks pass; actual live host/banner still pending, so row remains not_run pending complete evidence.

2026-10-07 fixed F0-01–07 evidence complete: [actual official outputs, host checks, controls, source-context reconstruction and browser Send](evidence/functional/2026-10-07/README.md). F0-08 remains human_pending, so Stable-0 incomplete. Automated browser input is explicitly not human input. No long-term PASS claim.

Scheduled follow-up found a test observer race, preserved [red](evidence/tests/native-failure-wait-race-red.txt) and corrected terminal-state observation without changing production/criteria. [66-test full suite PASS](evidence/tests/native-failure-wait-green.txt), [20 repeated failure cases PASS](evidence/tests/native-failure-wait-stress.txt). Functional evidence/status retained; F0-08 direct human evaluation remains pending.

2026-10-07 continuing development/human-judgment split: actual ongoing human thread verified; F0-08 remains human_pending, not inferred from continuation authorization. [Regression checkpoint](evidence/tests/development-handoff-full.txt). STATE.md identifies the evidence-bound handoff and only dependent completion work waits. No acceptance, production, provider proof or canonical-state change.

2026-10-07 direct human F0-08 answers received: [source turns and scoped answers](evidence/functional/2026-10-07/human-evaluation.json). Conversation improvement and grounded thank-you preferences are being reflected; original outputs preserved. F0-08 remains pending affected real-provider revalidation and confirmation.

Response-style revision ccfba35: [66-test full regression](evidence/tests/human-response-style-refined-full.txt). First real revalidation [FAIL retained](evidence/functional/feedback-20261007/result.json); prior F0 scenario PASS evidence remains historical baseline307058d, not proof of revised response behavior. F0-08 still pending revised live output review. No acceptance criterion was weakened.

Revised real response content checks [PASS on ccfba35](evidence/functional/feedback-20261007-02/README.md): direct-question conversation, host memory explanation and grounded2-sentence drafts. These are automated real-provider results; F0-08 awaits direct revised human usefulness confirmation.

Revised-output continuation audit: [owned host/read-only canonical invariants/evidence-link checks](evidence/functional/feedback-20261007-02/continuation-audit.json) and [66 tests PASS](evidence/tests/feedback-continuation-audit-full.txt). Human window has presented revised outputs; no direct revised verdict yet. F0-08 remains pending; no Stable promotion.

Revised evaluation blocked audit: F0-08 remains human_pending, with no direct revised-output verdict. [Current blocker and exact release condition](evidence/operations/revised-evaluation-blocked-audit.json). No acceptance criterion or PASS status changed.

## Final functional-first audit — 2026-10-07
All20 currently required S0/F0 rows PASS. [Controller audit, versions, source hashes, live artifacts/host bindings, read-only canonical invariants and historical chains](evidence/final/stable0/audit.json). [Final66-test full suite PASS](evidence/tests/stable0-final-full.txt). Direct human message `01a11475-3bd0-76c1-b980-806ec8cc8842` says 「合ってる」 about presented ccfba35 revised conversation/Cedar/Birch drafts, combined with prior recall/no-change and scoped answers. Historical pending notes above describe past checkpoints and are superseded. Historical S0-13 remains unmet/nonrequired; no long-term stability claim. Final Issue/repository completion recording follows this audit.

Stable-0 controller completion: all required rows PASS, final66 tests PASS, version/limitations recorded, [master Issue CLOSED/completed](https://github.com/thattor/personal-agent-lab/issues/1). [Completion receipt](evidence/final/stable0/completion.json). Stable-0 declared under D-019; no historical soak promotion.

## Stable-1 current acceptance — D-021 / D-031

D-031 reflects the owner's2026-10-08 direct priority change, not a retroactive test PASS.
Further conversation/prose-quality tuning, tests and reviews are stopped. Minor reversible
local-output defects remain known limitations. Original fixed40/independent12 and absence
probe results retain their original status; their repeated complete requalification is no
longer a release gate. No80% numerical quota is introduced. Functional target/authority/cost/
reference-stop/recovery/completion requirements and one actual overall owner evaluation remain.
Original ABS-A2 stays NOT_VERIFIED and must not be accessed/retried/replaced; its quality-only
second-sample requirement is withdrawn. [Direct authority and retained results](evidence/reviews/judgment-boundary/c060-grounding-results/README.md).


These rows define the NEXT release, not Stable-0. All begin NOT_RUN. No old PASS or human evaluation transfers to a new behavior. Freeze scenarios and expected results before implementation; retained failures and affected evidence must be revalidated after changes. Passing a finite corpus does not promise arbitrary-language correctness. No time/turn/session quota.

C042 current product is `content:sha256:c55cab29e61bc024ad67f1f5b6b6bd0f07c140b9a6190ec6f8d57202dabf71b5`; official Opus reviewed current-authorization precedence before the Primary-only edit. [Product freeze](evidence/reviews/judgment-boundary/primary-intent-limits-candidate-freeze.json), [75 focused tests](evidence/reviews/judgment-boundary/intent-limits-targeted-green.txt) and [249 full tests](evidence/reviews/judgment-boundary/intent-limits-full-green.txt) PASS. C043 first-attempt fixed40 now PASS16/16 requests and zero unwanted Goals/24 nonrequests with independent audits; independent12 PASS5/5 legitimate delegation opportunities, zero false-positive Goals, with independent read-only audit. [Post-live249 full tests](evidence/reviews/judgment-boundary/intent-limits-c043-full-after-live.txt) PASS20.244s. C039 product7c284733 passed16 requests but [FAILS N22 compound-send](evidence/reviews/judgment-boundary/clarification-run-n01-n24/README.md). C041 product60df1d0e [FAILS N17 record-only](evidence/reviews/judgment-boundary/compound-run-n01-n24/README.md):16 negatives PASS, one unwanted queued Goal, N18–24/requests/independent12 NOT_RUN, no worker/artifact/external effect. These failures and unused cases remain historical; no old PASS transfer. Unchanged host/security/recovery evidence retains its scope and cannot certify changed model behavior.

C063/D032 current candidate is product04f30387: only native duration, startup option and
visible deadline change from C061/e851cae0; Primary/Expert/context/canonical/control source
is unchanged. [Scoped evidence and277 full tests PASS](evidence/reviews/two-hour-trial/validation.json).
Startup freshness and one-use proof stay900 seconds; the owner-requested trial may use
explicit8100-second admission with its actual remaining call budget unchanged. This does
not mark owner usefulness PASS or imply2 hours of observed runtime. [Actual same-DB/URL
launch and UI deadline](evidence/operations/c063-preview-launch.json) carry16 unused calls
and record8007 seconds remaining at handoff; proof is valid until2026-10-08 23:37:26 JST.
Human use/evaluation remains pending and separate from these runtime facts. No quality rerun.

| ID | Required for Stable-1 | Acceptance | Evidence | Status |
|---|---|---|---|---|
| N1-01 | yes | Model-led natural local requests can create appropriate work; a meaningful missing-purpose question can lead to work from the answer. Record unwanted but reversible local draft creation as a known limitation; external execution or false external-completion claims remain prohibited. Report finite observed behavior and known limitations; the historical40-input recall/quota and repeated quality requalification are not release gates after D031. | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PASS (D031 functional scope; finite evidence) |
| N1-02 | yes | Retain independently prepared actual-model observations, disclosure/freeze provenance, request recognition and unintended-action findings. D031 requires an honest finite capability report, not further quality samples or a repeated perfect corpus. | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PASS (D031 functional scope; finite evidence) |
| N1-03 | yes | For0–3 Goals in mixed queued/running/waiting_input/completed/cancelled states, natural correction/cancel resolves uniquely or requests target selection without mutation. Zero wrong-target mutations; stale/cross-target answers cause no mutation and visible explanation. Fixed criteria unchanged | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PASS (D031 functional scope; finite evidence) |
| N1-04 | yes | Process kill during pending target selection and during correction recovers bindings with no duplicate Goal/artifact/report; existing epoch fencing, ingress dedupe and transactional outbox remain effective | [Six actual selector/correction SIGKILL boundaries, replay/outbox and atomic migration](evidence/reviews/stable1-targets/README.md); [91 tests PASS](evidence/reviews/stable1-targets/selection-final-full.txt); [current D029 Primary target/correction SIGKILL and replay](evidence/reviews/judgment-boundary/primary-target-crash-current.md),25 targeted tests and [234 integrated tests PASS](evidence/reviews/judgment-boundary/recognition-suffix-full-green.txt). Model responses in crash tests are scripted; actual SIGKILL and host/runtime recovery observed | PASS (current D029 host/runtime) |
| N1-05 | no (D031) | Fixed planted-absence draft probes contain no fabricated recipient/date/contribution; explicit placeholders or a conversational question are acceptable. Context-supported facts and requested constraints retained | [Corrective candidate605791e: all six fixed real samples PASS; supported facts/constraints retained](evidence/functional/stable1-20261007-run2/README.md). [Original unsupported-outcome FAIL retained](evidence/functional/stable1-20261007/README.md); D026 reviewed correction, finite proof only  [C044 current actual absence FAIL and independent adjudication](evidence/reviews/judgment-boundary/ui-c044-absence-failure/README.md): unsupported future-announcement promise, integrity PASS. Expert-only correction product53a616 reviewed; [249 full tests PASS](evidence/reviews/judgment-boundary/c044-full.txt), [C045 ABS-A1](evidence/reviews/judgment-boundary/ui-c045-partial/README.md) PASS with actual artifact/UI/receipt and independent audit. ABS-A2 NOT_VERIFIED after browser-client block; four remaining absence samples NOT_RUN. Historical passes do not replace missing current proof; original FAIL retained. | PARTIAL / historical FAIL retained; NONBLOCKING quality limitation |
| N1-06 | yes | Actual Japanese UI flow covers request recognition, unambiguous and ambiguous target resolution, correction and cancellation on an official real provider within fresh D-020 proof/budget; actual host/artifact evidence, no extra credits/renewal/fallback or model self-attestation | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PASS (D031 functional scope; finite evidence) |
| N1-07 | yes | One direct human whole-flow usefulness evaluation of the working version: understands usable requests, changes/stops the intended work and provides usable local output. Keep feedback visible; minor reversible wording/content-quality imperfections may remain known limitations under D031. Do not substitute a wording exam, test count or continued-development instruction for actual evaluation. | [HR-STABLE1-001 version-bound frozen materials](evidence/functional/stable1-20261007-run2/human-material.md), candidate605791e; actual positive output/control feedback plus later missing-information mismatch received. [Direct source turns and scoped interpretation](evidence/operations/human-feedback-received-20261007.json). [Current actual whole-flow material](evidence/reviews/judgment-boundary/ui-production-run/human-material.md) delivered once; [handoff and presentation receipt](evidence/operations/c035-human-handoff.json). [Current candidate75dc0e3/producte851cae0 real owner preview and actual handoff](evidence/final/stable1/owner-preview.json); no synthetic owner input. [C062 owner access report and same-DB/URL bounded restart](evidence/operations/c062-preview-restart.json); actual owner access/use still unconfirmed. [C063 requested two-hour trial](evidence/operations/c063-preview-launch.json), candidatea433787/product04f30387, was launched with unchanged16 calls and actual deadline. C064 subsequently stopped the host and preserved the DB under the owner pause/design-rebuild direction. [C064 direct owner feedback](evidence/operations/c064-owner-value-gap.json) rejects the draft-only candidate as sufficient PAL usefulness while accepting necessary component tests. The answer is received; do not repeat this evaluation. | FEEDBACK_RECEIVED / usefulness not accepted |
| N1-09 | yes | P002 functional clarification: bounded usable context, essential question and valid answer can continue intended work; ambiguous/stale/forgotten answers cannot resume the wrong work. Persist source/question bindings and visible incomplete outcomes with unchanged criteria, dedupe/recovery and cost limits. Retain actual-model/UI evidence and whole-flow human evaluation; no further prose-quality perfection/requalification gate under D031. | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PARTIAL (functional evidence PASS; N1-07 usefulness not accepted) |
| N1-10 | yes | D029 model-led Primary handles conversation, draft delegation, target/answer selection, correction, memory and reference-stop proposals. Host enforces closed actions, live snapshot/source/revision/epoch, fixed criteria and idempotent effects; structured controls remain immediate, with no lexical preemption or silent fallback. Use retained/current finite actual-function evidence; no further conversation-quality qualification loops under D031. Qwen3.8-27B remains a reference, not a tested PAL capability. | [Current function proof](evidence/reviews/judgment-boundary/c061-target-function/README.md); [C060 finite actual observations](evidence/reviews/judgment-boundary/c060-grounding-results/README.md); unchanged host and previous actual-function evidence scoped in [candidate audit](evidence/final/stable1/audit.json). Original quality FAIL/NOT_VERIFIED/PARTIAL retained under D031; no new perfect-language claim. | PASS (D031 functional scope; finite evidence) |
| N1-08 | yes | Full regression and affected S0/F0 behaviors revalidated on the release candidate, no weakened criteria/security/forget/lease semantics; final version/limits/evidence audit, next milestone parent Issue closure and private release record | Candidate full suite/version/boundary audit prepared in [release evidence](evidence/final/stable1/audit.json); [C063 duration/UI delta and277 full tests](evidence/reviews/two-hour-trial/validation.json) revalidate the changed provider boundary; C064 owner answer received with a material value gap; final Issue/release closure remains open. | PARTIAL (usefulness gap / release closure incomplete) |

[P-002 v1](docs/plans/P-002-v1.md) / HR-SCOPE-001 proposes moving only essential local-draft clarification into Stable-1. Official Opus agrees; conditional no-extra-cost realization direction is received from the human and feasible in the current architecture per official SWE supplied-source review. [Activation receipt](evidence/reviews/feedback-alignment/scope-activation.json). N1-09 is now required; implementation/live/functionality proof remains pending. Existing N1-07 feedback remains unresolved.

The broader content workflow remains a later candidate; only P002 essential local-draft clarification is now within Stable-1. N1-03/04 target-selection questions do not claim that broader feature. Before substantial implementation, obtain the required official SWE-2 High contract review. Host-visible target choices must be bound/persistent rather than raw model controls; exact representation remains an implementation-review decision.

## Project goal acceptance proposal — P-001 v1 / D-022

Not new Stable-0 or Stable-1 gates. G-P01–04 remain prospective NOT_RUN until actual human plan adoption; definitions and stage dependencies are frozen in docs/plans/P-001-v1.md. GitHub goal Issue#6 aggregates milestone results but requires its own integrated proof and authentic human usefulness before completion. Per-Issue and per-milestone objective gates/limits freeze before implementation; counts/closed children alone do not prove parent completion. N1-01–08 criteria remain unchanged; P002 separately adds N1-09 within the adopted cost boundary. Material plan/acceptance changes require Opus agreement and actual human finalization.

P002 current limitation: legacy diagnostic `_wait`/input at total-claim9 behavior remains unchanged and can strand queued work. New clarification atomic question-or-preview integration is still pending; terminal Store unit tests do not claim that dispatch or whole N1-09 PASS. Fixed preview byte limits remain enforced.

C010 partial N1-09 unit proof: [full121 PASS](evidence/reviews/feedback-alignment/dispatch-full-final.txt), [targeted22 PASS](evidence/reviews/feedback-alignment/dispatch-targeted-final.txt) verify atomic Store question-or-preview dispatch, concurrent replay and SIGKILL rollback. Earlier atomic-dispatch pending note is superseded for Store only; runtime/source/UI/live/human integration remains NOT_RUN. Legacy diagnostic/global9 behavior unchanged.

C011 partial N1-09: [full124 PASS](evidence/reviews/feedback-alignment/citations-full-final.txt), targeted25 PASS demonstrate write_draft's in-transaction optional literal citation check: exact manifest ID, prefixed note ID, stored sanitized substring, malformed/unavailable citation rejection and forget-before-apply no bytes. Runtime not using structured citations; question/preview checks and bound answer context/UI/live/human proof still pending. No semantic truth/completeness PASS inferred. Official runtime-swe review completed exit0, findings recorded D027; no paid fallback.

C012 partial N1-09 evidence: [claim/source/citation full regression127 PASS](evidence/reviews/feedback-alignment/bindings-full-final.txt); [targeted28 PASS](evidence/reviews/feedback-alignment/bindings-green.txt). Bound actual answer source remains available after recent30 truncation; forgotten answer text excluded. Question/preview citations reject before canonical effect. This is deterministic Store proof only; runtime/UI/live/human requirements remain unfinished, whole N1-09 NOT_RUN.

C013 partial N1-09 runtime evidence: [134 full tests PASS](evidence/reviews/feedback-alignment/runtime-envelope-full-final.txt), [15 runtime tests PASS](evidence/reviews/feedback-alignment/runtime-envelope-targeted-final.txt). Disposable scripted-provider restart/answer/exhaustion and negative authority/source tests prove host application paths, not live-provider usefulness. Template intake/UI/live/human proof unfinished; N1-09 NOT_RUN.

C014 template intake partial evidence: [137 tests PASS](evidence/reviews/feedback-alignment/template-intake-full-final.txt). Eligible blank-template flow remains failed/incomplete_template with preview receipt, never completed; correct refreshes flag while old revisions remain unchanged. UI/live/human requirements unfinished; N1-09 NOT_RUN.

C015 partial N1-09 UI/HTTP evidence: [139 tests PASS](evidence/reviews/feedback-alignment/question-ui-full-final.txt); [actual shipped JS synthetic DOM/HTTP proof](evidence/reviews/feedback-alignment/question-ui-js-green.txt). Five bound waiting forms, no diagnostic phantom form, draft retention, exact answer payload, stale suppression, preview/reference-stop labels. Actual HTTP wrong epoch unchanged Store, valid bound input same Goal, readonly artifact-status/retained bytes proven. Not actual browser/human/live proof. Required finite actual scenarios and human re-evaluation remain; N1-09 NOT_RUN.

C016 partial N1-09 Runtime recovery: [140 full tests PASS](evidence/reviews/feedback-alignment/runtime-question-crash-full.txt), [actual process death at three question transaction boundaries](evidence/reviews/feedback-alignment/runtime-question-crash.txt). One Goal/question/receipt/completion, replay without duplicates. [Finite six-case actual-provider matrix](tests/fixtures/p002_real_ui_v1.json) frozen NOT_RUN; synthetic test inputs never human attestations. Whole N1-09 NOT_RUN; no prior PASS transfer. P001v2 remains unadopted proposal, G-P rows prospective.


C017: controller mapped every frozen P002-LIVE-v1 case to deterministic tests and remaining actual-provider/UI evidence in evidence/reviews/feedback-alignment/live-coverage-audit.md. Fresh full140 PASS11.881s in live-preflight-full-authorized.txt. Restricted first run retained10 HTTP setup EPERM errors at loopback bind, same suite succeeds on approved escalation; no product code/criteria changed. Next run HTTP suite on approved loopback-capable execution path, preserving failed environmental evidence. Official SWE exec82542 confirmed still live; same-handle wait, no restart/new reviewer call. Matrix remains NOT_RUN, no live/usefulness PASS, no old host/DB write. Exact next: terminal SWE contract verdict, record reconciled contracts then harness tests/implementation; HR-PLAN-001 adoption and HR-INPUT-001 semantics stay independent.


C018: disposable scripted-provider audit on a81b930 reproduces a P002 template boundary defect: complete proposal containing literal {{date}}/{{place}} becomes completed with draft receipt and pass outcome despite adopted unresolved-placeholder preview requirement. evidence/reviews/feedback-alignment/template-complete-audit-terminal.json preserves request/revision/Goal/receipt/outcome/artifact. Not actual-provider/human evidence. Initial idle-event observation was inconclusive; second observer mistakenly read receipt.id as artifact ID; final observer uses canonical terminal polling and receipt.artifact_id verified against Store source. These observer mistakes and their prevention are retained. No runtime code or old DB changed. Exact next: await live SWE82542 terminal verdict, reconcile this concrete finding with official Opus/implementation review before the smallest host-boundary repair and regression test; do not execute the live matrix or weaken T1. Goal ACTIVE; human plan adoption remains independent.

C019: official SWE891.688s and Opus84.236s reviews TERMINAL completed. Adopted eligible-template literal floor now rejects reserved brace/underscore markers (NFKC check only, stored bytes unchanged) before draft bytes/receipt and defensively before completion; immutable attempt revision eligibility, prior outcomes and noneligible literal-code behavior retained. Prompt routes unresolved eligible templates to preview. Test-first red/green; five boundary tests include actual Runtime visible rejection/no completion, preview path, marker families, old-receipt defensive check, filled/noneligible/corrected revision. Gated shared-provider test helper implemented with one per-input permit, no-op borrower stop, owner-only idempotent stop, total20 cap, denied retry/concurrency/expiry/late-return/invalidUTF8; seven tests, no real provider calls. Full152 PASS11.763s in gate-template-full-final.txt. Full151 earlier failure was independent response-lane observer race; original output retained, await response Future and quiesce both lanes before whole-store outbox replay assertion, targeted SIGKILL test green. No product concurrency change or historical DB repair. Full live harness, watchdog/journal/source freeze/browser cases still pending; no live/usefulness PASS. P003v1 notice-only bare answer PROPOSED hash79859419dbf29b3579cfe6e2ac3452c64246d30c71bf74f79a507c4e63258bfd, requires HR-INPUT-001 authentic grammar/notice confirmation; shortcut unchanged. Exact next: implement reviewed fsync journal/watchdog/finite runner contract tests, freeze candidate and run fresh bounded real/UI matrix; receive separate P001v2 and P003 decisions without duplicate questions. Goal ACTIVE, Stable1 incomplete.


C020: reviewed test-run evidence/watchdog infrastructure implemented. EvidenceJournal uses exclusive no-follow creation (never overwrite/resume), owner-only scripted/live_synthetic scope, sanitized strict finite JSON, bounded fsync per-record hash chain, read-only tamper/truncation/duplicate-key verifier and failed-write no-repair policy. RunWatchdog monotonic deadline calls shared gate owner close_run and exposes callback errors, join bounded. Seven tests PASS0.322s: concurrent chain, unsupported human attestation, existing/symlink refusal, malformed/oversize payload with unchanged bytes, chain tamper/truncation/duplicate rejection, cancelled/expired watchdog, actual harness SIGKILL with retained fsynced call-start prefix and owned native fixture termination, actual in-flight native fixture killed by deadline with retained failure chain. No official provider generations, authentication, production/old DB changes or human evaluation. Integrated first run found call sequence/journal sequence collision; call_sequence correction and failed evidence retained in live-evidence-integration-red.txt/docs DEFECTS, no blind live retry. Full159 PASS12.001s live-evidence-full.txt. This proves test infrastructure, not live matrix or release. Exact next: test/implement finite runner loading frozen6-case P002-LIVE-v1, source/model/config/harness hashes, one consumed operator proof/Native20 owner, serialized phases/explicit bound answers, canonical observations+artifact readback, fail-stop and owned host teardown; then fresh bounded real UI proof. HR-PLAN-001/HR-INPUT-001 actual answers still pending independently; no duplicate questions. Goal ACTIVE.


C021: finite fixture runner assembly implements the frozen six-case sequence on six distinct disposable loopback stores, one shared gated owner, source/harness/fixture hashes, one permit per input phase, canonical state/question/outcome checks, artifact hash/size/role/read-status readback, same-Goal bound answers, reference-stop prompt exclusion, fsync captures/controller observations and fail-stop teardown. Five runner tests and full164 PASS; evidence/reviews/feedback-alignment/live-runner-full-final.txt. Fixture scope only: live_synthetic rejected before run-directory creation until operator proof/Native/config/process observations are integrated. No official generations, old runtime/DB writes, human evaluation or acceptance promotion. Next independent action: complete reviewed operator entry point with exact clean candidate/config/version freeze, externally observed fresh AccessProof consumed once, Native20 shared owner and supervised subprocess accounting; then actual owned UI fixed real cases. HR-PLAN-001/HR-INPUT-001 actual owner decisions remain pending independently; latest human-thread read contains presentation/acknowledgment only. Goal ACTIVE, Stable1 incomplete.


C022: reviewed live operator integration implemented, full167 PASS15.806s (evidence/reviews/feedback-alignment/live-operator-full-green.txt). Explicit python -m scripts.live_operator requires exact clean candidate, fresh externally observed AccessProof, shared runtime/native-proof-use one-use marker and audited Native20 owner. Frozen command/CLI/Python metadata, source/harness/matrix hashes and proof remaining-age deadline recorded; real supervisor start/finish and native slot attempt separated from gate calls, never CLI-grandchild/token telemetry. Serial stdin next/capture/accept/finish supports actual owned browser UI input; no automatic fabricated human inputs/evaluation. Direct live runner rejects unaudited owner, unconsumed operator path and already-claimed owner. Three operator tests and five matrix tests use fixtures only; no official generation or authentication performed. Prior full167 failed because controller edited live_operator.py while source-frozen runner test was active: preserved live-operator-full-final.txt, correct fail-stop detection; source unchanged throughout final green run. Exact next: refresh existing official authenticated usage/extra-OFF and scrubbed CLI proof, freeze pushed C022 exact candidate, launch one new owned runtime matrix directory through operator, use actual UI for six frozen synthetic cases and stop on first failure. After real evidence, receive actual N1-07 usefulness evaluation and pending scoped HR-INPUT-001 decision; final N1-08 audit remains unfinished. HR-PLAN-001 future adoption independent, no old soak/quotas/schedule restart. Goal ACTIVE; Stable1 incomplete.

C023: actual frozen P002-LIVE-v1 UI matrix on pushed candidate57b4a49 completed all six controller-observed cases, nine official generations in339.574s, fresh existing Pro/extraOFF one-use proof, no paid fallback/new auth/resampling. 79-record fsync journal verified; nine auth/nine generation supervisors returned0; all six owned loopback ports closed and retained DBs read-only integrity_check/receipt uniqueness OK. Full167 PASS16.614s after live run. Evidence/reviews/feedback-alignment/live-c022/README.md and audit.json. Actual output bytes and UI observations retained; controller synthetic inputs are not human inputs/evaluation. T1 observer URL typo404 and premature HTTP-readback wording corrected transparently by read-only retained-DB stale/body-hash audit; old journal not rewritten. A1/P1/F1 optional event-kind cue and G1 fictional attendance language visible for human rubric. N1-09 PARTIAL, not PASS: known unsafe bare-answer shortcut pending HR-INPUT-001/P003, actual human re-evaluation and release regression still incomplete. Exact next: deliver version-bound revised material to the existing human window without duplicate questions; receive HR-INPUT-001/HR-STABLE1-001 actual answers and implement/retest only adopted delta; meanwhile audit remaining final-candidate regression coverage for independent gaps. HR-PLAN-001 P001v2 future adoption independent. Goal ACTIVE; no Stable1 declaration.

C025: independent operator failure cleanup fixed within the reviewed harness contract. Injected operator.config append failure reproduced missing runner.close; injected terminal evidence failure reproduced skipped watchdog/host teardown. Nested finally now attempts each owned cleanup stage even when an earlier stage raises; no failed journal repair or PASS inferred. New tests patch startup/cleanup collaborators (no official auth/provider call) and assert cleanup attempts and visible exception; existing actual synthetic process tests remain separate evidence. Full169 PASS15.399s: evidence/reviews/feedback-alignment/operator-cleanup-final-full.txt; both failing tests retained in operator-config-cleanup-red.txt and operator-terminal-cleanup-red.txt. Initial168-test suite after the first fix is intermediate, not final. Routine local failure-path repair preserves accepted teardown design and requires no new design adoption/substantial implementation review. Product code/grammar and old runtime evidence unchanged. Current harness source differs from C023 frozen hashes; C023 stays historical candidate57b4a49 evidence, never transferred to a new final candidate. Latest human thread remains idle with only agent acknowledgment; HR-INPUT-001/P003 and HR-STABLE1-001 actual owner answers pending. Next: receive version-bound decisions, implement/retest adopted delta, then freeze final candidate and perform affected real regression/full release audit. P001 future activation remains separate. Goal ACTIVE; Stable1 incomplete.

C026: constructor initial run.started failure now closes the fully initialized runner; initialize teardown fields before starting watchdog, and wrap watchdog start/initial append in cleanup-on-error. Pre-fix injected write failure proves provider.stop was not reached; source inspection shows watchdog/journal acquired before that raise. Green test uses actual EvidenceJournal and RunWatchdog (scripted provider only), proving one provider stop, zero generations, closed fd, stopped real thread and unchanged empty evidence file. Full170 PASS15.236s: evidence/reviews/feedback-alignment/runner-startup-cleanup-full.txt; failing reproduction retained in runner-startup-cleanup-red.txt. Routine correction within existing reviewed lifecycle contract, no product/design/criteria change or new consultation required. It does not prove arbitrary earlier constructor failure, actual disk exhaustion, or official-provider behavior. C023 frozen real evidence remains candidate57b4a49 historical; changed harness requires a fresh freeze for subsequent actual runs. Human thread idle/latest terminal agent acknowledgment unchanged; no authentic P003 or usefulness answer. Next: adopt only incoming version-bound owner decisions, implement approved grammar delta then final candidate affected functional/regression/release audit. No further independent required slice identified; do not create extra harness work or unchanged test repetitions to avoid judgment wait. Goal ACTIVE; Stable1 incomplete.

Post-C026 blocked audit: three consecutive automatic goal continuations found the same idle human thread and terminal agent acknowledgment01a1160c, with no authentic HR-INPUT-001/P003 or HR-STABLE1-001 answer. This is no progress, not a verified live-process wait. C025/C026 independent fixes are completed/pushed; release-coverage audit identifies only judgment-dependent final work. Evidence: evidence/operations/stable1-c026-judgment-blocked-audit.json. Goal to BLOCKED under the three-turn rule, objective unchanged; Stable1 and overall project incomplete. Release: receive an authentic version-bound owner decision/evaluation in the ongoing human thread, then record/adopt its exact scope and resume corresponding implementation/retest or evaluation, followed by final candidate affected regression/live audit. P001 future adoption and Projects authorization remain separate. Last full170 PASS15.236s retained; no source change since that suite, so no redundant rerun for this documentation-only checkpoint. No repeated question, schedule restart, provider renewal/call or canonical write.

D028/D029 checkpoint: invalid HR-INPUT form-only/wording wait withdrawn after authentic owner feedback and official Opus review. Stable1 remains incomplete; one end-to-end actual human evaluation and final audit are unchanged. Prior N1 PASS evidence is historical to its candidate; changed Primary architecture requires affected release regression. Qwen model-card existence is not PAL performance proof. No old quota or scheduled wake restored.


C030 N1-10 partial verification: separately reviewed finite Primary-only harness ready;
[15 targeted checks](evidence/reviews/judgment-boundary/qualification-targeted.txt),
[211 full tests PASS18.056s](evidence/reviews/judgment-boundary/qualification-full-final.txt).
Pre-disclosure product freeze1a14de9/corpus hash retained; no model-prompt tuning after
oracle disclosure. Native24/one-use proof/remaining-proof deadline/no resume, raw-proposal
retention, exact fixture and offered snapshot, judged-before-next and read-only journal
verification covered. Original observer failure and20-repeat fix evidence retained.
These are infrastructure/host tests: actual Primary semantics, revised UI/Expert function,
Qwen capability and N1-07 usefulness are not PASS. Existing named acceptance unchanged.

C034 actual production path: candidatea1ba755/product1a14de9, four synthetic UI inputs,
six official native slots, two distinct completed Goals/Attempts/host receipts. Actual
artifacts opened from UI links and matched HTTP bytes/hash, source unchanged, owned
host stopped normally; full213 PASS18.510s. Not human inputs/usefulness or Qwen proof.
Current required rows remain unpromoted pending one whole-flow evaluation and final
audit; no obsolete quota or new formatting gate. See ui-production-run evidence.

C044: Expert-only grounding instruction corrects an observed unsupported future promise;
current N1-05 affected actual revalidation remains NOT_RUN after original FAIL. C043
N1-01/02 stay scoped PASS on their unchanged Primary/host components and old version
bindings, not new-candidate measurements. No whole-row semantic/human/release PASS
from deterministic tests or reviewers. New product manifest, unchanged-component audit
and bounded affected UI contract are in judgment-boundary/expert-commitment-*.json.

C045: corrected-candidate actual partial UI evidence archived in ui-c045-partial/. Three host cases PASS, one NOT_VERIFIED, one VOID, nine NOT_RUN;10 slots, five normal bounded teardowns. Full249 PASS20.122s. No whole-row/human/Qwen or release promotion. Next independent work is reviewed deterministic scheduling at the existing fault seam for actual cancellation proof; no blind timing retry or browser-block workaround.

C046: official Opus87.439s reviewed a possible existing-fault-seam controlled-delivery probe, preserving natural-timing VOID results. Required official SWE-2 High implementation review could not start: authenticated Free model verified, but CLI refused the untrusted workspace. HR-ACCESS-002 records the exact owner action/release condition; no bypass or implementation. No acceptance row promoted;249-test green and17 product hashes unchanged.


C047 infrastructure: actual HR-ACCESS-002 reply and successful official SWE-2 High Free
review resolve the workspace-trust dependency. Reviewed controlled-delivery operator
uses the existing worker fault seam; no product source change. [19 focused tests](evidence/reviews/judgment-boundary/c047-probe-focused-final.txt)
and [268 full tests PASS24.048s](evidence/reviews/judgment-boundary/c047-full.txt), independent
Astra race review and frozen cap3/600s contract recorded. Actual controlled cancellation
NOT_RUN at this freeze; no N1 row or human/Qwen/release status promoted. Original C045
partial/VOID/block evidence remains immutable.

C047 actual controlled-delivery cancellation now scoped PASS on c44d3b4/product53a616:
[actual UI, six-event chain, zero accepted effects and independent audit](evidence/reviews/judgment-boundary/c047-controlled-cancel/README.md).
Three slots, two frozen controller inputs, bound stale-artifact rejection, normal200.824s
teardown/exit0 with explicit ECONNREFUSED and PID-exit evidence. No product changes since
268-test full PASS. This fills one controlled cancellation subproof only; N1-06/10 remain
PARTIAL, N1-07 usefulness and final release audit remain incomplete.

C048 operational blocked audit: same residual browser artifact-access condition observed
at C047 exit and two automatic continuations; no new supported clearance/human response
or independent required slice. Goal BLOCKED with objective unchanged. Existing N1 states
and268-test evidence remain unchanged; no new test, provider call, PASS or release claim.
See evidence/operations/c048-blocked-audit.json.

C049 browser-block investigation: retained screenshot/source and official guidance
reviewed. Cause UNKNOWN; native-settings and chrome://policy reads refused, no bypass.
HR-ACCESS-003 asks only for visible Browse permission values; private support draft
prepared, not sent. No new model run, code/test change, acceptance promotion or access
clearance. [Investigation](evidence/operations/c049-browser-block-investigation.md).

C050 operational reconciliation: HR-ACCESS-003 answered and source image checked;
default Browse allows access but the original client block remains unexplained.
[Recorded response, three-chat authority and formal support handoff](evidence/operations/c050-access-and-continuation.md).
No model/UI rerun, canonical database write, product/test change, access clearance or acceptance
promotion. New 50-minute checkpoint NOT_CONFIGURED until noninterrupting delivery is
established; old schedules remain PAUSED. Existing 268-test green evidence remains bound
to unchanged source. Stable1 real functional/usefulness/final-release gates remain open.

C051 consumes the actual HR-ACCESS-004 answer: do not send Support; investigate a safe
alternative. The contract requires real UI/artifact observation without mandating a
named automation tool; no substitute proof is adopted. Current IAB transport is also
unavailable; opening an official public help page is queued, not displayed/cleared.
[Requirement/evidence map and scoped alternatives](evidence/operations/c051-alternative-validation.md).
Original C045 NOT_VERIFIED, all row statuses and finite budgets remain unchanged.
Official Opus review and controller reconciliation now preserve a bounded A0/known-
fixture diagnostic route and distinguish nine independent NOT_RUN first cases from
resampling ABS-A2. Static diagnostic preparation is checked, browser execution NOT_RUN.
HR-ACCESS-005 display is now confirmed, but one post-answer tool inventory still has no
IAB. No diagnostic/model run or promoted row; a prospective manual observer protocol is
being specified separately, without changing current criteria.
Even successful remaining first cases cannot erase the unverified second A-sample.

C052 specifies the equivalent human-operated main UI and development-side observation
method for only the nine untouched cases. Exact actual links/URL, receipt/body hash and
canonical identities must agree; original inputs/oracles/caps/first outcomes remain.
[Procedure and provenance](evidence/operations/c052-manual-observer/README.md).
No case has started or been promoted. HR-UI-001 asks actual availability for the first
one-input case, not a new technical approval or usefulness PASS. No product/test changes.

Subsequent owner correction supersedes that operation request: HR-UI-001 is withdrawn,
no manual-input/receipt or readiness wait remains. Development owns technical checks
through the existing supported browser connection, preserving all original real-UI/
host/semantic obligations. [Evidence reuse, real remaining risks and next operation](evidence/operations/c052-technical-verification.md).
This does not change any acceptance row or count an unexecuted test as PASS.

C053 actual independent UI subproof: CREATIVE-PARTICULARS and SUPPLIED-FOLLOWUP first
attempts PASS on pushed1af0501/product53a616, four native slots total. Both actual
Chrome UI links/body displays match exact HTTP bytes and host receipts; no unnecessary
questions, invented forbidden logistics or external effect. Owned hosts exited normally
within600s. [Evidence](evidence/reviews/judgment-boundary/c053-ui-chrome/README.md).
Seven untouched cases and original ABS-A2 second-sample gap remain; no whole N1 row,
owner usefulness, Qwen capability or release promotion. HR-UI-001 remains withdrawn.

C054 actual UI/context subproof: ABS-B1/B2/C1/C2 first attempts PASS, two general-gratitude
and two supplied-context samples,10 slots total, four bounded normal exits. Actual
rendered artifact bodies match receipts, and context source membership is verified.
[Version-bound evidence](evidence/reviews/judgment-boundary/c054-ui-context/README.md).
Three untouched UI flows, original ABS-A2 gap, owner usefulness and final audit remain;
no whole N1 row is promoted. Full268 C053 evidence applies to unchanged code/tests.

C055 actual UI-CLARIFY first attempt FAIL: explicit ask-first logistics were replaced
with placeholder drafting and completed before any answer; unsupported “soon” timing
also appeared. [Original state/artifact/receipt/stop](evidence/reviews/judgment-boundary/c055-ask-first-failure/README.md).
Two of three native slots used, no second input/retry/canonical repair. N1-09/10 are
FAIL on this candidate; integrity receipts are not semantic proof. Remaining TARGET-C/
COMPOUND NOT_RUN; old component PASS, ABS-A2 refusal and owner evaluation remain distinct.

C056 reviewed ask-first priority repair: only Primary prompt changes; existing execution,
Store, Expert, capabilities and UI are unchanged. Independent12 is frozen before the
edit and disclosed after the17-file product freeze. [Review/adoption](evidence/reviews/judgment-boundary/c056-ask-first-review/RECOMMENDATION.md),
[77 focused](evidence/reviews/judgment-boundary/c056-ask-first-focused.txt),
[270 full tests](evidence/reviews/judgment-boundary/c056-ask-first-full.txt).
Semantic revalidation NOT_RUN onproduct8f0f5b75; no old Primary PASS transfer or relaxation.

C057 [actual repaired UI-CLARIFY](evidence/reviews/judgment-boundary/c057-ask-first-ui/README.md)
first attempt PASS on b99c22d/product8f0f5b75: one grouped question before Goal, one
fixed answer, one grounded actual artifact with receipt/bytes match.3/3slots,139.987s
normal owned-host closure. C055 FAIL retained; no whole N1/human/release promotion.

C058 first-attempt semantic revalidation on f00f3dc/product8f0f5b75 is **incomplete**.
[Original journals, responses and defect](evidence/reviews/judgment-boundary/c058-primary-revalidation/README.md):
English8 complete; N01–22 in-run PASS plus N23 independent post-run PASS, original
N run PARTIAL at900s, N24 uncalled. Japanese R09–14 PASS, R15 specification invents
a future sender contact despite correct intent/Goal; FAIL and stop. R16/new independent12
not executed. No worker/artifact/human evaluation. N1-01 remains PARTIAL; current
N1-02/N1-09/N1-10 are not qualified by these partial results. The preserved C057 UI
PASS does not override this subsequent specification defect. Focused official review
and minimum repair are next; no acceptance change or original ABS-A2 retry.

C059: one reviewed Primary source-grounding clarification is fixed as producte851cae0.
[Original Opus/adoption, independent freeze and implementation](evidence/reviews/judgment-boundary/c059-source-grounding-review/IMPLEMENTATION.md).
77 focused/270 full tests PASS; actual fixed40/new independent12/affected UI qualification
is NOT_RUN. The correction preserves original oracles and explicit promises/fiction,
without transferring older semantic PASS. C058R15 remains a specification FAIL, not a
request-recognition miss or a claimed failed artifact. No release row is promoted.
