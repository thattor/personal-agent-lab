# STATE.md

## Goal
Reach Stable-0 as defined in ACCEPTANCE.md. Stable-0 is **incomplete**.

## Current phase
S0-01 through S0-12 PASS. Official tool-free native smoke and actual Chrome UI evidence complete. S0-13 human-use soak remains incomplete.

## Working checkout
`/private/tmp/personal-agent-lab-stable0-20261006`, same private GitHub repository, remote origin/main. Original supplied untracked workspace preserved. No old implementation/schema was reused; the accidental startup metadata inspection is explicitly recorded in docs/DEFECTS.md. Do not inspect it again.

## Last green increment
47 integrated native/UI tests PASS: [log](evidence/tests/ui-native-full.txt). Controls/input/pause/resume real SIGKILL fault coverage, independent lanes, typed host-only capabilities, original-request dedupe/fate lookup, native lifetime supervision and secret-free OS auth environment. [Clean live smoke](evidence/live/2026-10-06-clean/result.json): 3 official Claude Pro calls, tools/MCP empty, no extra-charge/fallback/new login, actual 276-byte host-verified draft. [Browser smoke](evidence/ui/browser-smoke.md): conversation/draft/inspect/restart/session receipt. Prior failed/partial live attempts are preserved and do not count as PASS.

## Exact next action
Finish concrete soak-monitor SWE-2 review, rerun full suite + separate preflight, commit/push the clean baseline, then start the 72-hour mock host soak. Obtain actual human UI sessions/receipt attestation; scripted turns cannot satisfy D-016.

## Acceptance status
S0-01–12 PASS with evidence. S0-13 not_run. Master Issue #1 open; no Stable-0 declaration.

## Human participation requirement
D-016/Opus explicitly rejects substituting scripted traffic for user turns. The user must type >=20 turns in >=3 sessions spanning >=72 hours, create >=5 Goals, cancel once and correct/reference-stop once. Monitor may perform the supported unfinished restart and read-only checks. Preparing this concrete environment requires no new auth, broader permission, payment or public exposure. An autonomous-only substitute would change accepted evidence meaning and requires the user's judgment.

## Deferred
PublicSearch, time wake, proactive topics, Dreaming, multi-Expert, vectors, local inference, automatic procedure updates, external push.
