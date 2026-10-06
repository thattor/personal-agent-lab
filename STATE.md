# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
S0-01 through S0-12 PASS. Official tool-free native smoke and actual Chrome UI evidence complete. S0-13 mock host soak is running; actual human-use gate remains incomplete.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote origin/main. Original supplied untracked workspace preserved. No old implementation/schema was reused; the accidental startup metadata inspection is explicitly recorded in docs/DEFECTS.md. Do not inspect it again.

## Last green increment
55 integrated tests PASS: [full log](evidence/tests/ui-native-soak-full.txt), [actual monitor preflight](evidence/tests/soak-preflight-summary.json). Controls/input/pause/resume real SIGKILL fault coverage, independent lanes, typed host-only capabilities, original-request dedupe/fate lookup, native lifetime supervision and secret-free OS auth environment. [Clean live smoke](evidence/live/2026-10-06-clean/result.json): 3 official Claude Pro calls, tools/MCP empty, no extra-charge/fallback/new login, actual 276-byte host-verified draft. [Browser smoke](evidence/ui/browser-smoke.md): conversation/draft/inspect/restart/session receipt. Prior failed/partial live attempts are preserved and do not count as PASS.

## Active soak
Started 2026-10-06T13:41:26.756470+00:00, clean baseline `c887c35d540a55f6f3108d546da3220f0852b76a`. Monitor PID 28510; app PID 28513; runtime/soak-20261006-01. Conversation http://127.0.0.1:58500/ and read-only /inspect. Initial canary/invariants PASS, human turns 0. [Start evidence](evidence/soak/2026-10-06/start.json). Match owned process command/start/boot identity before any lifecycle operation; do not blindly restart or repair DB.

## Exact next action
Obtain the first actual human UI session receipt and direct attestation. Atomically write runtime/soak-20261006-01/human-attestation.json with exactly source=direct_user_attestation and the confirmed session_ids, only from the human's explicit confirmation. Then a draft in that attested session arms the supported unfinished restart. Accumulate >=20 human turns / >=3 sessions spanning >=72 actual hours / >=5 human Goals / cancellation / correction or reference-stop. No scripted substitute or self-attestation.

Read live hash chain/candidate/health; diagnose any finding without canonical repair. Runtime/probe changes or failures reset this run. When an anchored candidate qualifies, run final full suite/evidence audit, write the controller completion marker described in README, verify anchored orderly final completion, update all acceptance/Stable state, commit/push, and close Issue #1.

## Acceptance status
S0-01–12 PASS with evidence. S0-13 in_progress (human_pending). Master Issue #1 open; no Stable-0 declaration.

## Human participation requirement
D-016/Opus explicitly rejects substituting scripted traffic for user turns. The user must type >=20 turns in >=3 sessions spanning >=72 hours, create >=5 Goals, cancel once and correct/reference-stop once. Monitor may perform the supported unfinished restart and read-only checks. Preparing this concrete environment requires no new auth, broader permission, payment or public exposure. An autonomous-only substitute would change accepted evidence meaning and requires the user's judgment.

## Deferred
PublicSearch, time wake, proactive topics, Dreaming, multi-Expert, vectors, local inference, automatic procedure updates, external push.

## Follow-up and pending user decision
Hourly current-thread audit registered as `pal-stable-0-soak-audit` (ACTIVE, failed-run notifications only), restricted to this checkout and existing soak; first scheduled execution is not yet observed. It must be paused after verified completion or direct user cancellation. This operational audit is not a PAL scheduled-wake product feature.

The human has been asked whether to proceed with real typed UI sessions or request reconsideration of the human-use gate. No response/attestation is assumed. Pending first action: enter one non-secret message at http://127.0.0.1:58500/, copy Session receipt JSON and explicitly confirm the input was human-typed in this chat. Until then no attestation file is written and no human minimum is counted.

Session closing verification: full suite in evidence/tests/soak-start-full.txt. No runtime/probe changes since baseline c887c35; only docs/evidence updates, so the running clock remains valid. Prior synthetic UI host on port58487 stopped normally; its DB retained. Real soak host/monitor remain running.
