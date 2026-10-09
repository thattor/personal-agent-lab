# AGENTS.md — Personal Agent Lab

Current D040/C077 continuation and D037 route instruction supersede earlier stops
and the CO-only restriction. Evaluate checkpoints, correct within accepted scope,
then actually continue the next unfinished authorized dependency.
SWE-2 remains preferred when usable; native Astra/Sol and scoped AGY Opus5.5/Sonnet5.5
are owner-approved alternatives. Preserve both recorded unknown calls; no implicit
retry/cancel or state edit. AGY exact-conversation loading was rejected by automatic
review; its concrete optional approval is in the human lane. D039 now prioritizes
CO SWE and fresh scoped AGY code; D040 lifts native restraint after manual reset.
Owner max32 is bounded by actual route/tool limits and independent work. Old unknown
conversation actions remain prohibited. Exact limits are in STATE/DECISIONS.
INT00/1, TSK01/1, MEM01/1, TSK03/1 and TSK02/RUN01 local mock preparation are
integrated with separate review and full531 regression, including durable C14,
actual controls/source-stop and callable-cessation occupancy. Real PRI authority,
recovery, saved verified drafts, live services and full v5 activation remain unproven.
C074: saved drafts are connected through actual MEM/TSK/RUN/ART/C14;
full605 passes with independent ART/TSK/RUN/consumer reviews. Exact CO Opus5.5
milestone review is ALIGNED. Continue the next unfinished
verification/completion dependency; whole v5 service activation remains unproven.
Native Sol authored storage under existing owner fallback; the CO timeout remains
unknown and untouched. Current STATE/DECISIONS supersede historical pending text.
C075: deterministic VER is connected atfab7c77, full650 and independent review
pass; exact Opus milestone0e78d5da is ALIGNED. COMPLETE01-SCOPE is frozen
for isolated TSK/RUN work. Continue the loop; do not activate partial completion.


C077: READ01 local slice MET atff1a1cc,747 host PASS and independent exact Opus
code APPROVE. Milestone provenance REFINE was addressed by a saved/rerun harness;
do not relabel it ALIGNED. ASK01 contract remains under technical reconciliation.

## Mission
The project-level destination is the personal assistant described in SPEC.md. Manage project goal → GitHub milestone → goal-bearing Issue → verified work unit under G-001/D-022. [Latest overall plan P-001 v2](docs/plans/P-001-v2.md) is PROPOSED, not human-adopted; v1 is retained history. Stable-0 is released; Stable-1 under D-021 remains the approved current milestone; C065/D034 authorizes the scoped CO development start; shared wire, bounded intake and MEM/TSK queued-source connection are integrated. C14 delivery and the TSK execution/control boundary are next; external product activation remains subject to the reviewed candidate scope. Resume STATE.md, continue independently authorized work, and never activate PROPOSED stages from GitHub metadata alone.

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

Keep reusable PAL research, design records and data in this private repository with provenance and verification limits (D-030). Temporary folders and chat artifacts are staging copies, not the only retained copy. Historical access receipts and one-time approvals do not grant new execution authority.

## Roles
- Codex: controller and implementer. Own project/milestone/Issue loops, coding, tests, commits, evidence, checkpoints and continuation within the current adopted plan.
- Opus: independent design partner. Consult before adopting a design change.
- Devin SWE-2 High: implementation-design and code-generation partner. Consult for substantial implementation architecture, concurrency, persistence, recovery, idempotency, test harnesses, provider/tool boundaries, or uncertain substantial code generation.

Codex remains responsible for integration and evidence.

Latest owner operating instruction (2026-10-08): this development chat is the sole
writer of product code and canonical records. Use the persistent human-judgment chat
for noninferable owner facts, authority and actual usefulness; use the existing design-change
chat for material proposals. Current IDs, scope and waiting conditions
live in STATE.md. Necessary messages between those chats are authorized; external
support submission is not. Pending future proposals do not block accepted work.

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
- a material development-plan/scope/acceptance/priority change needs actual human finalization after Opus agreement under G-001;
- accepted product behavior cannot be resolved within existing decisions after Opus review.

If a safer, no-cost, no-new-permission alternative exists, use it and continue.

D-028 clarification: first resolve choices using the owner's goal, existing decisions,
repository evidence and model reasoning. A human question is valid only when it names
the specific noninferable fact/authority/value judgment and the material outcome it
changes. Technical methods, model-capability testing, copy, and reviewer caution are
not approval gates. Opus/SWE advice cannot create owner-approval requirements.
One end-to-end personal usefulness evaluation remains necessary after working output
exists; do not fragment it into sentence/example approvals or block independent work.
Pending future-plan proposals are dormant until a real scope conflict needs a decision.

## Reviewer commands
Use the installed official CLIs and verify syntax with --help when needed. Do not enable paid fallback.

Opus example:
claude -p --model opus --permission-mode plan --output-format text "<review prompt>"

SWE-2 High example:
devin --model swe-2-high --permission-mode auto --sandbox -p "<review prompt>"

Respect official workspace trust. A refusal requires the scoped owner action in
D029 C046; never use the old trust-check override example to bypass that boundary.

Before each call, confirm the account is already authenticated and the selected route does not require extra payment. Never commit credentials or private account data.

## Development loop
1. Read source-of-truth docs and git status.
2. Select the smallest unfinished acceptance slice in the current milestone recorded in STATE.md.
3. Add or extend a failing deterministic test first when practical.
4. Consult Opus/SWE-2 High if a gate triggers.
5. Implement the minimum coherent change.
6. Run targeted tests, then the full automated suite.
7. Run required fault injection or live smoke when the slice calls for it.
8. Update ACCEPTANCE.md with evidence and STATE.md with current state.
9. Commit a small green increment. Reference acceptance and decision IDs.
10. Evaluate the unit goal and contribution to its Issue/milestone/project; record outcome/evidence/commit/limits/plan impact/next action. Continue the next unfinished authorized item.
11. At Issue entry/closure verify its design role, concrete added user value, why it is the next necessary work, and remaining project gap. At milestone entry/exit, and on direction drift or repeated causes, obtain one official Opus design-alignment review of those points through the design lane. Record the resulting next work choice in the existing CHECKPOINTS/STATE records. This is not a per-commit/wording review or another owner approval gate. Defects/user feedback/assumption failures trigger an early checkpoint. Closed children alone never complete the parent.
12. Material plan changes: discuss/agreed with Opus → versioned evidence-bound proposal → actual human decision → update docs/GitHub → resume dependencies. Pending judgment blocks only affected work; routine technical decisions remain autonomous. See D-022 and docs/plans/P-001-v1.md. Do not restart paused schedules.

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

## C065 CO development lane (2026-10-09)
SOL integrates and owns canonical records. Use the global task-orchestration skill and the qualified co_v4.task entrypoint identified in STATE.md. Scoped worker changes are generated in CO-owned isolated workspaces and integrated only after SOL checks the exact diff, host verifier and independent review. Preserve the original dirty checkout and runtime data. Use the published0.4.5 concurrent-task CLI identified in STATE.md. Independent ordinary runs may share the existing qualified state, within the host limit of12 per Native adapter; no second engine, alternate state or ledger edits to bypass it. Current input is docs/design/contracts-v5. Common-wire design consultation is complete, full v5 service adoption and independent code review remain incomplete. The SWE attempt has unknown outcome: follow the exact continuation limit in STATE.md rather than starting a duplicate implementation.

The owner later authorizes updating to and using an official CO0.4 parallel-capable
version when available; follow D034's state-preserving supported migration and actual
qualification. Continue independent PAL work meanwhile. This permits runtime update
inside its conditions, not CO implementation edits, a0.3 downgrade or a new monitor.


C073 route clarification after scoped diagnosis: the prior no-duplicate instruction
prohibits a blind CO retry, not the owner's explicit separate native implementation.
Root freshly read actual owner message01a11e03-d444-78c1-9fab-b0e861d29d1d: use
Astra/Sol6.1/AGY while SWE2 cannot implement; direct call allowed without a CO adapter.
Diagnosis found no local process, no assistant/tool response and no implementation
files for task917989. Remote cessation/cause remain unknown. Preserve that pause and
workspace exactly. A NEW isolated native Sol6.1 workspace implements ART01-store/1
plus the frozen inspect callback; no late CO output auto-adoption, no shared DB or
external effects. This applies existing user authority (which supersedes skill
routing defaults), not a fabricated CO pause decision or new CO engine. AGY's own
unresolved call/rejection stays untouched. Ordinary Codex usage is allowed; no paid
fallback, reset, new authorization or external service is used. Independent Astra
will review ART after its TSK task; separate Sol reviews Root/Astra changes.

C076 local completion is MET atbdce832: full711, independent TSK/RUN review and
exact CO Opus5.5 ALIGNED. Source-stop preserves completed history. Continue the
concrete READ01 result-inspection consumer; its design refinements are adopted,
implementation freeze follows SWE consultation. No service activation or recurring
owner gate; current STATE/DECISIONS retain all unknown-call and cost boundaries.
