# AGENTS.md — Personal Agent Lab

## Mission
Build Stable-0, the minimum stable Personal Agent Lab implementation. Continue autonomously until the Stable-0 definition in ACCEPTANCE.md is satisfied with evidence.

This is a greenfield project. Do not search for, read, copy, migrate, or preserve compatibility with any old PAL implementation, schema, workflow, review, P0/P1 list, or codebase.

## Source of truth
Read at the start of every work session:
1. AGENTS.md
2. STATE.md
3. SPEC.md
4. DESIGN.md
5. ACCEPTANCE.md
6. DECISIONS.md

If documents conflict, later explicit decisions in DECISIONS.md win. Never silently weaken accepted product behavior to make tests pass.

## Roles
- Codex: controller and implementer. Own planning, coding, tests, commits, evidence, and continuation to Stable-0.
- Opus: independent design partner. Consult before adopting a design change.
- Devin SWE-2 High: implementation-design and code-generation partner. Consult for substantial implementation architecture, concurrency, persistence, recovery, idempotency, test harnesses, provider/tool boundaries, or uncertain substantial code generation.

Codex remains responsible for integration and evidence.

## Consultation gates

Consult Opus before adoption when a change affects:
- product scope or Stable-0 definition;
- Primary/Responder/Expert/Executor responsibilities;
- Goal/Attempt/Acceptance/Evidence semantics;
- approval, cancellation, correction, forget/reference-stop, or resume semantics;
- capability/security boundaries;
- moving a DEFERRED feature into Stable-0 or removing an accepted Stable-0 behavior.

Record the question, answer, and adopted/rejected conclusion in DECISIONS.md before implementation.

Consult SWE-2 High before substantial implementation when:
- choosing or changing persistence/transaction strategy;
- choosing or changing concurrency/worker model;
- implementing restart recovery, dedupe, stale-result fencing, artifact atomicity;
- designing provider/tool adapters or capability enforcement;
- designing a non-trivial test/fault-injection harness;
- generating a substantial new module or refactoring a boundary.

Routine naming, local refactors, small bug fixes, test additions, and obvious details do not require consultation.

Ask the user only when:
- a new login/authentication or broader permission is required;
- any additional payment or metered paid fallback would be required;
- external/public exposure is required;
- accepted product behavior must be changed and Opus review cannot resolve it within existing decisions.

If a safer, no-cost, no-new-permission alternative exists, use it and continue.

## Reviewer commands
Use the installed official CLIs and verify syntax with --help when needed. Do not enable paid fallback.

Opus example:
claude -p --model opus --permission-mode plan --output-format text "<review prompt>"

SWE-2 High example:
devin --model swe-2-high --permission-mode auto --sandbox --respect-workspace-trust false -p "<review prompt>"

Before each call, confirm the account is already authenticated and the selected route does not require extra payment. Never commit credentials or private account data.

## Development loop
1. Read source-of-truth docs and git status.
2. Select the smallest unfinished Stable-0 acceptance slice.
3. Add or extend a failing deterministic test first when practical.
4. Consult Opus/SWE-2 High if a gate triggers.
5. Implement the minimum coherent change.
6. Run targeted tests, then the full automated suite.
7. Run required fault injection or live smoke when the slice calls for it.
8. Update ACCEPTANCE.md with evidence and STATE.md with current state.
9. Commit a small green increment. Reference acceptance and decision IDs.
10. Continue immediately to the next unfinished item. Do not stop merely because one slice passed.

If leaving a red state because of a real blocker, STATE.md must contain the exact failure, evidence, attempts, and next action.

## Stable declaration
Never call the product Stable-0 until every required Stable-0 row in ACCEPTANCE.md is PASS with linked evidence under the revised functional-first definition adopted in D-019. The historical 72-hour soak row is optional and must not be relabelled PASS.

A mock, fixture, reviewer opinion, or model self-report is not product evidence.

## Security and scope
- No secrets in repo, logs, memory, prompts, fixtures, or test artifacts.
- Models/Executors do not write canonical state directly.
- Host-issued observations/receipts are authoritative evidence.
- Irreversible/external side effects require host-side policy plus explicit approval.
- Stable-0 should avoid real irreversible side effects; use a spy/denied tool for negative tests.
- No extra cost.
- No external public exposure.
