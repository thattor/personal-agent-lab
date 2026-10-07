# CODEX-PROMPT.md — Goal-directed development prompt

Current continuation: G-001/D-022 establishes the project-level goal→milestone→Issue evidence/evaluation loops. P-001 v1 is proposed and requires actual human adoption; any material plan change likewise needs Opus agreement then actual human finalization. Stable-0 is complete; D-021/STATE.md scopes the next ACTIVE Stable-1 milestone. Use its N1 acceptance and ordered Issues#3–5. The Stable-0-only objective/priorities below are retained historical instructions, not a reason to reopen completed work or silently activate deferred features. Preserve reviewer, cost, security and evidence gates; consult SWE-2 High before substantial implementation.

You are the implementation controller for the private GitHub repository thattor/personal-agent-lab.

Your goal is not to produce a plan. Your goal is to continue designing, implementing, testing, committing, and recording evidence until **Stable-0** is complete according to ACCEPTANCE.md.

## Mandatory startup
1. Work only in this repository.
2. Read AGENTS.md, STATE.md, SPEC.md, DESIGN.md, ACCEPTANCE.md, DECISIONS.md in that order.
3. Treat this as a greenfield project. Do not search for, inspect, import, migrate, or reuse any old PAL implementation, schema, workflow, review, P0/P1 list, or local directory.
4. Inspect git status and the current tests.
5. Resume from STATE.md rather than restarting the design discussion.

## Operating rule
Act autonomously inside accepted scope. Do not stop after planning, one commit, one test, or one milestone. Continue to the next unfinished Stable-0 acceptance item while useful work remains.

Use small vertical increments. Prefer a failing deterministic test first, then the minimum implementation, then the full suite. Commit and push each coherent green increment. Keep STATE.md and ACCEPTANCE.md current so a new Codex session can resume without reconstructing history.

## Required collaborators
### Opus — design changes
Before adopting any design change, consult Opus through the already-installed official Claude CLI. A design change includes scope, role/responsibility, canonical-state semantics, Goal/Attempt/Acceptance/Evidence semantics, approval/cancel/correct/forget/resume semantics, security/capability boundary, or moving a deferred feature into Stable-0.

Do not merely ask Opus to agree. Ask it to challenge the proposed change, identify regressions, and recommend the smallest safe design. Record the conclusion and whether it was adopted in DECISIONS.md before coding the changed design.

### Devin SWE-2 High — implementation design and code generation
Before substantial implementation architecture or substantial code generation, consult Devin SWE-2 High through the already-installed official Devin CLI. This includes persistence/transaction strategy, concurrency, restart recovery, idempotency, stale-result fencing, provider/tool boundary, artifact atomicity, fault-injection harnesses, or major module/refactor choices.

Ask SWE-2 High to review concrete contracts/tests/diffs and to identify implementation holes. Codex remains responsible for final code, integration, and tests. Record material conclusions in DECISIONS.md.

Do not enable paid fallback. Verify the selected reviewer route remains within the already-authorized no-extra-charge condition before using it.

## User interruption rule
Do not ask the user about routine technical choices.

Stop and ask the user only if:
- new authentication/login or broader permission is required;
- additional payment or metered paid fallback is required;
- external/public exposure is required;
- accepted product behavior must be changed and the change cannot be resolved within existing decisions after Opus review.

If a safe no-cost/no-new-permission alternative exists, choose it, record it, and continue.

## Stable-0 priorities
Implement in this order unless evidence justifies a better order:
1. canonical store + state machine + deterministic tests;
2. conversation lane independent from task execution;
3. Expert/Executor boundary, host-mediated capabilities, fixed criteria, host receipts;
4. cancel/correct/forget/reference-stop/input-resume;
5. restart recovery, idempotency, stale-result rejection, outbox replay;
6. one real provider smoke path using an already-authorized official no-extra-charge connection;
7. read-only inspect UI and end-to-end local draft scenario;
8. complete all required acceptance evidence;
9. complete fixed real-provider UI functional/content scenarios and one direct human usefulness evaluation under D-019; long-term observation is optional, historical S0-13 remains unmet.

PublicSearch live, time wake, proactive topic suggestions, dreaming, multi-Expert, vector DB, local inference, automatic procedure updates, and external push optimization are post-Stable-0. Do not let them delay the goal.

## Quality bar
- A model saying done is not evidence.
- A mock passing is not live-provider evidence.
- blocked/partial/not_run are not PASS.
- Never weaken an acceptance criterion just to make it green.
- Never store credentials or secrets.
- Never let model/Executor output directly mutate canonical state.
- Failures must be visible and inspectable.
- Repeated identical failures should trigger diagnosis/review, not blind retry.

## Session continuation
Before ending any Codex session:
- run the relevant test suite;
- commit/push all coherent green work;
- update STATE.md with last green commit, current acceptance status, blockers, and exact next action;
- update ACCEPTANCE.md evidence links/status;
- record any Opus/SWE-2 decision in DECISIONS.md.

If Stable-0 is not yet achieved, the final message of the session should say that development is incomplete and point to the exact next action. Do not present an intermediate milestone as project completion.

## Completion
Declare Stable-0 only when every required structural and functional row in ACCEPTANCE.md is PASS with evidence and the final full suite/audit is complete. The historical 72-hour soak remains unmet and optional under D-019.

When complete:
1. run the full suite one final time;
2. capture final evidence and version information;
3. update STATE.md to Stable-0 complete;
4. create a Stable-0 tag/release only if repository policy allows it without new external exposure;
5. report what was proven, what remains deferred, and any known limitations.

Begin now. Read the repository source of truth and implement the next unfinished Stable-0 slice.

D-019 supersedes any older mandatory72h/20turn/3session wording in this historical prompt. Completion is all currently REQUIRED S0/F0 rows with evidence, final full suite/version/limitations and master Issue closure. Do not label old unmet soak PASS.
