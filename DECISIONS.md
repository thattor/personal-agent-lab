# DECISIONS.md

This file records decisions needed to continue implementation. Newer entries override older conflicting entries.

## D-000 — Greenfield only
Date: 2026-10-06
Decision: New PAL is designed and implemented from zero. Old PAL code, schema, workflow, reviews, P0/P1 lists, and compatibility constraints are excluded from design input and reuse analysis.
Owner: user decision.

## D-001 — Product goal
Date: 2026-10-06
Decision: Goal is the minimum stable implementation, Stable-0. Codex continues development until acceptance evidence is complete.
Owner: user decision.

## D-002 — Review protocol
Date: 2026-10-06
Decision:
- Design changes require Opus discussion before adoption.
- Substantial implementation-oriented design and code-generation decisions require Devin SWE-2 High discussion.
- Codex remains controller/integrator.
- User is interrupted only for new auth/permission, extra cost, external/public exposure, or a required contradiction of accepted product behavior.
Owner: user decision.

## D-003 — 2 bots / 4 responsibilities
Date: 2026-10-06
Decision: Primary Bot = Primary + Responder. Expert Bot = Expert + Executor. Primary owns canonical control/routing; Responder owns conversation and proposals; Expert is a thin durable outcome controller; Executor owns local execution within scope. Responsibility boundaries should be enforced as capability boundaries where practical.
Owner: prior user/ChatGPT/Opus agreement.

## D-004 — Finish and evidence
Date: 2026-10-06
Decision: Acceptance Criteria are fixed before execution. Executor self-report cannot complete a Goal. Host-side gate checks host-issued evidence/receipts and returns pass/fail/unverified.
Owner: prior user/ChatGPT/Opus/SWE-2 High agreement.

## D-005 — Reversible proactive behavior
Date: 2026-10-06
Decision: PAL may proactively perform reversible preparation. Explicit limits override this. Irreversible/external operations are not executed without explicit approval. Host policy, not Executor self-report, classifies action class.
Owner: user decision; implementation boundary refined in review.

## D-006 — Memory
Date: 2026-10-06
Decision: Keep secret-sanitized raw records broadly; keep lightweight derived notes/source refs for recall; re-read source for important conditions/conflicts. Forget means reference stop, not deletion. Raw history remains; AI use of the forgotten source stops.
Owner: user decision.

## D-007 — Procedure learning
Date: 2026-10-06
Decision: Record successes/failures/corrections and propose improvements with evidence. Formal procedure/workflow/playbook changes require human approval. No automatic procedure promotion in Stable-0.
Owner: user decision + Opus agreement.

## D-008 — Stable-0 scope review
Date: 2026-10-06
Question: Should Stable-0 equal the full earlier M1?
Opus conclusion: No. Minimum stable should keep restart/dedupe/stale-result defense, cancellation, correction/reference-stop, conversation during work, input/result resume, one no-extra-charge real provider smoke, automated tests, and a 72-hour real-use soak. External-dependency/polish items such as PublicSearch live and time wake should move post-Stable-0.
Adopted: yes.
Reason: keeps the stable exit tied to core reliability rather than unrelated external integrations.

## D-009 — SWE-2 High implementation review
Date: 2026-10-06
Question: Is the Stable-0 scope implementable and how should Codex execute it?
SWE-2 High conclusion:
- Implementable without more broad product discussion once core semantics are fixed.
- Recommended slices: canonical store/state machine; concurrent ingress; Executor boundary/approval gate; cancel/correct/forget/resume; recovery/idempotency/provider smoke.
- Repo should maintain AGENTS, SPEC, DESIGN, DECISIONS, STATE, ACCEPTANCE.
- Codex should use small green commits, test-first where practical, and consult Opus/SWE-2 only at defined gates.
Adopted with refinements already present in DESIGN.md and ACCEPTANCE.md.
Important clarification: do not use old PAL or any unrelated memory as input.

## D-010 — Stable soak
Date: 2026-10-06
Decision: Stable-0 requires a 72-hour wall-clock soak after all other Stable-0 acceptance rows pass. Normal supported restart is allowed; direct DB/state repair is not. A semantic persistence/recovery change resets the soak.
Owner: implementation acceptance decision, based on Opus/SWE-2 review.

## Pending decisions
None that block Slice S1. Add entries only when a consultation gate actually triggers.
