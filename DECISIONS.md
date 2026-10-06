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

## D-011 — S1 review and concrete state contracts
Date: 2026-10-06
Question: [S1 proposal to Opus](evidence/reviews/s1-opus-question.txt); [SWE-2 implementation proposal](evidence/reviews/s1-swe-question.txt).
Responses: [Opus](evidence/reviews/s1-opus-response.txt), [SWE-2 High](evidence/reviews/s1-swe-response.txt). Routes: [verified official access](evidence/reviews/access-2026-10-06.md).
Adopted before implementation:
- States queued/running/waiting_input/paused/completed/cancelled/failed/unknown. Global single task slot. Host controls every mutation.
- One epoch increases on claims and fencing controls; Attempt also pins Goal revision and immutable acceptance version. Corrections create revisions; unchanged criteria reuse acceptance version.
- Attempt outcomes pass/fail/unverified/error/fenced/abandoned. Unverified retries within claim-consumed budget, then waiting_input; it never becomes a PASS or an automatic Goal failure.
- Pause is user-only from queued/running. Resume only paused. Input answer must match current question ID and epoch; dedupe returns original result.
- Crash recovery is an explicit supported startup operation, never a side effect of creating each Store handle. Abandon orphaned Attempts, bump epoch, requeue within persisted budget; exhaustion waits for input. External ambiguous intent remains unknown, never automatically retried.
- Forget disables raw AI references and all affected derived notes; recheck full context manifests before publication. Incidental context requeues; explicit task/criteria source loss waits for input. Do not overload user pause.
- SQLite per-operation connection/transaction, FK/timeout/FULL each connection, WAL, schema-version guard; immutable criteria triggers; unique global running-slot index; dedupe includes canonical payload hash plus original result; outcome unique per Attempt.
- Goal transition and event transactionally coupled. Durable local report uses unique source_event_id and marks delivered in same transaction; external push deferred.
- Tests terminate real subprocesses mid-transaction and after commit, not merely simulated exceptions.
Rejected: auto-pause on forget, unverified => failed, unbound input answer, generic state-update API, unbounded crash retries.
Artifact representation remains under a short follow-up review: SWE recommends transactionally stored SQLite blobs while Opus described filesystem atomic staging. No artifact implementation until resolved.
Stack: stdlib only; this honors the explicit user requirement over SPEC's optional FastAPI/pytest preference. Native official provider CLI is the authorized route; no new API credentials.

## D-012 — Atomic bounded draft evidence
Date: 2026-10-06
Question/response: [Opus follow-up](evidence/reviews/s1-artifact-question.txt), [answer](evidence/reviews/s1-artifact-response.txt).
Adopted: SQLite blobs and host-issued opaque artifact IDs, bounded small draft buffer, strict UTF-8, no BOM/NUL, host hash of inserted bytes, host receipt and blob in one fenced transaction; immutable update/delete triggers. No scratch paths or staged unbound artifacts are exposed/created, so filesystem/symlink staging and GC races are eliminated by construction. Size/encoding rejection is retained as host rejection evidence; never truncate to meet acceptance. Receipt readback/hash/bounds rechecked before completion.
Forget remains reference stop, not byte deletion (D-006). Published evidence bytes/receipts remain inspectable; never feed audit/artifacts automatically into conversational memory. No secure erasure is claimed. This selects Opus C8's explicitly retained-evidence option. Derived export files are not canonical evidence.

## D-013 — Two lanes, atomic ingress and bounded result contracts
Date: 2026-10-06
Question/answer: [runtime proposal](evidence/reviews/s2-swe-question.txt), [SWE-2 High review](evidence/reviews/s2-swe-response.txt).
Adopt before runtime implementation:
- Message Record + explicit draft handoff/Goal + ingress dedupe in one host transaction; ordered persistent outbox.
- One task thread, independent conversation pool; no provider call inside a Store transaction. Global task slot enforced by database; process-lifetime nonblocking flock prevents a second host/recovery racing a live worker.
- WorkOrder is immutable data only; response must echo Goal/Attempt/epoch. Host rejects unknown action/extra canonical-state fields/wrong types with terminal capability_violation. Product Executor has no shell/filesystem/store capability.
- All result, receipt and Responder publication transactions recheck context manifest usability.
- Pause/cancel fence results rather than promise synchronous preemption of arbitrary threads. Shutdown stops provider process groups; native calls use stdin, bounded output/timeout, tool-free route, minimal environment and no paid fallback.
- Error/capability violations terminate rather than loop; repeated unverified signatures escalate to a diagnostic input question. Budget still limits every claim.
Rejected SWE suggestion 7: canonical unknown is NOT read-only validation fallback. D-011/Opus require persisted unknown for durable external-effect ambiguity; this newer reviewer suggestion conflicts with accepted semantics and is not adopted. No real external effect capability is exposed.
Verification: Event/barrier concurrency tests; disposable-DB fault tests; second-host lock test; native provider isolation/cancellation tests. Additional caller/model constraints are implementation enforcement, not scope reductions.
