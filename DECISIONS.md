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

## D-014 — Official tool-free route and UI evidence
Date: 2026-10-06
Implemented within reviewed D-011–13 contracts: official existing Claude Pro route, fresh no-additional-charge proof expiring after 15 minutes, native auth rechecked under the same scrubbed OS identity environment, model tools empty, safe-mode, MCP empty, no API-token/config override inheritance, no paid fallback or saved model sessions. Process-lifetime supervisor pipe kills/reaps native process groups after timeout/shutdown/host SIGKILL. Native text generator uses a text-only system prompt/default permission mode; reviewer plan mode is not a product contract.
Evidence: [clean real smoke](evidence/live/2026-10-06-clean/result.json), [actual draft](evidence/live/2026-10-06-clean/draft.txt), [host evidence](evidence/live/2026-10-06-clean/host-evidence.json). Prior [failed](evidence/live/2026-10-06/failed-result.json) and [partial planning-transcript candidate](evidence/live/2026-10-06-verified/result.json) remain visible; neither counts as PASS. Causes/prevention: [defect record](docs/DEFECTS.md).
UI: loopback only, exact Host/Origin, JSON/size bounds, textContent/CSP, conversation and read-only inspect; browser/readback evidence in evidence/ui. UI default is mock; real provider proof is the separate live path. No new auth, payment, grant, public route or unrelated-project mutation.

## D-015 — Lost ACK and original request dedupe
Date: 2026-10-06
Question/implementation review: [SWE-2 soak review](evidence/reviews/soak-swe-response.txt), item 1.
Adopted: read-only operation fate lookup by client key. Dedupe hashes original sanitized client request, not host-resolved natural-language routing fields that may change on retry. Replay returns original target/ACK; different client payload conflicts. Atomic Record/Goal/outbox boundary unchanged. Natural forget regression verifies target binding.

## D-016 — Faithful soak gate and human participation
Date: 2026-10-06
Question/answers: [Opus question](evidence/reviews/soak-opus-question.txt), [Opus response](evidence/reviews/soak-opus-response.txt), [SWE question](evidence/reviews/soak-swe-question.txt), [SWE response](evidence/reviews/soak-swe-response.txt).
Adopt before monitor implementation:
- Scripted fixture turns cannot satisfy user-turn/Goal/control minimums. Required human participation: >=20 typed UI turns, >=3 distinct sessions whose first/last span >=72 hours, >=5 human-created Goals, >=1 human cancellation, >=1 human correction or reference-stop. Only the human may attest those sessions/receipts. UI key namespace/session receipt corroborates identity; a label alone does not prove human input.
- Supported planned restart while unfinished may be scripted and must prove abandonment/fencing, resumed same Goal, lost-ACK reconciliation, no second completion/report. An unplanned death does not count as the required planned restart.
- Mock-adapter host-stability soak is allowed; no live-provider reliability claim follows. S0-10 live smoke remains separate. Bounded mock task latency is host configuration for control/restart exercises; default remains zero and no product time-wake feature is introduced.
- All S0-01–12 PASS and clean baseline commit before clock starts. Baseline includes tracked runtime/store/schema/adapter/UI, probe semantics, Python version and declared provider config. Source/probe-semantic changes, detected invariant failure or repairs require a new run; docs/evidence-only changes do not.
- Separate monitor; readonly SQLite mode=ro/query_only, public HTTP, fsync/hash-chained measurements every five minutes with UTC + CLOCK_UPTIME_RAW, app PID/start, boot time. Disclosed sleep is downtime, not uptime. Unexplained >15-minute gaps and clock discontinuities fail/reset; planned supported restarts are logged. Sleep/wake records are filtered to this run. No DB repair or fabricated host receipts.
- Count only attested UI sessions; retain expected accepted keys/IDs and reconcile against canonical state. A candidate cannot declare Stable-0; controller still performs final full suite/acceptance audit/master issue closure.
Rejected: counting synthetic traffic as human use; arbitrary SWE downtime allowances (6h/4h) without accepted basis; SWE statement that secret canary may legitimately persist (S0-09 explicitly requires sanitation before persistence); treating reviewer text/claims as product evidence.
Opus claimed a global plan artifact in its response; exact named path stat showed it did not exist. Use repository-captured response only, not the model's artifact claim.
Current blocker to autonomous completion: required human participation. A fully scripted substitute would alter accepted evidence meaning and needs explicit user judgment. Prepare concrete UI, monitor and green evidence before asking.

## D-017 — Concrete soak monitor implementation review
Date: 2026-10-06
Question/answer: [concrete code](evidence/reviews/soak-monitor-swe-question.txt), [SWE-2 High findings](evidence/reviews/soak-monitor-swe-response.txt).
Adopt before implementing follow-up fixes: candidate/attestation digest bound into the fsync chain, atomic JSON exports, final controller-audit path, transient attestation parse error remains inspectable/pending, restart armed for an explicitly attested session, host-observation interval bounds for human span, measurement cadence checked in awake time with disclosed sleep, immutable-row fingerprints and DB inode identity, reverse pass/outcome/Goal and receipt/Attempt invariants, new recovered Attempt ID and original/replayed ACK digests, percent-encoded operation keys. One short retry only for transient transport/SQLite busy errors, never for invariant violations. Baseline scope is app/probe source + Python/SQLite + declared mock configuration; docs/evidence-only changes remain non-resetting.
Rejected finding 1: canary is NOT legitimately persisted raw. S0-09 and D-016 require sanitation before persistence; actual preflights completed with DB/WAL scan PASS. Keep the DB/WAL scan, not the proposed exception. Restart minimum is at least one, not a maximum of one. Routine supported restarts do not become defects just because there is more than one.
Finding 2's stop invalidation was already partly corrected before the response arrived; anchor candidate and audit events so historical verification remains possible after orderly final completion. A live candidate still cannot declare Stable-0 by itself.

## D-018 — Personal-use acceptance reconsideration (PROPOSED, NOT ADOPTED)
Date: 2026-10-07
Direct user instruction in controller chat: 「長期利用ってそんなに大事？そこまで重たく感じてないんだけど、まずは動作が完全に期待通りになることが優先では？Opusはなんて言ってる？個人利用だよ？」 followed by 「OpusとAstraで協議してあなたが受け取って」.
Question/answers: [Opus initial reconsideration](evidence/reviews/personal-use-reconsideration-opus-question.txt), [response](evidence/reviews/personal-use-reconsideration-opus-response.txt); [Astra independent source review and reconciliation](evidence/reviews/personal-use-reconsideration-astra-response.txt); [Astra challenges returned to Opus](evidence/reviews/personal-use-reconsideration-opus-followup-question.txt), [Opus follow-up agreement](evidence/reviews/personal-use-reconsideration-opus-followup-response.txt). [Fresh official existing-auth/no-extra-charge verification](evidence/reviews/personal-use-reconsideration-access.txt). Official tool-free Opus calls; user-selected gpt-6-astra/high independent agent. No paid fallback/new login/settings change.
Both reviewers agree functional expectations come first for personal use. Prior D-016 Opus prompt explicitly required preserving the existing gate; its answer interpreted that gate and rejected falsely counting synthetic human traffic. It did not independently establish that 72h or the turn/session quotas are necessary. Controller previously promoted gate compliance as the next priority while meaningful real-provider UI functionality remained unverified; correct that prioritization subject to the user's explicit adoption of a changed completion definition.
Observed source/evidence: server.py always uses MockProvider; ordinary mock response is fixed and mock draft echoes the request. S0-10 live smoke explicitly has quality_claim:none and checks transport/host artifact validity, not requested meaning. Existing S0 PASS claims retain their structural scope; they do not prove useful personal assistant semantics. Further mock turns/time cannot close this gap.
Smallest consensus proposal for ONE user adoption:
- Prospectively revise Stable-0 to require both existing structural/security/canonical/recovery acceptance and a bounded real-provider UI functional acceptance set fixed before execution.
- Keep existing canonical host-only state, fixed acceptance, idempotency, stale fencing, cancel/correct/forget-reference-stop/resume, sanitation, visible failure and no-extra-charge official-auth boundaries. No protection is weakened.
- Keep mock DEFAULT. Add only explicitly selected, bounded real-provider UI using the already-authorized official route and fresh no-extra-charge proof. No unattended always-on native calls/new auth/paid fallback/public exposure/deferred features.
- Finite functional set: ordinary conversation without unwanted Goal; remember/recall synthetic non-secret fact; context-grounded local draft with specified content/constraints; correction superseding old fact/request; forget stopping model references while raw history remains inspectable; canonical status plus cancel/pause/input-resume explanation. Automate structural/content constraints where meaningful; user judges actual usefulness once for the fixed scenario set. Existing fault/recovery tests remain required. No LLM self-report is evidence.
- Remove only 72h / 20 human turns / 3 sessions quotas as mandatory completion gates; keep optional long-term observation, never relabel old S0-13 unmet evidence PASS. No assertion of long-term stability follows functional acceptance. Preserve all historical runs, hashes and human confirmations.
- SWE-2 High must review concrete real-provider UI/access-expiry/failure contracts before substantial implementation. Use existing commit/diff and affected checks; uncertain impact requires conservative revalidation.
Rejected after actual exchange: Opus's initial new Personal-Usable-1 label, repeated P0/P1/P4 approvals and user-only completion declaration, new dependency-hash framework and mock-only-for-tests default. Astra challenged these and Opus conceded. Opus's lease/backoff examples were not verified current mechanisms; actual timing contracts are AccessProof 15min wall-time freshness and native monotonic deadline. SIGSTOP/SIGCONT is not sleep/wall-clock-jump evidence. Verify actual contracts at implementation review; no new time-testing framework solely for generic examples.
Decision status: consultation completed; consensus recommendation recorded, NOT adopted or implemented. The latest user requested deliberation, not removal of the original explicit 72h completion rule. One explicit user adoption is required because this changes Stable-0 definition (original user Completion rule and D-010/D-016/AGENTS stable-declaration rule), not because of a routine technical choice. Until adoption, existing ACCEPTANCE rows/gates remain in force and Stable-0 incomplete. Current monitor/evidence retained unchanged. Next action: present concise consensus and obtain this single completion-definition decision, then record adopted/rejected decision before implementation. No repeat participation quotas requested during this deliberation.
Verification: [55-test full suite](evidence/tests/personal-use-reconsideration.txt); unchanged runtime/probe baseline, valid 21-record hash chain and fresh measurement observed during consultation. Docs/reviewer evidence only; no canonical repair, no soak reset.

D-018 final Astra assent: AccessProof already uses time.time(); no monotonic-only TTL defect established. Fixed scenarios prevent post-hoc greenwashing, not legitimate evidence-preserving revisions followed by revalidation. Require concrete draft content fit as well as human usefulness.
