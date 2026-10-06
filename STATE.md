# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
D-019 adopted functional-first Stable-0. S0-01–12 structural PASS revalidated; actual official F0-01–07 PASS with finite functional evidence and 66 full tests. F0-08 awaits one direct human usefulness evaluation of the prepared real UI outputs; no time/turn/session quotas. Historical S0-13 NOT PASS/nonrequired. Stable-0 incomplete.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote origin/main. Original supplied untracked workspace preserved. No old implementation/schema was reused; the accidental startup metadata inspection is explicitly recorded in docs/DEFECTS.md. Do not inspect it again.

## Last green increment
Actual official Japanese functional scenarios and controls PASS on runtime baseline307058d, evidence pushed in52b4ea6. [Functional evidence](evidence/functional/2026-10-07/README.md). Follow-up found a new test observer's unsupported idle-event completion assumption; corrected only that test to inspect terminal canonical Goal state. [66-test full suite](evidence/tests/native-failure-wait-green.txt), [20 repeated failure-case tests](evidence/tests/native-failure-wait-stress.txt), [cause/prevention](docs/DEFECTS.md). No production/runtime/probe changes, accepted-behavior changes or canonical repair. F0-08 still awaits the already-requested direct human usefulness evaluation; do not repeat it.

## Historical soak (stopped for approved development)
Soak01 retained after reproduced stale UI warning; soak02 retained and intentionally reset for the user's bilingual UI request. Both old DBs/hash chains/receipts stay intact. [Soak02 directly confirmed receipt and reset](evidence/soak/2026-10-07/soak02-human-and-reset.json). No old human counts/time/restart proof transferred. Bilingual UI only changes display text; fixed controls, canonical values, receipts and provider remain English. [55-test full suite](evidence/tests/ui-bilingual-full.txt), [actual refresh recovery probe](evidence/ui/recovery/bilingual-after.txt). Historical runtime/soak-20261007-03 started 2026-10-07T06:14:18.834450+09:00 from clean pushed baseline 1863ef2a3037b335fa6f257a8d6fd95fb44da9dc on port58500, monitor PID3322/app PID3324. [Fresh start and served bilingual UI](evidence/soak/2026-10-07/start-03.json).

## Exact next action
Human reviews the actual Japanese conversation/recall and Cedar/Birch two-sentence local drafts at http://127.0.0.1:58500/ and directly reports whether they are useful/expected, or identifies a concrete mismatch. This is F0-08 usefulness evidence, not renewed time/turn quotas or routine technical approval. On that reply, diagnose/fix/retest any mismatch; if accepted, final full suite/evidence/version/all-required-row audit and master Issue #1 closure. Do not mark Stable complete before that evaluation. No fake attestation.

## Acceptance status
S0-01–12 and F0-01–07 PASS; historical S0-13 NOT PASS/nonrequired. F0-08 human_pending. Master Issue #1 remains open.

## Human participation requirement
D-019 supersedes old time/turn/session quotas. Human confirmation of actual usefulness is required once for the fixed real-provider scenario set; scripted outputs are never human attestations. Previous receipts retained as honest historical host/control proof. No routine repeated participation or approval prompts.

## Deferred
PublicSearch, time wake, proactive topics, Dreaming, multi-Expert, vectors, local inference, automatic procedure updates, external push.

## Follow-up and pending user decision
Hourly current-thread audit registered as `pal-stable-0-soak-audit` (ACTIVE, failed-run notifications only), restricted to this checkout and existing soak; first scheduled execution observed at 2026-10-06T14:44:41.652900+00:00; [read-only audit](evidence/soak/2026-10-06/hourly-audit-01.json). It must be paused after verified completion or direct user cancellation. This operational audit is not a PAL scheduled-wake product feature.

The human has been asked whether to proceed with real typed UI sessions or request reconsideration of the human-use gate. Historical pending request, now superseded by the first direct human confirmation below. Original first action: enter one non-secret message at http://127.0.0.1:58500/, copy Session receipt JSON and explicitly confirm the input was human-typed in this chat. That first confirmation was received and registered; later sessions still require direct confirmation.

Session closing verification: full suite in evidence/tests/soak-start-full.txt. No runtime/probe changes since baseline c887c35; only docs/evidence updates, so the running clock remains valid. Prior synthetic UI host on port58487 stopped normally; its DB retained. Real soak host/monitor remain running.

## First goal-continuation audit
2026-10-06T13:50:31.174033+00:00: verified wait, exact monitor/app processes live and HTTP worker healthy; unchanged runtime/probe baseline; hash chain valid, no findings or repair; no UI ingress/attestation. Full suite 55 PASS. [Checkpoint](evidence/soak/2026-10-06/continuation-01.json). Previous turn made implementation/evidence progress; this continuation confirms the live wait, not Stable completion. Existing human-participation request remains pending; do not repeat it or synthesize an answer. Next action remains direct human receipt/attestation followed by normal draft/restart workload.

## Three-turn blocked audit
2026-10-06T13:52:37.644578+00:00: the initial implementation turn requested actual human participation; first goal continuation verified the live wait; second continuation again confirms no UI ingress/attestation. Same blocker across three consecutive goal turns. [Audit](evidence/soak/2026-10-06/blocked-audit.json), [55-test full suite](evidence/tests/soak-blocked-audit.txt). No useful autonomous implementation slice remains within accepted scope: S0-01–12 already PASS, and more fixtures/idle elapsed time cannot supply human turns, sessions, Goals or controls. Controller marks the thread goal blocked after this evidence push. This is not a Stable declaration or a PAL Goal-state mutation.

The exact monitor/app processes remain live and unchanged; local measurement and hourly operational audit remain active. Do not stop/restart/repair them merely because controller is blocked, do not self-attest and do not repeat the pending participation question. Release: human supplies the first actual UI receipt and explicit human-typed confirmation; then process it as described above and resume acceptance work. An explicit request to reconsider the human-use gate requires Opus review and a recorded accepted decision; no change is inferred from silence or automatic goal messages. Master Issue #1 remains open.

## First scheduled operational audit
2026-10-06T14:44:41.652900+00:00: first heartbeat received and executed. Exact owned monitor/app identity and live HTTP worker verified, unchanged runtime/boot baseline, all 15 hash-chain records valid, 13 measurements with valid cadence and latest age 186 seconds. Read-only canonical invariants PASS; no failure events, canonical writes or repair. [Audit](evidence/soak/2026-10-06/hourly-audit-01.json). This proves operational follow-up execution only; S0-13 remains in_progress/human_pending. Pending human question and exact next action above remain unchanged. [Session full suite](evidence/tests/soak-hourly-audit-01.txt).

## First attested human session
2026-10-07 06:05 JST: human directly confirmed the screenshot receipt input. Session/key/record ID matched read-only canonical ingress; one actual human turn registered with monitor-anchored attestation. [Evidence](evidence/soak/2026-10-06/human-session-01.json), [55-test full suite](evidence/tests/soak-human-session-01.txt). Existing baseline/clock unchanged; no canonical writes, repairs, runtime changes or new provider calls. Planned restart is armed for unfinished work in this session, not yet performed. S0-13 remains incomplete. Historical blocked condition of no first receipt is released; subsequent human actions and time gate remain outstanding. Exact next action: human sends the first local draft request in the same page session, then controller verifies supported restart evidence.

## UI recovery defect correction
2026-10-07: direct human test proved unfinished restart and single draft completion; screenshot also exposed stale outage warning. Deterministic actual-JS failure→success probe reproduced and verified the minimal fix. Existing design preserved; routine UI fix exemption applies. Soak01 intentionally invalidated, not repaired or silently continued; fresh baseline/run required under D-016/D-017. Earlier active-host, counts, next-action and blocked notes above are historical and superseded by the current phase/active soak sections.

Fresh soak02 startup verified healthy, source/versions captured, initial fsync chain valid and human counts zero. Hourly operational automation updated to active soak02; old run explicitly excluded. The user must reload the conversation page to load fixed JavaScript and establish a new UI session. Previous screenshots/receipts are retained as historical defect/recovery evidence only. No old attestation was copied.

## User-requested bilingual presentation
2026-10-07: user requested UI Japanese alongside English with internals retained in English, and directly attested the soak02 screenshot receipt. Matched/anchored that receipt before supported stop. UI labels, action explanations, status messages, errors and inspect table headings now bilingual; user content and inspect/receipt JSON stay unchanged. This is routine presentation work within accepted behavior, no design/capability/criteria changes, so consultation gates do not trigger. Old run counts not copied. Initial UTF-8 stdin edit failed before changing files; corrected with explicit coding declaration and reran verification after actual diff. Older active-run/next-action entries are historical; current sections above supersede them.

Active operational heartbeat updated to soak03; older run metadata/history do not override active sections. User must reload to obtain bilingual JavaScript/new session and provide one new human-confirmed receipt before draft/restart work. Internal English contracts preserved; no canonical repair or prior-count transfer.

Soak03 first direct human receipt confirmed and registered: [matched receipt, owned health and fsync attestation anchor](evidence/soak/2026-10-07/soak03-human-session-01.json). No canonical repair or runtime/probe changes; baseline and clock retained. Next action: first human draft in the same session for monitored unfinished restart.

Receipt increment verification: [full suite 55 PASS](evidence/tests/soak03-human-session-01.txt). Initial sandbox-only run could not bind test HTTP sockets (7 PermissionError setup errors); [retained restricted-run log](evidence/tests/soak03-human-session-01-sandbox-blocked.txt). Rerun with approved temporary loopback test access passed; future full HTTP suite runs need that access. No product defect or soak reset implied by the isolated sandbox restriction.

[First bilingual human draft and supported restart evidence](evidence/soak/2026-10-07/soak03-human-restart.json): same Goal, ACK digest match, one completed artifact; user opened artifact and directly confirmed input. Current host PID23997, started_at1791322170.840451; monitor remains PID3322. Baseline/chain unchanged, no reset or canonical repair.

Restart receipt increment: [full suite 55 PASS](evidence/tests/soak03-human-restart.txt). Docs/evidence-only increment preserves current runtime baseline and clock.

[Four directly confirmed inputs, conversation before completion and cancel fencing](evidence/soak/2026-10-07/soak03-human-conversation-cancel.json). Dinner Goal completed, conversation reply precedes completion record; picnic Goal cancelled with Attempt fenced and no receipt. Six human turns / one session / three Goals / one cancel; correction and remaining time/session/turn gates pending. No runtime changes or canonical repair.

[Conversation/cancel increment full suite: 55 PASS](evidence/tests/soak03-human-conversation-cancel.txt). Docs/evidence-only update; baseline/clock retained.

[Two directly confirmed correction inputs](evidence/soak/2026-10-07/soak03-human-correction.json): revision1 fenced with no receipt; revision2 completed with one host-verified corrected artifact and fixed criteria unchanged. Screenshots show correction applied and 8-turn receipt; artifact UI opening not claimed. No runtime changes or canonical repair. Audit initially assumed a trailing newline; actual readback has none, matching receipt size/hash. Corrected audit expectation without product change; next checks compare exact stored bytes/specification.

[Correction increment full suite: 55 PASS](evidence/tests/soak03-human-correction.txt). Docs/evidence-only update preserves runtime baseline and clock.

[Second directly confirmed session and fifth Goal](evidence/soak/2026-10-07/soak03-human-session-02.json). Screenshot receipt is a new session, not the earlier session; both confirmed IDs retained and monitor-anchored. Fifth Goal completed with host-receipt hash/readback. Ten human turns / two sessions / five Goals; no clock reset or canonical repair.

[Second-session increment full suite: 55 PASS](evidence/tests/soak03-human-session-02.txt). Evidence/docs-only change retains baseline and clock.

User steering and Opus/Astra reconsideration: [D-018](DECISIONS.md). Both reviewers agree current mock UI/time quotas do not prove expected functional behavior. Recommendation is pending explicit adoption; original S0-13 not PASS, no canonical changes or historical evidence rewrite. [Full suite 55 PASS](evidence/tests/personal-use-reconsideration.txt).

D-019 direct adoption received; goal/accepted completion definition updated before code. App goal replacement unavailable for unfinished objective; do not fake completion. Repository objective and this latest user instruction supersede stale blocked app-card72h text.

D-019 implementation transition: old soak03 monitor/app stopped normally before runtime changes; [24-record terminal hash chain and retained snapshot](evidence/soak/2026-10-07/soak03-functional-development-stop.json). No old time/count transfer or canonical repair. Operational heartbeat updated to revised functional objective. [55-test adoption suite](evidence/tests/functional-definition-adoption.txt).

D-020 bounded UI implementation: strict one-use metadata proof, dual expiry, shared atomic invocation budget, supervised auth and generation, pure visible provider status, explicit CLI selection/default mock. [65-test full suite](evidence/tests/real-ui-bounded-green.txt), [actual refresh probe](evidence/tests/real-ui-refresh-green.txt). Test-first failures retained. Live functionality not yet claimed. Old runtime and optional soak clocks remain stopped and preserved.

Functional baseline 307058d: explicit official host PID74721 on port58500, runtime/functional-20261007-01/state.db (new DB, old soak DBs intact). Proof expires at1791324883.163075; 13 of32 host generation invocations used. UI mode/budget visible; no auto renewal/mock fallback. Fresh official verification + explicit restart needed for further native calls after expiry; historical responses/artifacts/inspect remain available. [Real evidence](evidence/functional/2026-10-07/README.md), [66 tests](evidence/tests/real-functional-full.txt). F0-05 prompt backed by actual context implementation and response manifest reconstruction, not raw stdin logging. Scripted browser receipt never counts as human input.
