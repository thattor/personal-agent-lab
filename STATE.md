# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
S0-01 through S0-12 PASS. Official tool-free native smoke and actual Chrome UI evidence complete. S0-13 soak01 was invalidated by a reproduced stale UI warning and is retained/stopped; the fix is verified and a fresh soak02 baseline is ready. Stable-0 remains incomplete.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote origin/main. Original supplied untracked workspace preserved. No old implementation/schema was reused; the accidental startup metadata inspection is explicitly recorded in docs/DEFECTS.md. Do not inspect it again.

## Last green increment
55 integrated tests PASS: [full log](evidence/tests/ui-native-soak-full.txt), [actual monitor preflight](evidence/tests/soak-preflight-summary.json). Controls/input/pause/resume real SIGKILL fault coverage, independent lanes, typed host-only capabilities, original-request dedupe/fate lookup, native lifetime supervision and secret-free OS auth environment. [Clean live smoke](evidence/live/2026-10-06-clean/result.json): 3 official Claude Pro calls, tools/MCP empty, no extra-charge/fallback/new login, actual 276-byte host-verified draft. [Browser smoke](evidence/ui/browser-smoke.md): conversation/draft/inspect/restart/session receipt. Prior failed/partial live attempts are preserved and do not count as PASS.

## Active soak
Old runtime/soak-20261006-01 retained, explicitly INVALIDATED after direct human UI finding. Supported monitor stop appended reset_required; original DB/history and human/restart evidence preserved. [Finding and verified canonical recovery](evidence/soak/2026-10-06/ui-recovery-finding.json). UI fix clears recovered state-fetch warnings, preserving message failures. [Actual JS red/green probe](evidence/ui/recovery/after.txt), [55-test full suite](evidence/tests/ui-recovery-full.txt). No canonical repair. New run runtime/soak-20261007-02 will start from this clean committed baseline on loopback port58500. No previous human counts, time or restart proof transferred.

## Exact next action
Launch fresh soak02, verify owned health/hash chain and record baseline. Then human reloads conversation UI (new session/fixed JS/fresh data), sends one ordinary message, supplies Session receipt and explicit human-input confirmation. Register ONLY that newly confirmed session before the first draft so unfinished restart is armed. Accumulate >=20 human turns / >=3 sessions spanning >=72 hours / >=5 human Goals / cancel / correction or reference-stop. No scripted substitute or self-attestation.
When an anchored candidate qualifies, perform final full suite, acceptance/controller audit, historical-chain verification, evidence commit/push and Issue closure. Stable-0 remains incomplete.

## Acceptance status
S0-01–12 PASS with evidence. S0-13 reset_required (fresh baseline ready). Master Issue #1 open; no Stable-0 declaration.

## Human participation requirement
D-016/Opus explicitly rejects substituting scripted traffic for user turns. The user must type >=20 turns in >=3 sessions spanning >=72 hours, create >=5 Goals, cancel once and correct/reference-stop once. Monitor may perform the supported unfinished restart and read-only checks. Preparing this concrete environment requires no new auth, broader permission, payment or public exposure. An autonomous-only substitute would change accepted evidence meaning and requires the user's judgment.

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
