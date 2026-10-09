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

## D-019 — Adopt functional-first Stable-0 (supersedes D-010/D-016 time quotas)
Date: 2026-10-07
Direct user adoption in controller chat: 「合意した内容をもとに、この合意案で完成条件を改定して、実機能への実装を進めていってください。もしゴール設定の変更が必要であれば、その変更もしておいてください。」
Adopted: D-018 final Opus/Astra consensus, before implementation. Revised Stable-0 requires existing security/canonical/recovery safeguards AND precommitted finite real-provider UI functionality/content evidence plus one direct human usefulness evaluation. Mock remains default; real UI is explicit and bounded via existing official no-extra-charge auth proof. No new auth/cost/public scope or deferred features. SWE-2 High review required before substantial implementation.
72h / 20 turns / 3 sessions are optional observation, not completion requirements. Historical S0-13 remains NOT PASS under its original criterion; it becomes a nonrequired historical row, never falsely promoted. Existing runs/DB/logs/receipts remain preserved. Development changes require closing the old baseline observation honestly; no clock transfer or row repair. Structural checks cannot substitute semantic functionality, and human usefulness cannot substitute structural safety. New functional rows are pending until actual evidence; final suite/audit/master Issue closure still required.
Scenario set is fixed in ACCEPTANCE.md before live execution. Legitimate later revisions retain old failures/rationale and rerun affected evidence. No additional approval per scenario or new label.
Controller objective: deliver this revised Stable-0 autonomously. App goal update attempted: create_goal rejects replacing unfinished blocked objective; update_goal supports status only. Do not mark unmet old goal complete merely to replace its text. Repository goal/STATE and operational follow-up carry latest objective; original app card is stale metadata and its 72h wording is superseded by this direct user adoption.

## D-020 — Bounded explicit official-provider UI contract (adopted before code)
Date: 2026-10-07
Reviews: [focused SWE-2 High contract](evidence/reviews/real-ui-swe-focused-question.txt), [response](evidence/reviews/real-ui-swe-response.txt), [diagnostic](evidence/reviews/real-ui-swe-diagnostic.json); [Opus boundary challenge](evidence/reviews/real-ui-opus-boundary-question.txt), [answer](evidence/reviews/real-ui-opus-boundary-response.txt). Fresh official access captured alongside questions. First large SWE call failed without response; [honest diagnosis](evidence/reviews/real-ui-swe-first-failure.json), not PASS. Reduced contract plus captured diagnostics returned official SWE-2 High review successfully.
Adopt: explicit startup provider/proof/call-limit, mock default, reject invalid/mixed flags before Store; strict bounded regular nofollow UTF8 proof JSON, exactly verified_at/no_extra_charge/route, no duplicates/nonfinite/bool timestamps or truthy cost fields. Metadata issued only by operator after actual official UI/auth check, not web/model self-authorization. Fresh proof expires by either wall age or independent monotonic remaining deadline; future dates fail closed. One-use canonical-value hash marker O_EXCL with nofollow dirfd, owner/mode check and file/directory fsync. Hash normalizes numeric timestamp representation. No marker deletion/refund/reuse; startup failure burns valid proof, fresh check required.
Choose Opus's explicitly offered repository-local alternative: marker root runtime/native-proof-use, guarded per CHECKOUT. No new per-user external writable directory or permission. This task uses only this checkout. Marker is a trusted local-operator guardrail, not cryptographic evidence or a cross-checkout/global-account limit; an operator can deliberately remove/forge it. Disclose limitation, do not claim unconditional global boundedness.
Single shared NativeClaude instance for task/conversation lanes; default16, maximum32 reserved generation INVOCATIONS per proof/host; atomic reservation then release lock before I/O. Failed calls/expired-after-reservation consume slot. Pure read-only status exposes safe closed error codes/budget/expiry, no auth or proof reread. Auth status and model subprocesses lifetime-supervised for shutdown/host death, no paid/model fallback. Calls admitted before expiry may finish within120s; maximum admission-window plus admitted generation deadline1020s (auth has separate10s bound and proof is rechecked after auth).
Reject SWE suggestion to kill shared provider on per-Goal cancel: D-013 fences rather than preempts arbitrary threads; shared kill would interrupt independent conversation. Cancel/pause fences persist, admitted slot never refunded; bounded wasted call possible. Host shutdown/death kills all auth/model subprocess groups.
Reject Opus's SDK retry/one-HTTP-request claim as inapplicable/unverified: this uses official Claude CLI, no Anthropic SDK transport is exposed. Budget bounds host generation INVOCATIONS, not internal HTTP attempts/token refresh; CLI internals are not independently proven retry-free. Existing official creditsOFF/no-extra-charge proof and no fallback remain mandatory; no new paid API/SDK route introduced.
Proof expiry/exhaustion causes visible recorded conversation failure or terminal failed Goal, no automatic retry/renewal/mock substitution. Operator verifies fresh route and explicitly restarts with a fresh proof; failed Goals do not silently resume, new explicit request/Goal is required. Existing recovered pending Goals still follow canonical recovery and their provider errors remain visible.
Verification plan: strict schema/marker replay/numeric forms/symlinks; concurrent budget and pure status; expiry before auth/after reservation/clock rewind/jump/sleep age; host shutdown during supervised auth; startup invalid-before-Store; existing canonical/crash/fencing suite plus actual live UI fixed F0 scenarios. No credential storage, canonical schema mutation or deferred scope.

## D-021 — Next milestone: Stable-1 natural local delegation (adopted scope, not implemented)
Date: 2026-10-07
Direct user instruction: 「次はstable-0が最終ゴールからどのポイントか、次の作業項目を整理して次のマイルストーンを設定しよう」. Authorizes positioning, task organization and milestone setting; this increment does not claim runtime implementation or automatically activate later deferred work.
Question: What is the smallest next milestone toward a personal assistant that handles conversational requests without requiring the user to manage internal tasks? [Concrete source-grounded Opus question](evidence/reviews/stable1/opus-question.txt), [official response](evidence/reviews/stable1/opus-response.txt), [fresh existing Pro authentication and extra credits OFF](evidence/reviews/stable1/access.txt).
Opus conclusion: Stable-0 proves a bounded useful durable core, while phrase-triggered ingress and latest-Goal targeting leave a conversational delegation gap. Split the proposed missing-content clarification feature out: first distinguish request/non-request and safely resolve correction/cancel targets, then reuse target bindings for later answers. Preserve fixed criteria, host-only canonical writes, recovery, bounded official provider and explicit forget.
Adopted: Stable-1 = natural Japanese local-draft request recognition plus safe correction/cancel targeting. Ambiguous operations ask a target-selection question or make no change with an explanation; never guess the latest Goal. A uniquely named target or explicit host-issued ID can resolve without a routine question. Existing English single-target controls remain supported. External-send-only or combined draft-and-send requests create no Goal and explicitly explain the unsupported action; the user may separately request a local-only draft. No silent omission of sending. No new capabilities or memory retrieval architecture.
Prospective gates: zero false-positive Goals in the frozen non-request matrix; at least15/16 explicit draft requests recognized, every miss visibly safe; zero wrong-target mutations in mixed-state0–3 Goal fixtures and stale/cross-target probes; supported process-kill recovery of pending target selection and correction with fixed criteria/dedupe/outbox/fencing preserved; bounded real-provider UI proof, no unsupported fact invention in fixed absence probes, one actual direct human usefulness evaluation of the new flow, full regression and final audit. All new rows start NOT_RUN; Stable-0 evidence/status remain immutable in meaning.
Adopted with a proportionate adjustment to Opus's held-out proposal: use12 independent reviewer-controlled utterances, frozen before implementation and withheld until the candidate is fixed; zero false-positive Goals is required and request recall is reported. Do not require the human to author15 utterances or add participation/time/session quotas. Human supplies only the actual usefulness judgment that automation/review cannot supply. Distinguish finite corpus coverage from arbitrary-language correctness.
Deferred direction: Stable-1.1 content clarification, then evidence-driven memory/reversible-preparation improvements and separately scoped integrations/proactive behavior. These are candidate directions, not adopted implementation scope or guaranteed release definitions. No always-on operation, proof auto-renewal, 72h requirement, natural-language forget expansion, PublicSearch, scheduled wake, dreaming, multi-Expert, vectors, local inference, automatic procedure update, external send/push, arbitrary shell/repo/browser tools.
Implementation contracts are deliberately undecided: classification rules/proposal schema, target resolution and persistent selection bindings, recovery representation, corpus/live harness. Obtain fresh official SWE-2 High concrete contract review before substantive code and Opus review for resulting semantic/boundary changes. No reviewer opinion counts as functional evidence. [Unchanged baseline66 tests PASS](evidence/reviews/stable1/baseline-tests.txt).

## D-022 — G-001 project/milestone/issue loops; P-001 proposed overall plan
Date: 2026-10-07
Direct user instruction in development chat: 「最終ゴールを全体のゴールとして、githubマイルストーンを活用してください」「project milestone issue この関係性です」「まずは現在時点の全体の開発計画を立案し、チェックポイントごとに計画を評価して、必要な時には開発計画を変更する。その際はopusと議論をして合意したものを発案して人間判断により変更確定とします」.
G-001 ACTIVE by that direct instruction: project goal → GitHub milestone goal → goal-bearing Issues/work units; implementation/verification/evidence loops at each level. Unit, Issue, milestone and triggered anomaly checkpoints evaluate their own goal and contribution to the parent. Closed children alone do not prove the parent. Material plan/scope/acceptance/priority changes require Opus agreement and an evidence/version-bound proposal finalized by actual human decision. Routine within-scope implementation choices remain autonomous. Human can explicitly amend this governance; Opus is a review gate under the current user rule, not a veto over the owner.
Opus consultation: [first concrete question](evidence/reviews/project-plan/opus-question.txt), [challenges](evidence/reviews/project-plan/opus-response.txt), [six-point revised proposal](evidence/reviews/project-plan/opus-followup-question.txt), [AGREED, no blocking regression](evidence/reviews/project-plan/opus-followup-response.txt). Fresh official existing-auth/extra-credits-OFF proof recorded for both calls. Reviewer uses official CLI model alias opus; exact backend model version not exposed. Codex drafted; separate tool-free Opus reviewed. Follow-up explicitly lacked the first review context and agreed only to the stated delta; controller checked it against the saved first response, with no contradictory requirement adopted.
Adopted operational governance: sole project-level application goal, GitHub global goal Issue and milestone/Issue objective+acceptance+dependency+work-unit+evidence+checkpoint fields. A GitHub Projects board is not required to perform these existing-authority operations and is not claimed created. Future milestones may be registered PROPOSED with no dates/assignees and must never be selected as ACTIVE work.
P-001 v1 PRODUCT PLAN: PROPOSED, NOT ADOPTED. [Frozen plan](docs/plans/P-001-v1.md), [content hash/review/empty human decision](evidence/reviews/project-plan/proposal.json). Proposed PAL-1.0 includes user-initiated local preparation3a; system-initiated topics/time wake3b are separate optional extension. Initial broad plan remains HR-PLAN-001 human_pending; initial setup and permission approval are not future-scope adoption. Preserve D-021 Stable-1 ACTIVE and its acceptance; do not absorb missing-content workflow into it. Future numeric context/budget/probe gates freeze before execution, never post-hoc. No runtime/DB/schema/model prompt/capability changes.
Latest user steering: 「ゴール設定に必要な権限は私の承認のみであれば承認します。作業を継続してください」. Applies to necessary goal-management permissions, NOT P-001 product-plan adoption. Existing gh lacks Projects scope; official project-scope refresh initiated after this direct approval, Git credential settings declined. HR-PERM-001 requires actual human GitHub device authorization and safe scope readback before Projects board creation. Temporary login code is not stored in repo/evidence. Existing Issue/milestone planning and D-021 work remain independent. No paid fallback, new public exposure or stopped-schedule restart.
Verification: [unchanged66-test baseline PASS](evidence/reviews/project-plan/baseline-tests.txt). Checkpoint C-000: hierarchy/authority/plan review baseline; product implementation N1 remains NOT_RUN, global goal remains incomplete. Detailed future acceptance is prospective until adopted/scoped at milestone entry. On any future plan change, preserve this version and evidence, get Opus agreement, hand off a targeted human proposal, then activate only after direct adoption.


## D-023 — Stable-1 Issue3 host classification contract (adopted within D-021)
Question: distinguish affirmative local-draft requests from discussion, quotes, negation/deferral and requested external effects without additional model calls, schema, tasks or permissions; preserve duplicate/restart semantics. Questions/answers and fresh official no-extra-charge proofs: evidence/reviews/stable1-classification/{swe,opus}-{question,response}.txt and access files. Official SWE-2 High: adopt with corrections; official Opus: approve with required corrections. Reviews actually ran in parallel; synthetic heldout12 generated by official Opus before implementation, hash sealed/unopened in heldout-freeze.json.
Adopt: pure versioned normalized classifier; exact controls first; frame-level record-only/report/hypothetical/meta decline; quoted content masked for both request/effect detection; clause-specific prohibitions; affirmative agent external-effect request rejects whole request; affirmative local-document request creates one Goal; uncertainty never creates work. First-person desire/report/old-draft edit does not create Goal. Request-time deferral differs from payload date. Conservative finite patterns and explicit limits, not full natural-language understanding.
Reconciliation: SWE bare quoted imperative example A16 conflicts with Opus quote-only demotion; adopt Opus conservative conversation outcome, never execute/request effects from quote-only text. Frame-level decline wins over send inside that frame. Keep original sanitize/dedupe identity unchanged; NFKC/casefold/invisible removal are classifier matching copies only. Do not equate distinct original ingress payloads by normalization.
Replay correction: persist classification+version in existing remembered ingress result JSON, in the same existing transaction as record/Goal creation; no DB migration/schema change. Stored outcome and stored reply always dominate current grammar. Historical results without classification retain their historical effect; never reinterpret into new Goals or unsupported claims. Fixed bilingual unsupported host reply is persisted with existing host assistant-record/dedupe path: host observation, NOT artifact/tool evidence or model attestation; no claim of atomic response+ingress, gap safely reconstructed from persisted outcome. Existing ingress rollback/epoch/outbox contract unchanged. Singleton non-draft/non-external requests stay conversation; compound draft plus unclassified action fails closed. No new capability or essential-content question engine.
Frozen40cases remain unchanged; controller-authored edge cases supplement them. Baseline pure diagnostic10/16 request matches,6/24 false positives; canonical/replay red failures preserved. Scope/acceptance unmodified; full N1 and live/human gates still required, not yet PASS. P-001 future plan remains human_pending.
Latest direct user authorizes multi-vendor parallelism via CO0.3 stable, maximum32 total, not32 Codex workers. Respect actual available slots/cost/auth, isolate writes. Official reviewers used in parallel; installed co help identifies a Codex wrapper, CO0.3 runtime not verified, AGY available but no fresh cost proof so not used. No CO/other-project modifications; no invented delegation claim.

## D-024 — Stable-1 Issue4 persistent host target selection (adopted contract, NOT implemented)
Question: natural correction/cancel across0–3 mixed-state Goals with safe literal cue or durable button choice; transaction/replay/crash/forget safeguards and fixed criteria. [Concrete question and official SWE answer](evidence/reviews/stable1-targets/question.txt), [SWE](evidence/reviews/stable1-targets/swe-response.txt), [Opus](evidence/reviews/stable1-targets/opus-response.txt), [actual-code reconciliation](evidence/reviews/stable1-targets/followup-response.txt). Fresh existing-auth/no-extra-charge checks precede each review; no paid fallback/new auth. Initial Opus and SWE reviews ran in parallel; no reviewer wrote code.
Both recommend one minimal control_selections table instead of mutable dedupe JSON. Adopt: immutable host proposal, random selection_id, source_record_id/source ingress key/action, snapshot choices(goal ID/revision/epoch/state/sanitized truncated label), original correction text, consumed_by. Dedupe stays immutable. Current Store already uses BEGIN IMMEDIATE/busy_timeout5000; do not add another transaction framework. Resolve/apply/consume and fixed host question/outcome record in existing ingress transaction; no model calls. Exact original choice key replays stored result before fresh binding checks; other attempts on a resolved selector return fixed already-resolved. Bound staleness/unavailability resolves once, not blind retry.
Scope reconciliation: current Store is one canonical conversation stream, no canonical conversation_id namespace. Bind to Store plus exact selection_id/source_key/offered target_id, generic rejection for unknown/mismatched/foreign fields. No new auth or multi-user routing. Literal cue normalized/casefold/exact-substring over eligible targets; unique applies, zero matches fixed no-target, multiple matches asks selection, never latest/ranked/fuzzy. Above3 choices requires a narrower cue, never first3 guess. Exact English correction/cancel retain single-target behavior; ambiguous multi-target latest-pick is intentionally removed under D-021. Pause/resume/epoch-bound answer baseline preserved. Natural control takes precedence over content answer, typed ordinals never consume a selector; buttons are the binding path. No TTL, model matching, content-missing workflow or new task types.
Actual claim/recover DO increment epoch. Strict same revision/epoch/current eligibility therefore rejects choices after claim/recovery. Prior Opus hypothetical claim-without-epoch-change statement is superseded by followup agreement. Record this STALE-heavy usability cost; do not loosen fencing. Unknown/stale/cross-target decisions do not mutate any Goal or acceptance; selected correction uses stored operation/text, never caller-supplied action/criteria/specification.
Opus blockers reconciled before code: A is a mandatory replay/display/apply test gate — gate source and every target revision's sources via _usable; never emit copied labels/correction text unchecked. Keep ingress/dedupe result free of correction text and prefer selector IDs only; fixed question has no copied task text; live choices are a guarded projection. B/C actual Store._forget at lines412–422 only sets usable=0, disables derived notes and fences affected work; it does NOT DELETE/scrub rows. Therefore retained raw proposal is inert after source forget and FK without cascade does not obstruct current soft-forget; no stronger retention claim. A implementation proof remains NOT_RUN, not closed by review opinion.
Correction provenance conformance: current _control writes revisions.sources=[]; natural/selected corrections must cite the original text-bearing user control record. Explicit host ingress adds its real user record; direct Store.control remains sourceless unless genuine source supplied. No fabricated source or expanded retrieval; criteria unchanged. This makes existing forget/reference-stop effective for corrected specifications. Additive schema1->2 startup transaction retains old rows and refuses unknown future versions; v1 binary refuses v2 database, so preserve v1 data for rollback. Do not migrate original/soak/live DB now; exercise disposable fixtures before controlled candidate UI.
[Nine semantic fixture cases](tests/fixtures/stable1_target_matrix_v1.json) frozen, NOT_RUN. Must additionally prove concurrent double-click, wrong-source/target/key conflicts, forgotten source/label projection, deterministic claim race, selector replay after consumption, process kill before/after selector and correction commit, source-tracked forget and schema migration before N1-03/04 PASS. No material plan change; D-021 authorized, P-001 still human_pending.
## Operational collaborator ceiling — direct human steering, 2026-10-07

Human explicitly authorized up to32 parallel workers across vendors using the
CO0.3 stable workflow, naming Codex/Claude/Devin/AGY. This is an overall upper
bound, not32 native Codex slots or authority for paid fallback/new authentication.
Actual official Opus and SWE-2 High text reviews ran concurrently; Codex separately
performed a bounded read-only target exit audit. Controller remains sole writer.
The installed `co` entrypoint advertises a Codex launcher; stable multivendor worker
control was not verified, so no CO runtime/AGY execution is claimed. Existing AGY
no-extra-charge proof is absent, so it was not invoked. Accepted project scope,
cost/security and human judgment boundaries remain unchanged. This operational
allocation does not change product roles or enable multi-Expert behavior in PAL.
## D-025 — Stable1 Issue5 bounded real verification contract (adopted, NOT_RUN)

Question: challenge fixed planted-absence and actual Japanese target UI tests,
budget/provenance/races and independent human usefulness under existing D021.
Official Opus initial/followup and official SWE-2 High source-contract reviews:
evidence/reviews/stable1-targets/issue5-*-response.txt with fresh auth/cost proofs.
Opus followup confirms test-only clarification, explicitly limited to restated
D021 rather than independently reading prior context. SWE independently read the
current relevant source and approves with eight concrete corrections. Controller
checked against canonical D021; no product completion gate changes, new authority,
missing-content engine or P001 adoption.

Adopt frozen tests/fixtures/stable1_real_ui_v3.json/hash in issue5-v3-freeze.json;
v1/v2 retained. Two actual finite A/B/C samples each in separate disposable DBs.
Omitted fields/placeholders permitted; invented particulars FAIL, question-artifact
FLAG/notPASS, no favorable resampling. Grounded context only through genuine host
ingress; missing manifest VOID, output invention with supplied context FAIL.
All negative/FLAG/VOID retained; human rubric frozen and authentic evaluation
required on the new evidence/version, never the Stable0 answer.

Prefer existing pal.server, not a new shared-provider/capture harness. Eight frozen
host slots: A1/A2/B1/B2 each2, C1/C2 each3, FLOW1=12 and FLOW2_VOID_ONLY=6;
existing per-host enforced invocation ceilings sum32 suite-global. Each launch
requires a fresh existing-subscription operator check and new one-use D020 proof;
these are distinct frozen DB scenarios, not automatic renewal of an expired host.
No extra hosts/proofs or redistributed cap; no paid fallback. FLOW2 only replaces
a timing-VOID setup within max2 attempts, never FAIL/FLAG/expiry/error. Already
started calls may finish after expiry; no new admission then. Retain actual counters.

Interleave actual UI create→typed pause→create→typed pause; confirm paused/epochs.
Neutral self-contained correction payload does not misleadingly name its target;
host asks persistent selection and actual rendered button applies to chosen Goal.
Selected revision+1/epoch+1, unchanged criteria/source original correction record;
subsequent claim adds1 epoch (net+2). Unselected has no new claim/Attempt/receipt
since pre-selection snapshot, preserving legitimate historical fenced attempts.
Maple must actually be running before unfinished cancel; late rejection ordering
bound to host event/Attempt, otherwise honest incomplete/VOID/unverified. No delay
hooks or DB repair. Duplicate/stale safety remains separately deterministic-tested.

Exact manifest-bound prompt reconstruction is sufficient; label reconstruction
and sanitized returned artifact bytes honestly, no raw stdin/stdout capture or
wire claim. New loopback ports/DBs, preserve Stable0 process/DB and all oldsoaks.
Known limits include finite language corpus, strict stale-heavy selections,
per-proof guardrails, unknown actual alias model version/provider internal retries
and hidden personalization. Minimal demonstrated-invention prompt repair would
need required review/recorded candidate; missing-content operational flow is
deferred Stable1.1 and needs actual adopted scope. No human routine-choice ask.

## D-026 — Demonstrated unsupported causal-benefit repair and one finite corrective cycle

2026-10-07, Issue5/N1-05, candidate6ee436f first-run C1 FAIL. [Question and exact evidence](evidence/functional/stable1-20261007/defect-review-question.txt), [official Opus](evidence/functional/stable1-20261007/defect-opus-response.txt), [clarified standing-authority followup](evidence/functional/stable1-20261007/defect-opus-followup-response.txt), [official SWE-2 High source/contract review](evidence/functional/stable1-20261007/defect-swe-response.txt); all fresh existing official no-extra-charge access proofs retained. Six invocations are4 A/B drafts plus C1 remember conversation + C1 draft; no hidden retry. Independent Codex evidence audit corrected observer reconstruction format, source/artifact FAIL unaffected.

Both official reviewers agree FAIL: supplied design-discussion organization does not establish smooth progress or causal benefit. Minimum existing-grounding enforcement adopted BEFORE code: explicitly prohibit stated/implied effects/results/benefits/impact incl hedging unless stated in context/request, thank supplied action itself, allow writer gratitude, omit missing details; retain supplied facts/language/name/sentence constraints. Reject Cedar/Mika example contamination, new missing-content workflow, criteria/rubric changes and new placeholder instruction. Existing explicit placeholders remain acceptable. This is accepted N1-05 repair under D021/D025, not a product/safety/overall-plan change. Opus relies on supplied canonical excerpts; SWE independently read actual source/decisions. Model agreement does not supply human acceptance.

Standing autonomous repair/verification authority supports exactlyONE corrective candidate cycle: new committed version/new DBs/new exact preflight, unchanged frozen v3 inputs/rubric, fresh existing Pro/no-extra-charge per-slot proof, same32 total fixed caps as a ceiling not a target, fail-stop. First-run unused slots die; no carryover/reallocation/replacement/expiry renewal/fallback. Label run2, cumulative usage6+run2; all retained negative/FLAG results go into authentic N1-07 evaluation packet. No prior PASS counted for new candidate. Choose stricter reviewer threshold: any repeated unsupported-outcome FAIL in corrective run escalates for diagnosis/human decision BEFORE another autonomous candidate, not blind retry (SWE suggested third-candidate threshold, rejected in favor of Opus second-run threshold). New payment/auth/permission/public exposure or accepted behavior/criterion change also stops. P001 not adopted by this operational correction.

Implementation/testing/live result remains pending; instruction-text presence is not semantic proof. Existing92 pre-repair tests PASS, actual FAIL preserved. No existing production host/DB write or migration.


D026 verification: committed candidate605791e completes one finite corrective run2, unchanged frozen v3 suite:6/6 planted-absence samples PASS; actual two-target correction and unique/running cancellation PASS. First FAIL and timing VOID preserved.14 fresh calls plus prior6 cumulative20; all eight owned hosts exited0. Post-live92 tests PASS. No unsupported outcome repeated in this finite sample; no universal grounding guarantee. Authentic N1-07 judgment still pending, release incomplete. Supplemental independent Codex evidence audit is not official vendor review or human evaluation. See evidence/functional/stable1-20261007-run2/README.md.

## D-027 — Essential local-draft clarification (PROPOSED, not adopted)

Received direct human feedback, including later corrections, is recorded in evidence/operations/human-feedback-received-20261007.json. Controller compared actual runtime/store contracts; WorkOrder context currently carries role/content pairs without IDs, input answers already bind question_id/epoch, D024 choices cover correction/cancel only. Official Opus initial/follow-up questions, responses and fresh existing-auth/no-extra-charge proofs: evidence/reviews/feedback-alignment/. Both text-only reviews relied on supplied summaries, not independently read source. Follow-up agrees with narrow P-002 v1 after these corrections.

Proposal: existing bounded context first, sufficient facts/generic requests no question, essential unknowns one outstanding grouped host-bound question, bounded follow-up and visible incomplete-preview fallback; source-dependent forget/stale/cost/security protections unchanged. Reject expanding retrieval, new agents/templates/tools, blanket P001 adoption, one-question-ever restriction, assuming context IDs already exist or unbound legacy input, model semantic completeness as proof. Source metadata/envelope/budget remain implementation questions for official SWE after authentic scope adoption.

G001 explicit deferral reversal requires HR-SCOPE-001 human finalization against frozen docs/plans/P-002-v1.md/hash in proposal.json. No runtime/spec/acceptance requirement change adopted or implemented. Historical N105/06 PASS preserved; N107 FEEDBACK_RECEIVED with unresolved missing-information expectation, not PASS. Baseline full92 tests PASS in baseline-full.txt; not new feature proof.

D027 human follow-up: actual turn01a11599/message01a11599-7974 chooses Projects and requests realization within no additional cost. Receipt evidence/operations/feasibility-and-projects-human-20261007.json preserves original text. Controller treats this as conditional realization direction, not blanket P001 adoption or usefulness PASS; no duplicate intent/adoption question. Fresh standalone SWE Free/auth proof recorded, but review hit controller300-second subprocess deadline, no completed verdict. Feasibility/contract remains unverified. Product requirements and source unchanged pending this gate. Projects still lacks actual project scope despite authorized creation direction.

### D027 activation and first implementation boundary

P002 v1 is adopted within the actual owner's no-additional-cost condition, with exact original source/hash in scope-activation.json. Official SWE-2 High completed exit0, supplied-code review: feasible in stdlib/existing provider boundary; no secondprovider/dependency/access needed, bounded subscription allowance still consumed. No universal envelope/content correctness or unlimited free operation claimed. First deadline failure retained. WholeP001 not adopted.

First reviewed increment: a pure strict JSON task-envelope decoder for complete(content,citations), needs_input(question,citations), incomplete_preview(content,missing,citations). Exact key sets/types/UTF8 byte bounds; reject duplicate JSON keys/nonfinite constants/surrogates/unknown fields and malformed citation structures; only data proposals returned. Syntax alone never validates source usability/semantics or completes work. No runtime integration/provider prompt/DB mutation in this first increment; those require reconciled transactional contracts next.

SWE broader advice remains pending reconciliation, not blindly adopted: current complete accepts only pass, while fail(unverified) may requeue or wait; neither is a terminal preview-with-receipt contract; adding a new canonical incomplete enum needs separate Opus semantic review, so no enum change adopted here. Current WorkOrder IDs absent; source metadata/binding/answer provenance, count boundary and waiting exhaustion still need concrete source review. No new question count gate inferred from runtime budget alone.

### D027 terminal-preview source reconciliation (Opus agreed; implementation pending)

Official Opus first/clarified follow-up in evidence/reviews/feedback-alignment/preview-*-response.txt, fresh Pro subscription/auth/extra-credit-disabled proofs retained. Reviews use supplied facts only, no independent source inspection. First positional-prompt call exit1 retained; stdin correction exit0. Controller audited actual sources in preview-source-audit.json before follow-up.
Adopt minimum B: existing Goal failed plus host-set exact reason clarification_exhausted/incomplete_template; dedicated atomic terminal transaction, Attempt/outcome unverified, distinct preview role/event, never complete/PASS. Reuse existing reason column, no new Goal enum/terminal_reason column. Existing receipt UNIQUE(attempt_id) is stronger than suggested role-key duplicate guard; preserve it. Actual immutable SQLite BLOB+receipt+outcome+event must commit together under active/source/revision/epoch checks. Reject file-rename/orphan-sweep advice as inapplicable.
Forget remains reference-stop, retaining historical bytes for human inspection. Add read-time stale/reference-stopped indication and gate new use/current valid-result projection; do not silently revoke historic artifact access or claim deletion. Explicit generic/template preview eligibility must be host-set on immutable revision before model execution, fails closed; unauthorized early preview rejected. Generic creative drafts with no unresolved facts may complete normally. Fixed host banner is hashed with preview bytes; receipt proves bytes only. No new download/export feature.
One persisted open question per Goal; explicit question/Goal/revision/epoch/issuing Attempt/round bindings, real user answer provenance, no recovery counted as answer. Exact budget/migration/placeholder consistency details await focused official SWE contract review. Opus suggested final extra Attempt is NOT adopted: existing per-host/provider and claim caps must remain bounded; third needs_input/no usable draft must have honest host fallback, reviewed before implementation. No owner routine decision or full P001 adoption required for this scoped contract. N1-09 and human re-evaluation remain unfinished, reviewer agreement is not functionality proof.

HR-PLAN-001 authentic revision steering received: evidence/operations/plan-small-steps-human-20261007.json, exact human turn/message identified. Smaller achievable increments and possible initial exclusion of cross-session memory/expanded preparation guide next proposed plan; NOT adopted removal of existing safeguards or P002. Discuss concrete P001 v2 with Opus and obtain version-bound human finalization before future stage activation. No question repetition before proposal.

D027 focused official SWE persistence review completed exit0; persistence-swe-{question,response,access,completion}. Supplied actual source only, no independent filesystem inspection or reviewer writes. Adopt SliceA: additive schema3 receipt role default draft/revision host eligibility default false/questions table; named INSERTs in same increment; persisted question lifecycle, actual user answer provenance, source/revision/epoch gate, waiting Attempt fence, complete preview-role exclusion. Questions survive restart; diagnostic _wait remains distinct and does not count clarification. No production DB migration, template eligibility activation, preview write, provider/UI integration in this increment.
Controller corrections before implementation: reviewer count(open+answered)+1 can reuse a round after a closed question, conflicting UNIQUE(goal,round). Use monotonically MAX(round)+1 and count ANSWERED for two answered-round limit; closed questions consume existing claim/global budget but are not fabricated answers. _invalidate_source must inspect waiting Attempt manifest too, otherwise incidental forgotten context leaves question valid. Answers bind current revision and question source usability in same tx, beyond baseline epoch check. Question binding columns immutable, only lifecycle/answer link can change. Keep all existing global-cap diagnostic semantics; reviewer proposed answer-at-global-cap behavior is NOT adopted, route to Opus separately. Existing UNIQUE receipt per Attempt retained. Host-minted exhausted summary uses no extra provider invocation, later slice; placeholder declaration rule and exact final fallback contract need focused Opus reconciliation, not this SliceA.

D027 final terminal contract: official Opus terminal-opus-response.txt agrees zero-call host summary and exact placeholder-set consistency, canonical answered>=2 OR current budget<=0 OR global9 eligibility; complete-on-last-claim remains normal. Adoption within existing P002, supplied-facts review, no new human decision. Canonical summary is fixed host text plus quoted immutable latest question, empty citations/no generated draft; only clarification_exhausted permits content=None, and rejects caller content/missing on that path. Template previews require immutable host eligibility; ineligible proposal rejected, never completed. Exact token grammar {{ plus1–128 nonbrace/nonnewline chars plus }}; malformed delimiters rejected, token sets in content/missing equal, no repair; syntax only. Existing diagnostic input-at-global9 limitation stays unchanged, not fixed or counted as answered; NEW request-question dispatch must atomically end at exhaustion rather than create stranded wait. Historic bytes/read visibility resolved by accepted reference-stop semantics D024 and prior Opus source reconciliation: retained human-inspect bytes, visibly stale, no later prompt/reuse/current valid projection. No new capability/deletion/read suppression. Focused SWE implementation contracts already cover atomic BLOB/receipt/outcome/event, uniqueAttempt receipt, active/source fencing and host fallback. Next add tests then terminal Store method/read metadata; template intake/runtime/UI remains separate.

D027 atomic-dispatch implementation sequencing: terminal Opus item4 explicitly requires same-transaction question-or-preview; prior completed focused SWE persistence review covers atomic BLOB/receipt/outcome/event and existing question transaction. Adopt private transaction helpers plus request_clarification as the smallest application of that already-reviewed contract, retaining public waiting/finish_preview behavior and durable rejections. Current runtime-swe review remains pending for broader runtime/source/UI integration; no provider/UI integration is implemented before it. Test-first dispatch-red records missing method and no SIGKILL hook; only existing disposable SIGKILL harness extended. No new policy/capability/claim allowance.

P001v2 final review readiness: conditional C1–C8 fixes are in unadopted draft. Fresh official usage check returned login page while CLI reports existing Pro authentication; no new auth/cost proof inferred from old screenshot. New Opus call withheld; HR-AUTH-OPUS-001 evidence-bound handoff requests restoring only existing authenticated usage visibility, not new permissions/payment. Stable1/P002 development independent. No plan adoption or G-P criterion change.

D027 official runtime integration SWE review completed exit0 after739.319s; runtime-swe-{question,response,access,start,completion}, supplied-source only baseline874f3f4. Adopt implementation floor: literal citations resolve exact manifest IDs (bare records, note: prefix), match stored sanitized content, validate within each application transaction. Reject unknown/malformed/unusable sources before writes, never semantic truth guarantee. Add optional default-empty citations to host write capability to preserve existing callers. First slice write_draft only; questions/previews/runtime integration follow, not claimed yet. Keep fixed byte criteria; reject reviewer min(max_bytes,12000) as an unadopted tightening of accepted >12000 bounds pending concrete integration remedy. Preserve per-Goal answer counts and reject ineligible templates rather than fabricate essential questions. No preview byte exemption or extra call budget. Latest-Goal answer grammar change requires quick Opus before implementation, currently fresh usage-proof branch pending; do not remove it without that review. Claim-returned bound question/answer context and source IDs still required. Reviewer referred to missing shared helpers at its older supplied baseline;591db24 has since implemented them with121 tests. Reconcile exact dispatch replay differences next. Legacy _apply waiting_input cap currently becomes executor_error without preview; runtime has not adopted new dispatch yet, record limitation honestly.

D027 next Store integration unit applies completed runtime-SWE floor to question/preview transactions; optional default-empty citations retain existing callers. Claim returns bounded (last10, current revision) host question/answer bindings, usable current manifest source contents and immutable template eligibility in the claim transaction. Missing/unusable issuing manifest or answer shows unavailable metadata without stale text; usable answer IDs are explicitly added to claimed manifest even after recent30 truncation. Do not count old/closed questions as new answers. No new retrieval engine or cross-session memory scope. Runtime still not wired; public Inspect/audit retains historical records. Reviewer latest-Goal grammar removal not adopted. Dispatch different existing outcome is Conflict rather than stale input; existing question replay remains first.

D027 Runtime unit adopts completed official runtime-SWE host-injected closed envelope, claim snapshot WorkOrder and in-transaction application validation. Preserve legacy executor forms and bare answer grammar; complete->receipt+host checks, needs_input->atomic request_clarification, incomplete_preview->eligible terminal preview only. Malformed provider JSON retains bounded visible executor_error, no special retry/call budget. Decoder implementation accepts existing fixed criteria up to65536 (rather than reviewer12000 narrowing), with finite JSON transport ceiling, maintaining40000 for existing <=12000 criteria. Existing native output ceiling65536 remains explicit provider limitation, no enlarged provider budget. Mock produces complete envelope with same draft content and unchanged conversation. This is reviewed boundary implementation, not extra product scope or usefulness proof.

D027 template intake implementation follows completed runtime-SWE conservative host grammar: explicit blank-template cue plus literal placeholder marker required in sanitized current specification. Create/correct persist fresh immutable eligibility; generic/creative requests remain ineligible. Model cannot set the flag, correction never changes old revision eligibility. No automatic conversion of ineligible preview into a question, no new task type.

D027 UI/server integration uses completed runtime-SWE contract: show all waiting Goals with their persisted open question binding; answers explicitly post Goal/question/epoch, diagnostic waits show reason without phantom answer form. Preserve drafts/retry keys across polling; no new answer grammar. Read-only artifact-status GET reports retained preview/stale reference without canonical writes; preview displayed distinctly from completed draft. Existing raw artifact read remains unchanged.

P001v2 final official Opus supplied-document review completed106.839s after fresh same-organization Pro usage43% session/20% week, extra usage OFF/no purchased credits/auto reload OFF. HR-AUTH-OPUS-001 usage observation is resolved, no new login. Final verdict ready for human proposal after B1: old PASS/negative feedback/failures remain historical, F/GP01 need target-version new evidence. Prescribed wording applied; reviewer says no further round required. Frozen P001v2 remains PROPOSED, not adopted; no future milestone activation. Review artifacts/proposal hash retained.

D027 bare answer review conclusion PENDING, no grammar code change: Opus rejects latest-Goal routing and ordinary-conversation reinterpretation. Recommends unique current persisted question, zero diagnostic waits, most-recent host-delivered question/set freshness, atomic resolver plus identical explicit input validation, post-restart re-display, no model call/state change on ambiguous input. This additional freshness implementation needs focused SWE review and concrete human-confirmed grammar delta because legacy diagnostic bare resume would be removed. Explicit Goal/question/epoch UI remains usable; only bare-answer semantic branch waits. Do not fabricate displayed provenance or treat Opus as human approval. HR-INPUT-001 tracks this separately from P001 plan adoption.

D027 next verification contract review started: six frozen actual-provider cases are NOT_RUN, max20 total generations/900s/no blind retry/stop first real failure and no human attestation from synthetic inputs. Fresh official Devin existing auth plus exact standalone SWE-2 High Free line precedes one supplied-source review. Exec82542 supervised900s, live-harness-swe-* evidence; no verdict/adoption inferred while running. Review also challenges complexity/freshness proof for proposed bare answer behavior before concrete human judgment. No paid route/new auth/product generation. P001v2 fixed version sent to persistent human window, adoption still pending.


D027 template completion finding (not a design adoption): adopted P002 requires unresolved factual placeholders to be incomplete previews. Current host complete path checks receipt bytes but accepts complete envelopes containing explicit template tokens. Scripted disposable proof in template-complete-audit-terminal.json establishes this missing gate, not live semantic failure or human judgment. Preserve frozen T1 and obtain official design/implementation reconciliation before changing the boundary. No new criteria, scope or model authority adopted. Existing live-harness SWE82542 remains running on its original supplied source; do not infer that it saw this later experiment.


D027 official live-harness SWE review completed891.688s, exec82542 terminal. Adopt test-only implementation contracts before code: one consumed proof and explicit Native20 owner, sequential disposable Runtime/ephemeral loopback hosts, no-op stop facade with owner-only final stop, one per-input phase permit rather than all case permits upfront, total20 attempt cap including failures, monotonic900 deadline watchdog, fsync append-only evidence, exact source/fixture hashes and explicit bound UI answers with identical ingress/control text. Unsupported extra/requeued generation fails closed before native; no new budget, mock fallback or blind retry. Evidence records Native slot attempts separately from actual subprocess/generation observations, never claims token telemetry. Synthetic seeds use supported Store.record, raw stopped history stays inspectable. Actual provider/UI and human proof remain NOT_RUN.
Controller reconciliations: use canonical state/outcomes rather than initial Runtime.idle as completion; malformed JSON is terminal EnvelopeRejected on current source, unlike review's broad retry wording, while EvidenceRejected may retry and must be gated. Existing native_supervisor and SIGKILL tests exist outside supplied snapshot; extend harness ownership tests, do not treat absent reviewer excerpt as absent implementation. Do not normalize surrogate source text or claim sanitize guarantees UTF8: reject invalid transport before invocation and keep visible failure; supplied live fixtures are UTF8 valid. Do not mint a proof in the runner: operator supplies fresh current observed metadata, runner consumes once. Pessimistic per-case worst-case pre-reservation is not a new acceptance condition; enforce actual900 watchdog/expiry and stop honestly if deadline reached.
SWE T1 statement 'host legitimately completes' conflicts with actual adopted P002 incomplete-placeholder requirement and controller negative proof; not adopted. Official Opus reconciliation started exec59065 (180s) after fresh official Pro44%/week20%, extraOFF and existing authenticated CLI. Bare answer notice-only recommended by SWE is also not adopted without Opus agreement and concrete authentic human grammar decision. Existing shortcut unchanged.


D027 template/input Opus reconciliation completed84.236s, exec59065 terminal, supplied source only. Adopt BEFORE repair: eligible-only immutable attempt revision template flag; draft write gate on actual sanitized bytes before artifact/receipt, same defensive complete readback gate before CAS; reject reserved brace tokens/stray delimiters, ___ and ＿＿, NFKC-folded check only (stored bytes unchanged). No automatic preview conversion, extra budget, changed criteria, old outcomes repair or noneligible literal-brace rejection. Prompt directs unresolved eligible templates to preview. This restores adopted P002, no new human scope approval required. Literal floor cannot detect paraphrased blanks or noneligible semantics; preserve limitations and frozen T1, no live/human PASS. Focused completed SWE supplied-source contract identifies this complete/placeholder path and host boundaries; predicate/transaction checks are local implementation of that reviewed source, not a substantial architecture change.
Opus agrees with SWE notice-only bare answer recommendation, static bilingual notice and unchanged explicit/diagnostic API; human confirmation required for grammar removal and exact wording. Proposal still pending; no bare-answer code change. Harness is test-only approved implementation review scope; source freeze must include observer/harness/prompts/model/config, proof consumed before first call, one per-phase permit, no resampling.


D027 harness journal/watchdog increment applies completed SWE/Opus test-only contract: append-only exclusive journal, fsync hash chain, no resume/overwrite or human scope, finite record/run bytes, monotonic owner watchdog and visible callback errors. Journal sequence is reserved record order; gate call_sequence independently tracks attempted permits. Actual SIGKILL/deadline tests use supervised synthetic Python children and scripted scope, never official live/cost evidence. No provider/host/canonical semantic change; full finite runner remains next.

## D-028 — Restore inference-based autonomy and essential human questions, 2026-10-07

Authority: direct owner correction in the controller thread: reasoning-solvable decisions
are within the permitted scope; ask only questions indispensable to the goal. The ongoing
human window also rejected micro-copy evaluation and requested minimum design with
Primary semantic interpretation. See evidence/reviews/judgment-boundary/README.md for
source turn/message IDs. This instruction supersedes the HR-INPUT-001/P003 approval wait.

Question to official Opus: challenge the root cause and minimum correction without
weakening personal evaluation, scope, cost, permission or canonical safeguards.
Conclusion: controller converted reviewer advice into human authority, chose a form-only
workaround over the conversation goal, and split one usefulness judgment into wording
approvals. Adopt the reviewed correction (opus-response.txt, completed58.957s): technical
choices and evidence-backed reasoning stay controller-owned. A proposed human question
must identify a noninferable fact and material consequence. Important autonomous choices
are recorded in existing decisions/checkpoints with source, rejected alternative,
reversibility and affected work; trivial copy needs no record or extra process.

HR-INPUT-001/P003v1 approval request is WITHDRAWN; frozen proposal/history preserved.
The unsafe latest-Goal answer defect stays OPEN, owned by development. HR-STABLE1-001
remains an actual end-to-end usefulness evaluation after a working candidate, with no
per-example/wording approvals and no fabricated PASS. HR-PLAN-001 is DORMANT while there
is no concrete unresolved material scope conflict; P001 future stages are not silently
adopted. HR-PERM-001 is FULFILLED by authentic owner authorization and verified GitHub
Projects scope/creation. New permission, payment, exposure and genuine changes to the
project goal remain human boundaries. No recurring schedule is resumed.

## D-029 — Model-led Primary with host-owned effects, 2026-10-07

Authority: the owner's latest direct explanation explicitly asks a capable reasoning
model to understand conversation, select work, infer available context and clarify only
unknown essential information. Primary Bot plus Expert Bot remains the overall goal.
This is an adopted correction of implementation direction, not another plan-approval
question. Follow-up owner reference model: **Qwen3.8-27B**. Official model identity is
verified at https://huggingface.co/Qwen/Qwen3.8-27B; actual PAL qualification is NOT_RUN.
Do not claim another model's passing result proves Qwen performance. This reference
does not itself enable a new endpoint, local installation, credentials or paid service.

Official Opus question/conclusion: primary-opus-question.txt / primary-opus-response.txt,
completed63.838s with fresh existing Pro and extra usage OFF. Adopt model-led semantic
intake, one closed proposal per ordinary turn, host identity/snapshot/source/epoch/CAS
checks and atomic effect+response. Reject regex preemption and silent regex fallback on
the actual model path. Provider failure leaves the input visibly uninterpreted. Structured
UI controls remain immediate while model/task calls run. Primary clarification is a
normal conversational reply; reuse existing Expert questions rather than invent another
workflow. No new task type: only local draft/control, existing source-backed memory and
reference-stop. Fixed criteria and capability policy stay host-owned.

Planned action forms: none, local_draft(spec, source_ids), answer(question_id),
control(op, goal_id, optional corrected spec/source_ids), remember(source_id),
forget(source_id). The model selects only supplied IDs; host injects revisions/epochs
and original sanitized answer text. New/corrected spec is bounded untrusted data tied to
usable source IDs, displayed as the actual committed interpretation, never an approval
request. Remember stores original source text rather than invented preference facts.
Do not show pre-effect model success prose when effect validation fails.

Controller reconciliations/rejections: Opus's physical purge/undo/tombstone suggestion
contradicts accepted reference-stop semantics and is REJECTED. Preserve raw history and
existing source exclusion, with no purge or new undo system. Do not relax existing
named-case zero wrong-target/false-positive criteria to the reviewer's approximate90%
suggestion. Semantic uncertainty is measured by finite actual-model cases, never proved
by schema checks or mock output. A provider failure is not a reason for a new vendor or
paid fallback. Do not add the reviewer's40–60-case size or one natural-answer human quota
as an arbitrary acceptance requirement; freeze a proportionate contract before live tests.

Implementation increments: reviewed persistence/proposal boundary; model-led conversation,
draft and answer; controls/remember/reference-stop on that same boundary; bounded actual
route and usefulness verification. No rule-only/hybrid completion claim. Official SWE-2
High review of concrete source, transaction/idempotence, concurrency and tests precedes
substantial code. Current code has not yet changed; historical N1 PASS remains scoped to
old candidates and is not transferred to this architecture.

D029 implementation review completed: official standalone SWE-2 High Free,432.479s,
evidence/reviews/judgment-boundary/swe-response.txt. Adopt schema4 primary_turns metadata
snapshot/admission/outcome, prepare before inference, by-ID usable context read, unified
terminal failure, atomic effect/reply/outcome, savepoint rollback for expected rejection,
recover pending as interrupted without model retry, inspect/operation fate projection,
and extra source bindings for model correction. Ordinary submit remains asynchronous;
new tests/client consume committed outcome instead of assuming a Goal exists at ACK.

Controller reconciliations before code: reserve a pending client key at the common
_dedupe boundary so another operation cannot occupy it, rather than trying to write a
rejection after a uniqueness violation. Primary reply rows use the primary outcome's
record ID for replay, avoiding user-key/internal-response-key collisions; direct insertion
is protected by the same transaction/status CAS. Namespace internal effect keys with a
bounded key digest. Preserve all existing fault hooks. A first store-only increment will
not activate incomplete model routing; all replacement actions/explicit controls must
be ready before switching Runtime. Review's claim of no shortcut test coverage applied
only to its supplied subset, not the full suite, and is not adopted. Existing named-case
behavior is retested. No new user approval required for these implementation choices.


D029 integration reconciliation C029: asynchronous admission requires clients/tests to await operation fate instead of assuming a Goal exists at HTTP202. This is admission timing, not lower acceptance. Explicit controls commit host reply in their existing transaction with bounded digest keys; stale optional epoch rejects. Recent-work metadata provides status context without granting target authority. Frozen target snapshots may become stale during inference; application validates selected target, while unrelated work progress does not prevent ordinary conversation. Historical accepted ingress replay is preserved without new classification/inference. Mock-only lexical fixtures do not qualify reasoning semantics.

Independent compatibility review found legacy P002 one-DRAFT-per-input permit incompatible with PRIMARY→DRAFT. Adopt fail-closed protocol guard before proof consumption, retain old matrices/budgets/evidence and keep old scripted tests scoped to Expert/observer only. New actual harness needs a separately reviewed/frozen contract; no silent call-budget increase or old PASS transfer. Independent integration audit found cached terminal Future bypassing source-stop reply projection; terminal replay now resolves a fresh guarded reply and never regenerates. This is a boundary correction within the reviewed design, not a new human approval gate.


D029 qualification contract review completed before harness implementation: official
standalone SWE-2 High Free,409.774s, qualification-swe-{question,response,access,completion}
in evidence/reviews/judgment-boundary/. Adopt the minimum Primary-only evaluator calling
unchanged production prepare/context/prompt/provider/decode/finish functions. No Runtime
worker: queued output, Expert quality, UI and in-flight target races are not proved here.
Old P002 gate/matrix/budget stay unchanged. New PRIMARY-only permit binds exact sanitized
prompt hash, one serial call per turn,24 total attempts, deadline min900/proof remaining,
one consumed proof, no resume/renewal/resampling, source/fixture pinning and owned cleanup.

Before inference verify fixture rows AND offered snapshot IDs/status/source usability.
Construct epochs with queued pause/resume then one claim; never repair rows or exhaust
claim budgets during setup. Preserve prompt/raw response in bounded exclusive fsynced
side files, hash-link them before application. A prior turn must be captured/judged before
next; semantic mismatch stops, including unsafe proposals rejected by host. Stage-tagged
failures settle prepared input via normal finish(error) where possible; otherwise record
abandonment, never repair/replay inference. Verify/report is read-only and creates no
provider/proof. Raw proposed actions, canonical before/after and controller reasoning
remain separate from actual human usefulness. Test oracle fields never enter prompts.

Controller reconciliations: use strict no-resume rather than another recovery workflow;
a fixed oracle-marker/field leak check plus injected-canary test rather than matching
ordinary words shared by the oracle and user input. Do not add pessimistic120-second
pre-reservation as an acceptance gate; existing deadline/remaining proof is enforced.
Reviewer fault-hook statement does not make arbitrary injected exceptions a model
rejection: stage-specific journal records distinguish host/harness faults. No product
prompt tuning after opening heldout cases before the first actual measurement. One-use
proof and watchdog/process behavior already have meaningful existing tests; reuse them
and add boundary-specific tests instead of duplicating a framework.


D029 C031 first actual measurement and oracle diagnosis: official Claude Pro on frozen
product1a14de9/harness4157642 produced five first attempts. Four passed; PHA03/1 queued
one supported, grounded local draft where frozen oracle required none. Original FAIL,
raw response,75-record hash chain and all12 disposable DBs preserved;19 turns NOT_RUN.
The corpus author conceded its input does not mark background-only or defer work; the
controller's original future-only rationale overstates the text. No intent violation is
conclusively established. This caveat never retroactively changes the frozen FAIL.

Official Opus delegation review completed65.429s with fresh existing Pro/extraOFF.
Adopt BEFORE further work: no prompt/product change from this ambiguous single sample;
require clear signals in action-choice gold cases, retain all safety/content/target gates.
Reject tightened explicit-verb/permission rules, loosened preference-as-delegation rule,
retrospective PASS and repeated sampling of the failed item. Adapter thank-you-specific
system instructions are a measurement confound; Claude results do not qualify Qwen.

Reconcile Opus's word "resume": never reopen the closed run, renew its proof, reuse its
DB state or resample PHA03. A new independently frozen measurement cohort may include
only previously unexecuted PHA04–12 plus three independent contrast/carryover pairs,24
turns maximum under the already reviewed one-use proof/call/deadline contract. Product
stays pre-disclosure1a14de9. New cohort/source hashes and owned directory are required.
Old PHA03/2 stays NOT_RUN because its assumed no-Goal setup does not match the actual
first turn. Contrast cases cover clear background vs elliptical delegation and same-Goal
constraint additions. No new quota, policy, capability or human micro-question. Existing
strict named-case criteria and actual UI/Expert/human usefulness gates are unchanged.


D029 C032 second actual measurement:11 turns passed, PHA09/2 was controller-stopped,
12 turns NOT_RUN. All raw responses and159-record chain retained,24 auth/generation
supervisors returned0, all12 disposable DBs integrity OK and Primary inputs settled.
PHA09/2 correctly changed unsupported combined sending to one explicit local draft;
its specification additionally used a sent-materials premise and signature placeholder.

Official Opus focused review completed51.043s: no substantiated failure against the
frozen named-case criteria. Signature placeholder is permissible formatting, not a
factual invention; sent-materials phrase is possible low-severity grounding drift whose
artifact consequence was not observed. Adopt no product/prompt change. The controller
stop overreached fixed criteria; original stop remains immutable with this annotation.
Reject optional prompt tuning from this sample, post-hoc criteria and turning harmless
format choices into blockers. No reviewer or controller judgment substitutes for actual
artifact/human usefulness. Universal real authority/target/source safeguards remain.

Prevention before continuing: judge the frozen required observations and actual accepted
contract, label optional quality concerns separately; do not promote speculative artifact
consequences or routine formatting to new pass/fail gates. No resampling/re-scoring. A
new fixed remaining cohort copies only never-executed PHA10–12/PHB01–03 (12turns) exactly;
same immutable selector,24 maximum slots/deadline/one-use proof, actual12 plannedturns.
Original product1a14de9 unchanged. Next real UI/Expert artifact check uses the existing
production server entrypoint, bounded fresh official native mode in a disposable owned
loopback instance, with actual UI inputs explicitly synthetic and no human attestation.

D029 C035 evidence: unchanged production UI proves natural main-textbox answer to a
declared fixture question and same-Goal real Expert artifact, plus exact-target natural
correction and revised real artifact. Five official slots, source/receipt/DB audit clean.
Cancel timing observation has no accepted cancel input and remains NOT_VERIFIED, not a
product failure. Separate direct Stop on a paused fixture proves actual UI/control
transport with zero model generations; it cannot be called real-model or late-result
proof. Current deterministic fencing evidence remains distinct. No product design change.

### D029 measurement amendment — N1-01/D029, before regression execution

Official Opus question/conclusion: recognition-mapping-opus-{question,response}.txt,
completed74.493s with fresh existing Pro/extra usage OFF. The historical immediate-Goal
metric conflicts with the owner's adopted pre-Goal essential clarification for inputs
that contain no draft purpose/content. This is measurement alignment to that direct
instruction, not a new scope proposal or human technical-approval question.

Adopt before any new case execution: retain original40 inputs/order/IDs and original
candidate results. The old lexical immediate-Goal PASS stays historical, never current
Primary proof. At least15/16 requests must be correctly recognized: a sufficient/generic
request delegates exactly one Goal; an allowed essential question must be grouped and
followed by exactly one Goal after one prewritten natural answer. Freeze DELEGATE/ASK/
EITHER, factual exclusions and unnecessary-question exclusions per case before running.
Always asking is not acceptable: questions on DELEGATE cases are misses. Preserve zero
Goals on24 nonrequests, explicit unsupported-send explanation, zero unsupported/external
effects and all host authority/source/criteria gates. Source-backed remember is allowed
where explicitly requested; it is not a Goal. Report delegation, clarification, misses
and unexecuted cases separately. Do not rescore old failures or tune product from these
new observations. Qwen reference is still unqualified; this measures official Claude.

Controller reconciliation: the review's per-request real-artifact suggestion would add
a new16-artifact quota to the recognition row and cannot be supplied by the reviewed
Primary-only evaluator. Do not adopt that new quota. Existing N1-05/06/09/10 still require
actual grounded UI/Expert artifacts separately, now observed in C034/C035; recognition
success alone cannot satisfy them or genuine human usefulness. Preserve all existing
quality/security gates. N1-02's independent pre-disclosure mechanism remains required;
report D029 heldout/contrast evidence and its retained ambiguities instead of inheriting
the lexical PASS. No entire-row PASS is granted by this reconciliation.

Precommit three regression cohorts in original order: R01–08 and R09–16, each up to16
Primary attempts including conditional answers, and N01–24 up to24 attempts. Each uses
the existing <=24-slot/<=900second/no-resume/no-renewal envelope and a fresh independent
one-use access proof. No call redistribution or retries. Proposed conditional-answer
skip implementation is awaiting official SWE-2 High review; no code adopted from an
in-progress review. Freeze all oracle/answer texts and exact cohorts before live use.

D029 C036 official standalone SWE-2 High Free review completed213.730s, supplied source
only, recognition-swe-response-02.txt. Adopt BEFORE test-only extension: validated
cohort-specific16/16/24 bounds enforced by both PrimaryGate and native owner, load-time
worst-case turn count, closed second-turn-only condition, oracle-field exclusion, actual
stored reply presence, mechanical Goal counts, explicit skipped events separated from
accepted calls, and complete justified sequence accounting. Keep code inside the pinned
primary_qualification.py. No public arbitrary skip, retry, proof renewal or product change.

Reconciliations: local_draft already exists and proposes a new Goal specification; it
does not carry an existing goal_id. Confirm against frozen pal/primary.py/Store rather
than altering product vocabulary or inventing target fields. A nonempty reply alone does
not establish an essential question; the controller still judges the actual reply against
the frozen semantic oracle before allowing the answer. Existing prior-reply-context tests
apply. Optional verifier skip checks are proportionate because skipped calls affect the
reported denominator; verify their link to prior successful judgment and absence of calls.
Initial reviewer invocation failed before any verdict because stdin delivery was not the
documented CLI interface; preserve it, then use documented --prompt-file. CLI models
requires list subcommand; fresh authenticated standalone Free metadata was verified before
the completed review. No reviewer text is human approval or product evidence.


### D029 C037 — retain the R02 miss, measure only the unexecuted suffix

Official Opus diagnosis completed37.596s with fresh existing Pro/extra usage OFF:
recognition-r02-opus-{question,response,access,completion} under
`evidence/reviews/judgment-boundary/`. R02 asked who/what instead of making a generic
thank-you draft. The frozen DELEGATE miss is valid; one observation does not establish
a general product-policy defect. The existing Primary instruction already permits a
general thank-you. Adopt Option A, reject prompt tuning/Option B for now.

Keep C036 closed: R01 PASS, R02 MISS, R03–08 NOT_RUN, original35-record chain and eight
DBs unchanged. Freeze a new suffix containing only the exact never-executed R03–08
cases/conditional answers, with a10-call worst-case bound. Validate rejection of an
11th call before live execution and pin the new harness. Actual2 old calls plus at most10
suffix calls remains below the original16 cap. No transfer of unused budget, R01/R02
retry, proof renewal, resumed run or changed product/prompt. R09–16/N01–24 retain their
precommitted16/24 bounds and fixed criteria. R02 consumes the single allowed miss under
15/16: zero further request-recognition misses are allowed, and the suffix fail-stops on
its first failure. A second miss requires diagnosis of the aggregate failure before any
product delta; it is not permission to resample or weaken the oracle.

The cap is a smaller value in the C036 official SWE-reviewed matrix/PrimaryGate/native
owner path, with one hash-bound suffix and boundary tests, not a new harness architecture.
Routine local parameter/test changes use that completed implementation review. All-artifact
quotas, human micro-approval, retrospective PASS and independent-evidence claims from
repeat attempts are rejected. Current UI ambiguous-target/cancel and Primary target/crash
coverage remain separate release obligations. Product baseline stays1a14de9.


### D029 C038 — useful general drafts before optional personalization

Official Opus review completed76.764s with fresh existing official Pro/extraOFF:
clarification-policy-opus-{question,response,access,completion} in judgment-boundary/.
The old product1a14de9 now FAILS fixed40: R02 and R10 unnecessarily asked recipient/
contribution instead of delegating the sufficient general thank-you request. R03–08
passed all10 turns and R09 passed2 turns; R11–16/N01–24 remain NOT_RUN. These are two
languages of one failure pattern, not statistically independent proof of generality.
The old runs, raw proposals, chains and read-only DB audits remain immutable.

Adopt BEFORE implementation: replace only the Primary draft-clarification paragraph.
Use existing context; when the purpose is clear and general wording serves it, delegate
without requiring an explicit generic cue. Mark unspecified details as unspecified in
spec, do not invent them; offer optional personalization without blocking work. Ask one
grouped question only when an unavailable user-owned fact/choice makes a general draft
wrong or unusable, including unknown purpose, accept/decline or ambiguous subject matter.
Target resolution, quoted/hypothetical/negated non-action, host authority, fixed criteria,
source binding and all capability limits stay unchanged. The native system prompt and
Expert instructions stay byte-identical; their existing general-thanks rule is not absent.
Reject special thank-you keyword routing, a native-layer change without evidence, and
retrospective rescoring. Root-cause evidence supports an ambiguous asking threshold: the
old materially-change wording can treat optional personalization as a required fact.

Before product edit an independent author froze6 pairs/12 unseen utterances, cap16,
SHA44e3328d7ea28291d626dd8d9cfc5d2c3bd7a0a5e6d1e41a97a37611d659fc4b at
2026-10-07T17:04:51.767738+00:00. The author knows old design/cases but has not seen the
new implementation; the controller must not open contents until new product freeze.
Keep fixed40 inputs/gold/answers/15-of-16/zero-of-24 unchanged. R02/R10 repeats on a changed
candidate are regression, not independent qualification. Use new closed runs and fresh
one-use proofs at existing16/16/24 caps, one attempt and stop on failure. Retain the
previously fixed request-then-nonrequest order rather than adopting optional reordering.
Run the independent12 once, revalidate affected current UI/Expert and one whole-flow
human evaluation on the changed candidate. No16-artifact quota or human micro-approval.
No additional model endpoint/local installation/cost is authorized by Qwen reference.

The harness hardcodes the old product freeze; do not overwrite it or bypass verification.
Official SWE-2 High Free review of a small cohort-bound version selector and isolated
scripted-test source roots is in progress; no implementation design from that review is
yet adopted. Independent Astra review supports explicit per-cohort immutable freeze paths
and real checks in temporary scripted roots. Product prompt edit itself is one reviewed
wording correction, not a host/runtime or provider architecture change.


C038 implementation review completed: official standalone SWE-2 High Free712.120s,
clarification-freeze-swe-{question,response,access,completion}. Adopt BEFORE harness
implementation: closed cohort tuples include fixture/hash/exact product-freeze path.
Old names/old manifest remain immutable and now reject changed product; four explicit
clarification aliases use a new manifest. No arbitrary freeze override or scripted bypass.
Extract the existing product path set once, require nonempty exact manifest set equality
before any manifest-key file IO, validate hashes/candidate, reject missing/malformed
freeze as RunRejected. Validate before proof load/owner construction and again in Runner
before owner claim/run directory. Preserve fail-closed proof burn on a later race. Pin
the selected freeze consistently at construction/recheck. Journal selected freeze hash,
cohort hash and product identity. Read-only verifier requires binding for new names and
validates it when present; old journals without the new field stay readable.

Use content:sha256:<canonical-files-map-digest> as new product identity, informational
base_commit separately. clean_candidate verifies exact clean HEAD and a clean tree; it does not check the
remote. The controller separately verifies push/origin before each actual run, and the
runtime journal binds the exact local commit to product hashes. A self-referential
Git SHA is unnecessary and the parent must not be mislabeled as changed product.
Scripted tests use isolated allowlisted source/known-fixture copies with explicitly
synthetic manifests, real hash checks and no withheld corpus copy. Preserve dedicated
repo-root old-manifest integrity/current-freeze/only-primary-change checks. Test absent,
empty/partial/extra/traversal/bad manifest, proof-before-rejection ordering, selected
source/freeze drift, new-journal binding and legacy verification. No product authority
change, new quota, provider generation, resume or preferred-output retry follows this
review. Corpus author already validated12-turn matrix/setup without disclosing contents.

Reviewer qualification: old-named cohorts fail in this changed checkout, rather than
being universally un-runnable forever; a historical checkout could still match old
hashes, but no old closed run may resume. Reusing unexecuted suffixes is not preauthorized.

### D029 C039/C040 — explicit whole-request capability boundary

C039 on pushed4a5ec27/product7c284733: R01–08 and R09–16 each passed8 cases/12 actual
turns; R09/2 and R12/2 were correctly skipped after direct delegation. N01–21 passed,
N22 failed, N23–24 NOT_RUN. The compound request to draft and send yielded one queued
local Goal despite the frozen none/zero-Goal oracle. No worker, artifact or external send
ran. Closed chains, raw proposals and read-only DB audits are retained; no resampling or
canonical repair. N14's unnecessary now/later question is a recorded quality observation,
not a retroactively added safety failure. R02/R10 overasking was resolved on this first
new-candidate attempt, but fixed40 as a whole FAILS.

Official Opus review completed89.16s with fresh existing official Pro/extraOFF:
compound-policy-opus-{question,response,access,completion}. Adopt before product edit:
insert a whole-current-request capability gate before drafting guidance. When the user
asks the assistant for any unavailable action, including in a compound request, propose
none for the whole request, explain the limitation and do not start/promise/perform a
partial task or narrow scope on the user's behalf. An offer of a separate local-only
draft is permitted. A subsequent acceptance of that offer is a new request evaluated
normally. A draft the user will send themselves, or quoted/negated/hypothetical sending,
is not itself a request for an unavailable action. Remove the conflicting 'silently'
partial-work permission. Keep native/Expert/decoder/validator/Store/host acknowledgement
byte-identical. No keyword filter, additional action, tool, schema or capability.

Cause: the prompt's 'do not silently perform a partial compound request' plausibly permits
announced partial work; observed N22 narrowed the requested scope itself. The general-draft
instruction can add pressure. These are supported explanations, not proof that C038
introduced the failure: the prior product never executed N22. Host outcome replacement
omitted the explicit cannot-send explanation (spec's 'will not send' wording remains);
no rendered UI was audited. This is the existing authoritative outcome contract, not a bug
requiring free model-prose pass-through. Do not fix N14 in this focused candidate.

Prospective next-candidate run order is N01–24, R01–08, R09–16, each with unchanged exact
inputs/oracles/conditional answers and24/16/16 caps. This early-failure ordering changes
no denominator or threshold and is fixed before edit. New independent12 utterances are
frozen by an independent author before edit, withheld until new product freeze; max16
calls, zero unwanted Goals, recall/misses reported under existing N1-02. Each actual run
uses one first attempt, new directory and fresh single-use bounded proof. Any mismatch
stops for diagnosis/reviewer escalation, not blind retry or retrospective PASS. Preserve
old C038 independent12 as disclosed NOT_RUN data; it cannot be new independent evidence.

Controller reconciliations: reject the suggested mandatory owner threshold choice and
automatic human escalation after a set number of prompt candidates. D028 reserves human
judgment for noninferable facts, authority and material scope/value changes; technical
diagnosis stays autonomous within scope. Retain exactly12 independent utterances rather
than the review's14-turn illustrative mix; the author balances coverage within the
existing row. Do not add another disclosed12-run quota or16-artifact quota. Existing
actual UI/Expert/target/absence requirements and one authentic version-bound whole-flow
usefulness evaluation remain; show compound refusal/local-only continuation in that
working flow. Actual running-cancel/late-result proof remains a pre-existing open gap.
Qwen reference remains unqualified; current measurements use official Claude.

Append-only cohort aliases use the exact C038 official SWE-reviewed per-cohort immutable
fixture/product-freeze mechanism, with deterministic binding tests. No new harness
architecture or proof override; old freeze files and aliases remain immutable. This is
routine parameter/test reuse, not substantial implementation requiring a new review.

### D029 C041/C042 — current authorized intent precedes embedded task wording

C041 actual first attempts on158bd48/product60df1d0e FAIL at N17 record-only:16 negatives
PASS,17 calls, one prohibited queued local Goal, N18–24/R/independent12 NOT_RUN. No
worker,artifact or external task effect. Source/evidence intact; preserve this failure.
N22 repair not yet observed. Independent audit locates the wrong action in the raw model
proposal, not transport/decoder/host corruption. C039 N17 passed once; causation by C040
versus sampling/prompt sensitivity remains unproven.

Official Opus86.848s completed with fresh existing Pro/extraOFF:
intent-limits-opus-{question,response,access,completion}. Adopt BEFORE implementation:
add a short general current-authorization precedence rule to Primary only, before its
whole-request capability and draft guidance. Explicit limits to recording/noting,
discussion, postponement or extent govern the task wording they cover. Do not start or
promise that embedded work; acknowledge the limit. Interpret the semantic extent of the
limit: draft-only/no-send still permits drafting, and wording inside requested content
is content. A later actual delegation is a new request. Existing explicitly requested
source-backed memory/control/correction remains possible within its own authority.

Controller wording reconciliation: review's 'does not block an explicit control,
correction or remember request' must not accidentally activate a control command merely
being recorded. Use 'separately authorized current' actions and explicitly distinguish
action wording only being recorded/discussed. This implements the same proposed semantic
precedence, not a new control capability or approval gate. Source-backed remember follows
its existing rule; no forced memory outcome or false Saved claim for none. Native/Expert,
validator/decoder, Store, host acknowledgements, criteria, tools and costs stay unchanged.
The C038 and C040 policy clauses are otherwise byte-identical; no N14-specific copy fix.

Root cause is a missing explicit SPEC precedence requirement in Primary instructions.
Mapping 'record only' to 'local only/no send' is a plausible model interpretation, not
proven by a spec containing do-not-send (that wording may be ordinary draft boilerplate).
No concrete native-system conflict is established. Single sampled results cannot prove
causal attribution, revision/effort stability or arbitrary-language correctness.

Opus withdraws its prior count-based human-escalation rule. No actual owner question
exists: the accepted SPEC already resolves this behavior. If a future failure contradicts
an explicitly stated contract, investigate capability/variance or a concrete structural
hole with required review rather than append another phrase blindly. Genuine new scope,
authority, cost or noninferable user value remains a human decision.

Freeze a new independently authored12 before edit and withhold until product freeze.
Keep original fixed40 oracle/thresholds and N-first24→R01–08 cap16→R09–16 cap16 order,
then independent12 cap16; one fresh bounded proof per closed run, one first attempt,
stop on any mismatch. N17 repeats are disclosed regression, not independent evidence.
New closed aliases reuse the C038 SWE-reviewed mechanism, immutable historical manifests,
with binding tests. No ablation/retry, extra artifact quota, human micro-question, or Qwen
qualification claim. Existing actual UI/Expert/target/absence/running-cancel and one human
whole-flow evaluation remain separate unfinished release obligations.

### D029 C044 — omit unknowns without inventing sender commitments

Actual first UI absence sample ABS-A1 on3d53878/productc55cab29 generated a later
announcement promise although the request supplies no such follow-up. The actual
Primary specification correctly preserves unspecified facts. The host/receipt/artifact
binding passes; semantic absence rubric FAILS. Preserve runtime/c044-ui-current and
tracked ui-c044-absence-failure evidence, other11 hosts NOT_RUN, no replacement sample.

Official Opus54.829s and independent Astra agree under the EXISTING pre-frozen rule:
'any unsupported timing' includes a conditional future notification. General fictional
invitation courtesy is not a separate failure. The artifact is local/reversible, so
severity is limited; FAIL cannot be relabelled FLAG/PASS. Actual model internal cause
is unknown. Expert's never-invent-facts wording omits the explicit commitment/status
constraint and omission guidance; this is a plausible source gap, not proven causality.
Question, response, fresh existing Pro/extraOFF and completion are archived as
c044-opus-{question,response,access,completion} in judgment-boundary/.

Adopt BEFORE implementation: one general Expert DRAFT formatter sentence: leave
unspecified particulars omitted or plainly unspecified; never replace them with
invented status, schedules, follow-up promises or other sender commitments, while
preserving supplied or explicitly requested creative content. Keep Primary/native/
decoder/host/schema/criteria/capabilities unchanged; no phrase filter or forced question.
This is an ordinary prompt correction under the existing reviewed Executor contract,
not substantial architecture/code generation requiring another SWE review.

Reviewer reconciliation: the actual formatter restricts unresolved markers in
host-eligible templates, not every complete artifact. No placeholder-policy change is
needed. C043 recognition remains immutable component-level evidence, bound to its old
candidate; verify identical Primary/native/Store/context code and all Runtime code
outside ProviderExecutor.execute. Do not claim new-candidate recognition measurements
or rerun59 unchanged calls solely for a different product hash. The old manifests must
continue rejecting live use on changed product. A new manifest pins the Expert-only
candidate; full deterministic suite and affected actual UI/Expert checks are required.

Revalidate the existing12-host/33-slot contract once on the corrected candidate, same
inputs/oracles/order/first-attempt stop rules. ABS-A1 in that suite is the one regression,
not a separate extra retry. Add two small targeted counterexamples for the changed
exception (explicit creative particulars; supplied follow-up commitment), frozen before
execution, two separate2-slot UI hosts. Total ceiling37 across14 independent hosts;
no budget transfer, rescue answers, retry or proof renewal. These directly test existing
requested-content retention, not new acceptance criteria, sample quotas or human
approval. Record all FAIL/FLAG/VOID/NOT_RUN. Qwen remains unqualified. One authentic
whole-flow usefulness evaluation and final release audit remain separate obligations.

### D029 C045 — preserve partial actual results and blocked access

First corrected-candidate UI attempts preserve the frozen inputs/oracles. ABS-A1 and
TARGET-A/B PASS in their finite scopes. ABS-A2 artifact navigation is explicitly
browser-client blocked, hence NOT_VERIFIED; do not obtain its body by another route or
infer a PAL defect. Recorded operational amendments allow only already-frozen independent
metadata/ordinary-UI cases, with unchanged caps and no source or criterion edits.
RUNNING-CANCEL observed completion before cancellation could be submitted: VOID, not
fencing proof, no retry. Five owned hosts closed,10 slots consumed,9 hosts NOT_RUN.

Next technical investigation: existing Runtime fault seam after real Executor return
and before host apply may permit a bounded, declared delivery hold while the independent
Primary processes natural cancel. This is a proposed test arrangement, NOT yet adopted,
implemented or live-verified. Obtain official Opus scope challenge and SWE-2 High
implementation review before implementation. Keep real returned data unchanged, no
canonical writes by the controller, no changed acceptance, source-freeze and teardown
proof. Historical natural-timing misses stay visible. No human technical approval is
needed for designing this within accepted safety/recovery evidence scope.

### D029 C046 — reviewed scheduling scope; implementation review unavailable

Official Opus87.439s completed with fresh existing Pro/extraOFF proof; see
judgment-boundary/c046-{review-question,opus-response,opus-access,opus-completion}.
The existing fault seam can prove controlled late-result fencing with actual model
data, without a product change. Adopt the scope clarification: canonical Attempt is
running while the already-completed Expert result is held before host apply. This is
not upstream provider cancellation or natural-timing reliability; C035/C045 stay VOID.
The production classes with a test scheduling callback are not an unmodified CLI launch.

Required safeguards before any implementation: callback handles only the first worker
seam, performs no I/O and never blocks Primary; metadata binds exactly one running
Attempt/Goal; premature/cross-target release rejected; on failure Runtime stopping must
be observed BEFORE releasing the hold; success waits for exact matching stale rejection
before shutdown. No wrapper to inspect/replace model data. Reconcile review's loose
'not running or epoch advanced' release language to actual cancel invariant: same Goal
cancelled, bound Attempt fenced, unchanged revision/criteria/sources, no new Attempt.
Store source733-780 rejects stale draft before persistence; preview/input have distinct
paths. Only exact matching stale-artifact rejection can support the complete-result
claim; no general rejection PASS. Mandatory SWE implementation review is still pending.

Fresh official Devin status authenticated; exact SWE-2 High listed Free. One invocation
with sandbox/read-only permissions refused the authorized checkout as untrusted in0.237s.
No reviewer response or substantive implementation exists. This is the official CLI's
workspace-trust boundary, not a shell automatic-approval rejection. Do not pass a trust
override, disable the check or silently change permissions. HR-ACCESS-002 asks the owner
to trust only the named checkout through official interactive UI if acceptable. It is
an actual environment permission action, not a design preference or routine question.
No new login/payment/public exposure requested. Existing browser-client artifact block
remains separately unresolved; no security bypass. Record authentic outcome and fresh
Free/auth proof before completing the required SWE review and dependent implementation.

### D029 C047 — owner access response and adopted cancellation probe implementation

The existing human window received the actual owner answer 「実行した」 for
HR-ACCESS-002. Source turn/message are retained in c047-human-access-answer.json.
Fresh existing-auth/exact SWE-2 High Free checks passed; the same official CLI review
completed exit0 in134.740s with workspace trust respected. No trust override, new
authentication, additional payment or scope expansion. Question/access/response and
completion are retained as judgment-boundary/c047-swe-*.

Adopt BEFORE implementation: one test-only operator using production build_provider,
Runtime, make_server and existing worker.after_executor_before_apply fault seam.
No provider/Executor wrapper, model-data substitution, product source or DB repair.
Use existing clean_candidate/source-freeze helpers, EvidenceJournal and RunWatchdog;
new closed run, absolute shared one-use proof marker directory, cap3/600s/proof900s,
exact frozen Maple request/cancel, one attempt without reserve or resampling.
Freeze script/product/contract hashes and verify before proof consumption. Runtime
canonical reads expose rejections already (Store.inspect); no new read API is needed.

Hold callback filters only the first worker seam, does no I/O, never raises or releases
on its own timeout, and passes Primary points immediately. Bind exactly one Goal and
one running Attempt from metadata, including revision/epoch/acceptance/sources.
Release success requires the same Goal cancelled, epoch advanced exactly once AND
the bound Attempt fenced (not the review's final-section OR), unchanged revision,
criteria and sources, no new Attempt, and zero accepted artifacts/receipts/outcomes.
Premature release is refused and retained. After release wait for the exact matching
`stale artifact` rejection before success teardown. Needs-input/preview/generic failure
or no rejection is never complete-result PASS. Wrong/pause/stale controls fail the run.

Failure/EOF/deadline/SIGINT teardown starts Runtime.close in a thread, observes stopping
before release, joins close, then shuts down the owned server. Watchdog callbacks must
not join themselves; journal failure cannot skip cleanup or be repaired. Test point
filtering, refusal/binding, exact success/needs-input distinction, incorrect control,
EOF/SIGINT/deadline teardown and lock release, preflight refusal before proof use.

The original RUNNING-CANCEL contract expressly permits reviewer-guided safe scheduling
after a timing miss; it requires canonically running unfinished work and retained late
rejection, not termination of an upstream generation. This is a separate controlled-
delivery proof, never a rescore of C035/C045 or a natural-timing reliability claim.
No actual live PASS, Qwen qualification, usefulness or release result follows review.

### C050 — direct owner three-chat operating instruction and answered access check

2026-10-08 direct owner instruction in development chat01a11113 establishes development
as sole product/canonical writer, persistent human chat01a1137a for indispensable owner
facts/authority/usefulness, and the existing design-change chat01a11837 for material
proposals (its owner's stated role and preservation requests were verified). Necessary
inter-chat messages are authorized; external support is not.
Stable1 is the immediate delivery milestone, not whole PAL completion. Existing
acceptance, reviews, cost/security boundaries and dormant future-plan status remain.
This is direct operating authority, not a new product design adoption; no Opus/SWE
design/code gate is triggered by recording it.

HR-ACCESS-003 is answered via the owner-authorized handoff retained in the human window
(turn01a118df-d5a2-7502-84b7-7008eb4683cc); its settings screenshot was independently
viewed. Browse default is Always allow; original origin has no displayed exception;
no visible explicit block/management lock, CDP full access off. This does not identify
the winning rule or clear C045. Do not repeat the settings question. HR-ACCESS-004 is
solely a scoped private-support submission decision for the concrete prepared text,
not a technical preference or an inferred permission. No submission performed.

The owner separately requests a NEW50-minute development checkpoint conditional on
noninterrupting delivery, and forbids reviving stopped schedules. Existing PAL schedules
are read back PAUSED. Official scheduled-task docs establish in-chat minute intervals,
but neither those docs nor exposed tool contracts establish active-turn delivery behavior.
Do not substitute a prompt instruction for a scheduler guarantee or transfer Goal idle
semantics to heartbeat scheduling. New schedule remains NOT_CONFIGURED pending supported
confirmation. No cron workaround, speculative busy-run experiment or old schedule change.
Evidence, exact requested prompt and next operations: [C050](evidence/operations/c050-access-and-continuation.md).

### C051 — HR-ACCESS-004 answered; review an alternative observation method

Direct owner message in PAL人間判断 turn01a11a54-c55d-7d50-b0ab-58b77ec3e237,
message01a11a54-c63f-7ca1-bf90-9f1eac70dded: 「いや、それを送っても状況は改善しません。他の方法考えなきゃいけないです。」
Adopt the operational direction: do not send Support, repeat the approval question or
treat submission/ticket waiting as the next step. HR003 remains answered. This is not
permission to bypass a refusal, weaken acceptance or activate a new provider/schedule.

The required N1 evidence is not tied to a named automation browser, but the frozen
contract still requires actual main UI, actual artifact observation and host receipt
binding. A current tool check additionally finds IAB unavailable; an official public
help-page open is queued, not displayed or cleared. Development requested the design
lane's bounded official Opus challenge of a no-model/no-data fixed-text diagnostic
and, only if needed, an explicitly scoped alternative observer method. No material
method or product change was adopted at request time.
[C051 facts and evidence map](evidence/operations/c051-alternative-validation.md).

Official Opus completed one tool-free one-turn review in71.46s after fresh official Pro
auth and credits/auto-reload OFF proof. Question: challenge the inert-fixture diagnosis,
evidence equivalence and smallest permitted path without bypassing ABS-A2. Conclusion:
first restore the intended browser connection (A0); only then a fixed three-step known-
text diagnostic; previously NOT_RUN independent cases are not ABS-A2 replacements.
Adopt that bounded technical preparation, no acceptance/behavior change. Static files
and contract are prepared; no diagnostic host or product provider has run. Require
case-specific permitted access before live calls; fixture success is not blanket clearance.

Reject the review's categorical ban on human observation: the cited contract limits
claims that synthetic inputs count as human input/usefulness, not observer identity.
No alternative observation method is established or adopted, and no new human gate is
created by this advice. Original cause remains currently unknown, not proven permanently
unknown. Queued semantics are documented, display is unverified. HR005 already asks
only the indispensable screen operation; no duplicate approval question. Original
ABS-A2 NOT_VERIFIED and its uncovered second A-sample remain, even if nine other first
cases pass. Do not lower that gate or resample it. [Raw review](evidence/operations/c051-design-review/opus-response.txt),
[bounded diagnostic contract](evidence/operations/c051-inert-diagnostic-contract.json).
No substantial implementation or nontrivial harness is introduced; SWE gate not triggered.

HR005 subsequently answered with the actual public-page screenshot. Development viewed
it and checked inventory once: IAB remains absent. The requested owner operation is
complete, no repeat question. A0 tool connection remains unestablished, so the fixture
is NOT_RUN. Design is specifying the manual-observer alternative for future independent
cases, not adopting an evidence waiver or retrieving ABS-A2. This post-review fact and
prospective method are not presented as part of the completed original Opus response.

### C052 — equivalent manual UI observation, unchanged acceptance

Question carried from C051's official Opus review: can actual main-UI observation be
provided by a human while development matches the same output to host-issued evidence?
After HR005 display succeeded without tool attachment, PAL設計 supplied a concrete
[post-review addendum](evidence/operations/c052-manual-observer/PROPOSAL-ADDENDUM.md).
Its additional reasoning is not represented as a second Opus review. Original contract
already separates rendered browser navigation from HTTP byte/receipt comparison and
does not mandate a single observer. Adopt this equivalent technical method for the
nine untouched cases only, preserving original inputs/order/oracles/caps/deadlines and
first outcomes. The actual screen/link/URL must bind to the same Goal/Attempt/artifact,
receipt/hash/revision/epoch/manifest; no early or alternate retrieval of refused content.
Old ABS-A2 remains NOT_VERIFIED, never retrieved/retried/replaced or waived.

Human source turn01a11a84-67e0-7c33-93a3-615782c4fec5/message01a11a84-6918-7470-8490-b1f2008c1547
asks which Computer Use operations fail and whether the owner can operate instead.
Development verified the direct message. HR-UI-001 now requests only actual participation
timing for the concrete first case. Technical scoring, host lifetime and evidence remain
development responsibilities. No new human approval for method selection, no fabricated
operator action and no N1-07 promotion. [Ready procedure](evidence/operations/c052-manual-observer/README.md).
No product edit, new harness, new model consultation or current proof is introduced;
SWE's substantial-implementation gate does not fire. Model/host execution is NOT_RUN.

Before any launch, the owner challenged the synthetic manual-input request and then
explicitly directed ordinary technical test input/execution to development, without
trivial owner judgments. [Direct sources](evidence/operations/c052-owner-technical-verification.json).
Withdraw HR-UI-001; no readiness or usefulness is inferred. The cause was overgeneralizing
the unavailable IAB transport into a manual-test dependency. Existing Chrome CUA is a
normal authorized observer for prospective untouched cases under the same actual-browser
contract. This routine technical choice needs no new owner approval or product design
change. C051's completed review already distinguishes those cases from ABS-A2 retries.
Keep first outcomes/caps/oracles and all actual UI/output binding; never fetch/regenerate
the old refused content, and stop on any new refusal without route switching. Reuse
unchanged-component evidence only within its scope. [Risk/evidence map and prevention](evidence/operations/c052-technical-verification.md).

## D-030 — Retain multimodal research and design materials, 2026-10-08

Owner source: design chat `01a11837-e1e3-71f0-8ff8-bbaf8dc14527`, 「マルチモーダル対応設計を確認」. The owner requested:

> 再利用するようなファイルや記録やデータはプライベートレポジトリのパーソナルエージェントラボのレポジトリに適切に格納しておいてください。

> 今まで保存されてなかった情報があるのであれば、それも今回一緒に上げておいてください。

Adopt the retention instruction. Store reusable PAL research, design records and data in this private repository, with provenance, original outcomes and verification limits. Do not leave the only reusable copy in a temporary directory or chat artifact. Retain local originals; do not import credentials, unnecessary account data, or one-off machine/approval configuration as reusable settings.

The [portable design entrypoint](docs/design/multimodal-qwen38-v1.md) leads to the [dated evidence archive](evidence/research/multimodal/2026-10-08/README.md). The archive preserves 63 existing chat-export files plus 17 previously uncollected reusable files: public-source inventory/metadata and capture helper, selection list, review access/diagnostic records and official CLI reference material. [IMPORT.json](evidence/research/multimodal/2026-10-08/IMPORT.json) accounts for all 142 file occurrences across the three task-related source locations, including 59 identical duplicates and three excluded one-off launch/config files. [Archive validation](evidence/research/multimodal/2026-10-08/ARCHIVE-VALIDATION.json) records hash and structure checks. Third-party source is retained with its license as research evidence, not a product dependency.

Earlier owner direction in that chat remains the scope of the design candidate: continue existing development independently; clarify future image understanding, audio input and audio output, with video as a later extension; use Qwen3.8-27B as the fixed reasoning/vision baseline instead of widening model exploration; specify handoff and evaluation despite unavailable physical hardware. The candidate uses original images and a separate ASR → PAL → saved-response TTS flow. It is not adopted product behavior.

Opus initial research and initial design reviews completed. A separately, explicitly authorized single SWE-2 High call returned only a partial response before the 600.016-second timeout. Received findings were reconciled with the frozen source and addressed in the candidate; revised text was not independently re-reviewed. Preserve the partial result, original denied attempts and later scoped approval as history. These records are not continuing authority for another model call, new access, payment, public exposure or implementation.

All 30 candidate product evaluations remain NOT_RUN; actual Qwen/PAL capability and physical-device quality/speed are unverified. Development received the archive and verified its retained hashes, then integrated the shared-document updates after the design chat relinquished stage/commit/push. This adopts retention, not product behavior, and does not change Stable-1 completion criteria or release status. Historical handoff drafts remain unchanged; they are not current delivery receipts. Future implementation must reconcile the candidate with the then-current source and project decisions. The current development continuation remains STATE.md.

Latest direct owner clarification in PAL設計, turn01a11a86-763a-70e2-a51d-4e8631ecf901,
message01a11a86-777d-7772-a21e-a67a66479b9f: current version's goal is text-based;
multimodal belongs to the next version, with bridge/milestone/Issue design and the
unfinished review allowed to continue now. [Verbatim source](evidence/operations/c052-manual-observer/owner-next-version.json).
Adopt the current-version exclusion and future design preparation direction. Do not
automatically activate P001/future implementation, duplicate Issues/reviews while PAL設計
prepares its packet, or delay the current text-only release for that packet.

### D030/MM0 — complete next-version design preparation, not implementation

PAL設計 returned the final packet after the owner's explicit current-text/next-version
multimodal direction. Development verified all48 manifest entries plus the manifest,
complete official Opus34.233s and SWE-2 High Free62.452s raw replies and their fresh
access/cost evidence. [Plan and provenance](docs/design/multimodal-next-bridge-v2.md).
Question: how to connect the retained v1 contract to bounded next-version work while
finishing current Stable1 first? Adopt MM0 preparation and deferred MM1–4 planning.
Opus requires both reviews for MM0, a clear next-version entry boundary and version-bound
evidence. The controller narrows evidence invalidation to changed measured components;
document-only commits do not erase historical PASS. SWE's two residual contract
ambiguities are explicitly resolved in the supplemental text: admission-only reserved
key lookup excludes terminal dedupe save, and CAS/Record/Primary pending insertion shares
a transaction with unique keys. Retry keeps the same key; only a new explicit request
uses a new key. New-key queue overflow503 and reply-lock-before-Store ordering are fixed.
The original1GiB-inclusive quota is retained. No additional model rereview is claimed.

Register a separate no-deadline next-version milestone with parent/MM0–4; no existing
Stable2/P001 adoption or current N1 gate. Close only MM0 after repository retention and
actual GitHub readback; parent and MM1–4 stay DEFERRED. All30 product cases remain
NOT_RUN. Review/fixture/physical-usefulness proof remain distinct; no new implementation,
model connection, authentication, payment, public exposure or owner micro-question.

### D029/C056 — preserve explicit ask-first constraints in Primary

Question before implementation: why did UI-CLARIFY on46bd418 convert the user's
explicit ask-first logistics into a completed placeholder draft, and what is the
smallest repair without restoring unnecessary clarification? The original C055 FAIL
and unsupported relative-time wording remain preserved. Official Opus challenge via
PAL設計 completed in33.236s, one tool-free turn, fresh existing Pro/extra usageOFF;
[original response and bounded access](evidence/reviews/judgment-boundary/c056-ask-first-review/opus-response.txt).
No extra review call, paid fallback, new auth or owner micro-question.

Adopt the proposed prompt-only precedence immediately after context/memory use:
an explicit confirm-before-use condition cannot be replaced by generic text/blanks.
Resolve from available context first; ask only unresolved named facts, grouped once.
If the owner actually requires reconfirming known values, present those values in one
question. A satisfying answer continues the original delegated request under current
intent, with no invented additional approval requirement. Mere absence still permits
useful generic drafting; requested templates retain placeholders; creative permission,
record-only/quoted/not-yet and whole-request unavailable-action limits remain intact.

Narrow two reviewer suggestions: a pre-Goal none/question is the intended repair path,
not a replacement for the frozen oracle that also accepts a valid existing Expert
question. Do not require a fresh explicit permission after a sufficient answer.
The unsupported “soon” artifact claim is a separate observed error; prompt repair
alone is not proof that it is fixed. No new state/schema/router/provider/worker/tool
boundary, or relaxation of accepted behavior. This small instruction repair and
existing-harness cohort registration are routine fixes; no substantial implementation
or new harness logic requires a new SWE consultation.

Before implementation, retain a newly independent12-utterance freeze without reading
its content. After source is immutable, disclose it and use the existing qualification
runner plus unchanged fixed40 inputs with new candidate aliases. Retain old results,
never transfer their PASS to changed Primary. Also rerun the original UI-CLARIFY once
on the new frozen candidate (two fixed inputs only after valid question, cap3/600s),
then remaining approved UI flows if green. No resampling, hidden followup, invented
owner evaluation, original ABS-A2 access or acceptance change. The finite runs are
technical validation under existing scope, not unlimited usage permission.

### D029/C059 — prevent invented facts and promises in Primary specifications

Before implementation: C058 R15 correctly recognized a local draft but added a sender
commitment to contact later without source support. C054 separately retained unsupported
Mika→her in spec/acknowledgement. Question: what minimum repair preserves useful generic
drafting, real supplied facts/promises, creative permission and ask-first, without new
host semantics or an owner gate? Official Opus completed one49.935s tool-free review
with fresh existing Pro/extra usageOFF, exit0/REVIEW_COMPLETE, no fallback or retry.
[Original review and disposition](evidence/reviews/judgment-boundary/c059-source-grounding-review/RECOMMENDATION.md).

Adopt a single replacement of the existing no-invention sentence in Primary: apply
source grounding to reply and draft/correct spec, including customary future-contact
promises, personal attributes and outcomes; generated assertions do not become user
facts merely by appearing in earlier conversation. Unknown/undecided values stay so
or are omitted, without a new question gate. Keep user-supplied promises/attributes,
neutral references, ordinary courtesy, supported conditional local help and explicitly
authorized fictional invention within its scope. Narrow the review's fictional-label
parenthesis: a fictional project label cannot authorize attributes/actions of a named
person, while an explicit fictional-meeting/creative request still permits its fictional
settings. Do not ban pronouns, future tense, recipient requests or polite phrasing.
Existing ask-first, templates, context, whole-request unsupported boundaries and Expert
prompt stay unchanged. No schema/router/provider/state/authority/acceptance change.

Reject the review's claim that C054 instructed unsupported impact: the complete source
clause prohibits mentioning results/benefits/impact. Only unsupported her is observed.
Keep original question/response intact and preserve the quotation correction; no second
review or new artifact FAIL. Review preparation had omitted the surrounding prohibition
in one excerpt; retain complete negation/modality next time and verify reviewer claims.

New independent12 was frozen before code modification, contents not yet disclosed.
[Hash/count receipt](evidence/reviews/judgment-boundary/primary-grounding-heldout-freeze.json).
Freeze the17 product files after the one-paragraph edit, then disclose/retain the corpus.
Use existing bounded fixed40 and independent12 with fresh no-extra-charge proof, one
first attempt per new candidate; retain all old failures. R15 keeps EITHER, not forced
DELEGATE. Revalidate affected Primary→Expert→actual artifact paths and remaining required
UI cases; one or two review examples cannot waive existing rows or original ABS-A2 gap.
Static/host tests are infrastructure proof, not semantic proof. New alias constants
only reuse the existing runner; this small prompt/data repair does not require new
substantial implementation/SWE review. Reassess that gate if scope grows.


## D-031 — practical initial quality; end conversation-quality loops, 2026-10-08

Direct owner source: PAL人間判断 `01a1137a-8de3-7890-b874-cdd0a7125711`,
turn `01a11b1d-5f2e-7233-9010-2fd64c9ef8d6`, messages
`01a11b1d-604c-7b13-b96a-d45f20b1b47e` and
`01a11b1e-19a9-7531-bf79-24d3fb83dda8`:
「80%の出来でいいんじゃない？あとは学習と経験で改善できるならそれでいい。
改善期待でもいい。作り込みすぎるよりかはよっぽどまし」 and
「会話の品質についてはこれ以上やるのは不毛だと思う」.
[Full direct text and provenance](evidence/reviews/judgment-boundary/c060-grounding-results/owner-quality-direction.json).
Development independently read those human messages. PAL設計 agreed the minimal
acceptance interpretation: stop further conversation/prose-quality tuning, cases and
reviews; retain minor editable local-output shortcomings as known limitations. This is
already human-finalized priority/acceptance direction, not a proposal needing another
owner answer. Before final adoption, one official Opus38.034s/exit0/REVIEW_COMPLETE
consultation checked only the minimum acceptance delta and retained functional boundaries,
using fresh existing Pro/extraOFF, no tools/MCP/retry/fallback. It did not tune or test
conversation quality. [Original packet and disposition](evidence/reviews/judgment-boundary/c060-quality-policy-review/DISPOSITION.md).
Adopt the quality/functional distinction, narrow safe-none to safety proof rather than
successful correction, and reject Opus's mistaken classification of ABS-A2 as a PAL
browse/send refusal: it is an unobserved generated artifact after client navigation denial.
The original remains NOT_VERIFIED. Manifest SHA was mistyped in the chat; all11 original
files match the actual manifest17ebb65c, and the author's correction is retained. No more
quality reviews/corpora are planned. Existing review gates for other substantial changes remain.

Adopt: no numeric80% threshold or new rubric. N1-05's historical zero-defect prose gate
is nonrequired; its old FAIL/PARTIAL/NOT_VERIFIED evidence remains. N1-01/02/09/10 retain
functional capability and host boundaries without repeated full quality requalification.
N1-07 remains one real overall usefulness evaluation, with minor quality feedback allowed
as known limitations rather than requiring every phrase to be repaired. Preserve existing
no-invention model guidance; no source/product code is weakened or changed here.

Do not relax external actions, money/auth/permissions, wrong-target changes, reference-stop,
data integrity, dedupe/recovery or truthful canonical completion. An actual failure of a
needed function still blocks that function. Do not rebrand prose tests as safety tests.
Do not claim an automatic learning/update mechanism: current correction and bounded
source-backed memory can use provided context; later developer changes can incorporate
feedback. Neither is automatic model training or guaranteed self-improvement.

C060 already captured35 passing Primary turns across Japanese8, English8 and independent12.
The active negative cohort received N01 before the instruction, judged that one response,
and closed normally without N02–24. Preserve it PARTIAL. The planned11-host quality sweep
is cancelled unexecuted. Original ABS-A2 remains refused/NOT_VERIFIED; its quality-only
second-sample quota is no longer a release gate, never access or replace that content.

Remaining technical work is the already-frozen TARGET-C functional path: two same-label
paused Goals, explicit target question, source-bound choice, correction of that Goal only,
and actual local artifact/receipt displayed. Reuse the existing two inputs and cap3/600s;
minor sentence-count/wording defects are observations, not a reason to resample or tune.
Then preserve available usable outputs for one owner evaluation and do the final full
suite/version/constraints/GitHub audit. No new acceptance case, harness or provider design.
Stable-1 remains text-only and is not overall project completion; future scope stays dormant.

## D-032 — owner-requested finite trial time, 2026-10-08

Direct owner request in PAL人間判断: 「もうちょと伸ばしてせめて2時間」,
turn `01a11b5d-802f-7bd0-8e68-d93f41313d17`, message
`01a11b5d-813b-72d1-9a89-8612f52c40b6`, independently read by development.
[Authority and original host observation](evidence/operations/c063-owner-extension.json).
The operational target is at least7200 seconds remaining when the owner receives the
ready trial, same DB/URL and actual remaining invocation budget, existing official
authentication and extra usage OFF. No repeated owner approval is needed for that scope.

Question to official Opus and SWE-2 High through PAL設計: challenge a minimal explicit
`--native-session-seconds` option, default900/max8100 seconds, while keeping fresh
load/consume at900, one-use canonical proof identity, dual clocks, call budget, auth
checks, subprocess deadlines and canonical state unchanged. This is duration-boundary
review, not a conversation/prose-quality review under D031.

Opus completed one41.920-second/exit0 review: proposal sound; validate a strict integer
duration, pass it to status and both complete checks, reject any native option with
mock including explicit900, and carry the observed remaining budget through a stopped
old PID into the same DB/port/cwd. No new quota ledger or switching architecture is
needed for the observed expired host with16 unused calls. A call already admitted
before expiry retains the existing120-second generation timeout.

Adopt this bounded design before implementation. An extended provider constructor
must still require a fresh900-second proof; changing duration never changes the
consumption hash or revives a used/old proof. Default provider/harness behavior stays900.
Use8100 only explicitly for this requested trial and verify at least7200 remain at
handoff. A fresh explicit restart is allowed here; no automatic renewal or schedule.
The implementation review result and original evidence are recorded below before code
changes. Rejected scope: unlimited session, increased call allowance, new auth/payment,
proof timestamp repair, canonical DB repair, and new prose-quality qualification.

Official SWE-2 High completed one101.352-second/exit0/REVIEW_COMPLETE review after
fresh existing authentication and its standalone Free model row were checked. Opus used
fresh existing Pro/extra usage OFF; both were tool-free supplied-source consultations
without fallback/retry. [Original reviews and disposition](evidence/reviews/two-hour-trial/DISPOSITION.md),
17 files verified against manifest `ffd885a266057ad3efeb15a797ae1f3b9f176966fcefce475c38dac11fbea6ec`.
Adopt strict integer1..8100 validation in both API constructor and check, outside proof
error conversion; invalid configuration raises ValueError. Keep current wall inclusive
and monotonic exclusive bounds, fixed constructor duration, and existing lock placement
(SWE's “pre-lock” wording does not move admission outside the lock). Constructor performs
default900 freshness check. Tiny already-expired durations fail closed; do not introduce
another admission policy. Default tests that constructed stale providers must instead
construct fresh then advance the test clocks, preserving their original rejection claim.
Pin successful complete() after900, expiry after auth, clock fences, budget exhaustion,
same proof reuse across durations, mock discrimination and HTTP/UI deadline agreement.
Preserve current120-second generation deadline and supervisor cleanup grace; the displayed
deadline is new-call admission, not a hard process-stop promise. No further review needed.

## D-033 — align work selection with actual assistant value, 2026-10-08

C064 independently verified three direct owner messages in the persistent human/design
lanes. [Exact text, message IDs and current source map](evidence/operations/c064-owner-value-gap.json).
The owner accepts necessary component tests, rejects the current conversation/draft-only
screen as delivering the desired PAL usefulness, and requests design alignment at Issue/
milestone progress so repeated attention to details does not displace the actual goal.
This is received negative value feedback, not an unanswered evaluation, release approval,
or permission to activate new external capabilities. N1-07 stays non-PASS.

Adopt the directly requested operating correction without another owner question: at
Issue entry/closure identify its design role, added practical value, necessity now and
remaining project gap. At milestone entry/exit and direction drift/repeated causes,
obtain one official Opus alignment review through PAL設計, with existing access/cost gates.
Use the existing CHECKPOINTS/STATE/Issue records and make the conclusion affect the next
work choice. Do not add a per-commit review, wording exam, new automatic approval gate,
or repeat the same draft-only owner trial. D031's stop on prose-quality loops remains.

Current facts: Primary reasoning and durable Goal/WorkOrder/local-draft Executor/host
receipt control are implemented. Thus an Expert control component exists, but its sole
capability is local_draft; there is no product external-information/task connector.
Official Claude model communication and controller GitHub/CUA/reviewer capabilities
are not PAL external tools. Existing277-test/finite real-function evidence remains
component evidence with its original limits, not integrated usefulness. No code changed.

Question assigned to one official Opus consultation in PAL設計: challenge the project's
current direction against SPEC/DESIGN and latest proposed P001v2; identify the smallest
useful external-information → Expert work → verified reversible result slice, compare
a repo-bound existing official GitHub read with the smallest useful alternative, and
separate available existing authority from a real capability/scope adoption decision.
The review is in progress at this recording. No changed product design is adopted yet,
and no review/implementation is duplicated in development. Preserve the raw review and
access evidence before recording its disposition. New capability implementation still
requires adopted scope and the existing SWE-2 High substantial-implementation review.

The process failure and next verification are recorded in docs/DEFECTS.md. This boundary
review must produce a value-bearing next unit rather than another conversation-quality
cohort. P001/future multimodal scope stays unadopted; current safeguards, no-extra-cost,
no new auth/public exposure, and paused schedules remain unchanged.

### D033/C064 — subsequent pause and design rebuild direction

The owner next explicitly instructed a development pause for learning from this failure,
then directed rebuilding the design into small milestones, checking actual implementation
with Opus at each boundary, continuing an unmet milestone and advancing when achieved.
Conversation and draft composition quality should be delegated to the model; focus on
giving Expert a concrete work instruction and obtaining its result. [Pause source/actual
shutdown](evidence/operations/c064-owner-pause.json) and [subsequent direct direction](evidence/operations/c064-redesign-direction.json)
were independently read. Do not treat this as an indefinite unanswered approval request,
permission to resume the old plan, or authority to discard all useful components.

Goal was changed to PAUSED. Owned trial PID20002 shut down normally; port59684 is closed,
original DB and a local private backup are preserved with unchanged6 records and zero
Goals/Attempts/artifacts/receipts. No new product code, tests, generation, trial extension,
release or schedule. Design preparation and the retrospective are now the authorized work.
The prior design turn is interrupted/archived. Its packet-generation command failed on
source encoding; a subsequent runner invocation failed because the file did not exist.
No completed Opus review exists. The earlier in-progress expectation above is superseded,
not review evidence. Do not retry the same missing script or claim another chat received
a handoff when delivery fails. Preparation should use structured/encoding-safe file writes
and verify its file before execution; no provider call is needed to diagnose this failure.

[P001v3](docs/plans/P-001-v3.md) is the single new DRAFT/UNREVIEWED/NOT ADOPTED plan,
not a second authority source. Its first candidate outcome is one actual bounded external
read through PAL, Expert work and a host-verified reversible result. Controlled continuation
and integrated evaluation/release are subsequent small candidates. Model composition
quality is not a gate. Preserve functional targeting, evidence, permissions and cost limits.
The exact new capability/scope still needs official Opus review and material human adoption;
the already explicit checkpoint/quality direction does not need another approval.

Next is to establish the designated design lane and review this concrete draft. The old
archived chat has not been revived and no new chat created. Missing routing does not
prevent preparing the evidence/plan, but it must not be reported as a completed review.
No first milestone is activated from this draft alone, and no product automatically restarts.

## D-034 — scoped SOL/CO development start, 2026-10-09

Direct owner source: chat 01a11c78-a3bc-76e1-b4ee-2451d5c0f1c2, latest message titled 開発体制：SOL統括＋Common Orchestrationによる並列実装. Owner explicitly authorizes delegation and necessary private PAL development materials to existing CO SOL/SWE-2 High/Devin/Astra/Opus routes, requests exact runtime/model/capacity identification and isolated scopes, and accepts actual capacity below30 with sequential work. Same existing Opus telemetry uncertainty alone is not a new send-approval gate. No new auth/service/additional cost/publication or refusal bypass is authorized.

Apply this newer direction to the first coherent development-preparation unit, INT-00: preserve/import the v5 candidate, obtain an actual Opus design-delta assessment, implement pure common contract types/examples via SWE, inspect and independently review the same diff. This does not label v5 already reviewed, activate all proposed product capabilities, alter Stable-0 acceptance, or resume old schedules/trials. Later external-capability adoption must be based on the concrete reviewed scope, not GitHub metadata or a collaborator's opinion.

Observed CO0.4.4 task entrypoint supports qualified Claude Opus5.5 and Devin SWE-2 High and one inference at a time per state, not30. Existing state is reused only through CLI; no direct state edits, route substitution, engine/capacity workaround or alternate state. SOL/Astra development APIs are not qualified co-task routes. Current Native quota is unknown; fresh official account observation shows Claude Pro extra usage OFF and SWE Free. Auth metadata alone is not inference proof.

Keep the original checkout's uncommitted record changes, unreviewed P001v3 and runtime data intact. Development uses an isolated local worktree and an explicit committed input baseline. CO's scoped task payload supplies only listed design/source files, not owner history, runtime DB, auth files or private account metadata. Existing Native ancestor/global instruction roots are recorded as potentially loaded in call evidence; measured tool-free setup is not full-machine containment or a completed transcript for the unknown SWE attempt. CO verified means its declared verifier/files/review version only; SOL must inspect/integrate/retest. No review had completed at the initial preparation checkpoint; later actual outcomes follow below.

### D034 / INT00 common-wire disposition

The corrected actual CO task `6a9dea446fa241ceb6ee876bbdb08be9` accepted a three-step
plan (819/815/840 UTF-8 bytes), completed a separate `claude/claude-opus-5-5` design
call, and entered `devin/swe-2-high` implementation. [Raw design and scoped SOL
disposition](evidence/operations/co-int00-20261009/design-disposition.json). This is
an actual common-wire design consultation, not an independent full-v5 service or
product review. Final implementation review and integration are still pending.

Adopt the technical binding `PAL-v5-common-wire / INT00/1` for this pure module:
one flat `kind` discriminator for C12 Action; closed strict Result variants;
mandatory allowed-Ref set at model DraftBrief/Action entry points; missing optional
lookup refs distinct from an empty array; text/plain and text/markdown compose;
zero budgets as exhausted, without implicit unlimited defaults. Do not mint formal
condition IDs or infer permission from parsed data. These choices settle shared
serialization only and do not activate a product connector or alter existing runtime.

Retain host obligations for later actual providers: resource/grant validation,
fixed current revision/epoch and state checks, saved identity/kind/provenance,
reference availability and no grant expansion. U1/U2/U6/U7/U9 are deferred to those
providers and their contract tests; parser examples cannot qualify them. The next
milestone must bind real provider/consumer values without private reinterpretations.

The design's claim that `raise ... from None` removes exception context is false:
a local Python3.13 check confirmed `__context__` remains while display is suppressed.
Require bounded errors without retained raw decoder context in the actual returned
code and tests. Preserve the design output and check implementation instead of
treating reviewer wording as proof. No state, returned plan or CO code was edited.

### D034 / actual implementation outcome and continuation limit

The same task's SWE implementation reached900seconds and returned exit75 with
route_timeout/inference and unknown result/process outcome. [CLI status](evidence/operations/co-int00-20261009/paused-status.json)
confirms no selectable route options, no returned code, no verifier or independent
code review, and verified=false. Registered Opus/SWE candidates are information only;
the runtime does not offer them as switches for this unknown call. Do not retry or
create a replacement task for the same work, alter the report or raise the timeout.

Keep the task deferred; the exact evidence and preservation recommendation were
delivered to PAL人間判断. No real human choice is recorded. An explicit cancellation
can close the CO task but cannot prove the prior request stopped. This is a CO
execution outcome limitation, not a fresh private-source consent issue, extra-cost
request, or reason to put all PAL work into blanket human approval wait.

Independent preparation is complete: imported candidates with hashes, preserved raw
Opus design and SOL wire binding, [five shared synthetic expectations](docs/design/contracts-v5/SHARED-EXAMPLES.json),
original13-record integrity and full277-test baseline PASS. Documentation validation
is not a CT/E2E implementation PASS. INT00 implementation and later dependent modules
remain incomplete; no product source, live DB/service, model configuration or CO changed.

### D034 / owner continuation and later parallel-runtime update

Independently read a real userMessage in PAL人間判断, turn
`01a11c9f-6db9-7f92-ba4a-96ed1ad16b07`: the owner states CO0.3 already has parallel
implementation, CO0.4 parallel support is in progress, and directs continuing possible
work until a parallel-capable0.4 version is available, then updating and using it.
[Original text and source](evidence/operations/co-int00-20261009/continuation-policy.json).
The0.3 capability/progress statement is owner-provided context, not this task's measured
CO0.3 performance, and is not an instruction to downgrade or modify CO implementation.

Adopt this continuation/update authority with existing cost/auth/data/public boundaries.
At normal work milestones or re-entry, inspect the official release and migration
instructions; preserve current state and the unknown task, use a supported update,
measure actual parallel/routes/capacity, then report evidence to the human window.
Do not create a recurring monitor or resume old schedules. The owner did not select
cancellation, retry or switch for the unknown SWE request; no decide is authorized.

Current official GitHub release check returned only `common-orchestration-v0.4.4`
(2026-10-08T15:40:28Z), no later formal release at this checkpoint. [Release observation](evidence/operations/co-int00-20261009/release-check.json).
The existing runtime remains0.4.4. A development HEAD advance is not a published
parallel-capable version or qualification. No update was performed from this check.


## D-035 — official CO0.4.5 update and independent preparation, 2026-10-09

Actual owner update source: PAL人間判断 turn
01a11d77-e713-7890-8422-e1e683b564d4, userMessage
01a11d77-e77e-7740-9e1c-dc4c9bd2631d: 「対応版が出ているので写真に更新してください。」
Read independently as the follow-through to D034's explicit available-release
update/use direction; the human lane explained the contextual latest-version
interpretation. This does not resolve or permit retrying the unknown SWE call.

Official common-orchestration-v0.4.5 was published2026-10-08T19:29:43Z. Retain
published archive/manifest/checksums privately; verify both SHA256SUMS entries and
all96 manifest files, then install the fixed payload under Documents/PAL/co-runtime.
Isolated import and VERSION identify this0.4.5 runtime. Existing state is reused via
CLI after an unchanged private backup; status preserves the same awaiting_decision
unknown task, no selectable switch. Old CO process inspection observed none;
no claim of remote cancellation. No CO source/global configuration/route edits.
[Installation evidence](evidence/operations/co-update-045-20261009/installation.json).

New supported semantics: independent normal tasks have separate workspaces and
journals under shared qualified state, with12 host slots per Native adapter.
Available task routes are still only exact Opus5.5 and SWE-2 High; Sol6.1/Astra
are unsupported here. Capacity readback initially has zero reservations/executions.
This is capacity evidence; PAL parallel execution and integrated product acceptance
must be measured separately. No30-task claim or extra jobs to fill slots.

Adopt two independent pure technical preparation boundaries in
[PARALLEL-SCOPE-1](docs/design/contracts-v5/PARALLEL-SCOPE-1.md): EXE02-request/1
validates a repo-bound GitHub read request and fixed argv without executing it;
ART01-content/1 prepares bounded UTF-8 bytes and hash without saving anything.
They leave operation/grant/recovery, shared contract types, DB, source checks and
real product capability activation to their owners. Scope does not change live
PAL behavior or adopt the full v5 service plan. The original unknown task retains
its four files; no replacement task or duplicate common implementation is sent.
SWE handles A implementation with Opus design/independent review; separate Opus
contexts handle B implementation/review. SOL alone integrates and records results.
Fresh existing CLI auth/versions and official Pro extraOFF/SWE exact Free model
were observed; no new authentication, billing/publication or stopped schedules.


### D035 / actual implementation and milestone disposition

Three ordinary tasks completed through the fixed official0.4.5 runtime and shared
qualified state: A2363ba2f94ca4183906f00aabb66dd50, Bb0fd78557fc64e2b834aa232060915d0,
C4fada68c758b4af8b65c4d64eca42dbf. Separate local workspaces and read/write sets;
13 actual Native calls (12 Opus5.5,1 SWE-2 High Free), two independent calls/tasks
at most concurrent. Confirmed local process intervals overlap96.164s; no remote
compute-time inference or30-way execution claim. Final host reserved/executing0.
[Actual records](evidence/operations/co-update-045-20261009/final-checks.json).

Adopt the pure request/content implementations as scoped preparation, unused by
PAL. SOL inspected both base diffs, enforced exact str argument keys after a
reproduced review finding, and corrected a historical-freeze test that wrongly
accepted the old trial freeze as current. Production validate_freeze and retained
manifests are unchanged; obsolete proofs must still fail closed. Opus final
milestone review agrees MET for preparation and UNMET for PAL/service/user value.
The independent note review caught its own INT00/Operation ownership error and
length limit; one CO repair/re-review corrected both, without source changes.

SOL confirmed the five reviewed source/test hashes match committedbf1759f and
full316-test evidence. Targeted39 tests and synthetic mock preview PASS; full316
PASS22.074s. Raw failures, design, initial request_changes and final review remain
available. No new host guard, permission, activation, old-proof renewal or existing
runtime behavior is adopted from these preparation results.

The remaining INT00 task stays unknown/awaiting_decision with options=[], unchanged
pause digest and preserved pre-update state. No cancellation, resume, retry or
switch choice was recorded. Common types remain its dependency; Operation ledger
belongs to later EXE01. This is not a blanket project approval wait. Original13
records remain byte-identical, original DB/services are not changed, trials and
schedules remain stopped. Update PR19 with this exact preparation scope and send
completion evidence to the existing human window; no public release or Issue closure.


### D035 / owner parallelism question and next independent batch

Independently read PAL人間判断 turn01a11d9c-c641-7fd1-8a66-5fcca4a9b044, actual
userMessage01a11d9c-c6bb-7051-be79-bd7f23d31425: asks whether2 parallel meant no
more work, a blocker, or a choice. [Exact source/selection](evidence/operations/co-update-045-batch2-20261009/selection.json).
SOL chose a two-module initial runtime pilot; no third concurrent send/rejection
occurred. The third prior run was dependent review. This was not a global shortage
of independent work or a two-call runtime cap. The earlier report omitted this
selection rationale; explain it to the human window without another approval.

Continue within original development authority, using
[parallel scope2](docs/design/contracts-v5/PARALLEL-SCOPE-2.md): small file-response
codec, bounded byte accumulator and host-metadata byte-integrity check. They have
settled local interfaces and disjoint files, no shared types/DB/capability activation.
These are needed read/storage/verification boundaries, not dummy capacity tests.
Launch three actual independent tasks under the same qualified state and declared
caps; independent model reviews and SOL integration remain required. UnknownINT00
is not repeated; service/provider/whole-product acceptance remains unmet.


### D035 / C067 actual three-task preparation and assessment closure

D47b8853cad145fa9330407acb617020, E1b22bca6ed14449ba1637d2caa538948 and
Fd84e6010a3584678b8c3a79bfaedaab0 completed with separate Opus reviews. SWE Free
implements D/E; Opus implements F in a different context from its review. SOL
checks declared files/base/diff/verifier versions and integrates only those files.
Actual peak3 is proven by eight completed local Native overlap segments,
total262.733616s. No3+ capacity rejection occurred; first2 was a small pilot choice.
Local cap remains12 per Native adapter; provider quota unknown,30 not available.

Adopt the three unused pure preparation helpers within PARALLEL-SCOPE-2 and a six-case
synthetic read-bytes/decode/content/integrity test. Root corrections: exact fixed
buffer error codes after a reproduced hostile/subclass case; declared-size precedence
assertion; explicit invalid-integrity results. D's single CO repair corrects only a
test-helper keyword; all17 malformed Base64 cases remain. No validation is weakened.
Root full399 PASS22.153s, targeted122 PASS; all11 source/test hashes match committed
4ebab5a29e3c4c1b0dac939aa4d9a60364974bef. Real service/PAL/value remains UNMET/NOT_RUN.

Independent Opus task Gcc4c676211714e51a18c0f1604d8f0c9 finds no source blocker and
confirms the same hashes, but its document task remains failed/review_unresolved,
verified=false after one allowed repair left a citation error. Preserve that result;
no resume or status rewrite. Known completed calls distinguish this from unknown INT00.
H5c28f94d39ba4a619d39cc3f62b5f3f0 closes only the specified attribution line, with
an exact document verifier and independent Opus approval. Final476 tokens, other text
unchanged. H does not rerun source/product tests or claim a new code review. SOL
reconfirms the11 unchanged hashes before adopting the corrected assessment.

Batch2 total5 ordinary tasks:4 verified,1 failed,23 actual Native calls (20 exact
Opus5.5,3 exact SWE-2 High Free), final reserved/executing0. Pre-task verifier/host
scripting errors created no extra Native task; retain the preflight evidence and
proportionate prevention in DEFECTS. [Final records](evidence/operations/co-update-045-batch2-20261009/final-checks.json),
[final assessment](evidence/operations/co-update-045-batch2-20261009/milestone-review.md).

All96 runtime payload files,290 pre-update state files and13 original records remain
byte-identical. Existing Pro extra usage remainsOFF and SWE exact model remainsFree;
no authentication/billing changes, public release, old schedule/trial restart or CO
implementation edit. Old INT00 pause digest/options/unknown outcome unchanged; its
four files are still absent. Next dependency is its WorkRef/Ref/Action/Result types;
Operation belongs to EXE01 and canonical ART/grant/source checks to later services.
Update the same private Draft PR19 and report actual outcome to PAL人間判断. No
whole-project approval wait or new human usefulness request is inferred.

C067 delivery complete: existing Draft PR19 and Issue6 current continuation updated;
previous Issue6 body retained as history. Fresh readback confirms private repository,
open/draft PR, published83c01a9 and unchanged main94fcacb. Current code/test source
remains4ebab5a. The authorized human window received the report and its agent
summarized it; no actual owner choice, read receipt or usefulness PASS is inferred.
Publication/delivery evidence is linked from STATE; later commit changes records only.

## D-036 — diagnosed unknown call and explicit alternative implementation, 2026-10-09

Direct owner sources were independently read in PAL人間判断. Turn
01a11dfe-89e5-7f81-86ce-7d8b66cf57da/userMessage01a11dfe-8a72-7c63-855f-90eb8ad3acf5
requests official Devin/SWE information and concrete diagnosis; CO is a development
tool, with no current owner decision pending. Turn
01a11e03-d386-77c0-8faa-41f0ab765513/userMessage01a11e03-d444-78c1-9fab-b0e861d29d1d
directs SWE-2 as primary when usable; Astra, Sol6.1 or AGY Sonnet5.5/Opus5.5 as
alternatives while unavailable, prioritizing AGY due current usage. Direct calling
is allowed when the CO adapter cannot support the route. Necessary PAL development
material is within this specific route instruction; no credentials, irrelevant
personal data, new auth/fees, publication or broader permissions are added.

The original task is not cancelled, retried, switched or relabelled successful.
Correlated Native logs, exact prompt digest, official session listing, read-only
single-session DB metadata and task workspace show: local parent/ACP are absent;
no stored assistant/tool response or recoverable implementation; no task file changes.
The900s deadline is corroborated by900.149432s file mtimes. Both observed old runtime
revisions have identical relevant cleanup code, but that code suppresses stop errors
and this attempt has no durable cleanup receipt. Its exact loaded revision, remote
inference terminal outcome and underlying no-response cause remain unconfirmed.
The old state/pause digest/options=[] are preserved. CO0.4.5 offers no documented
external-evidence reconciliation command. [Facts/URLs/limits](evidence/operations/co-int00-20261009/diagnosis.json).

Adopt the explicitly authorized separate implementation: isolated workspace/branch,
fixed baseline and the existing INT00/1 contract/scope/disposition; text/diff adoption
only by SOL. No old output is automatically applied, and no shared DB/service writes
are permitted. An independent reviewer uses a fresh context after implementation.
This is the owner's alternative-route instruction, not a fabricated CO pause choice
or a workaround for a service/security denial. Keep the old workspace/journal intact.

AGY model listing succeeds with exact Opus5.5/Sonnet5.5 variants on1.3.1, but quota and
no-credit-fallback are not yet verified. Its PAL cwd trust prompt was declined. A
home-wide usage/settings startup was rejected by automatic approval review for its
broad file/read/execute scope; no startup or alternative home access is performed.
Current task selects native gpt-6-astra for isolated implementation and fresh
gpt-6.1-sol for independent review. Current Codex Pro ordinary usage is allowed,
40% weekly used; no credit purchase, usage reset or paid fallback is authorized.
Report actual launch/results and any remaining AGY limitation to the existing
human window. Do not ask the owner to repeat the technical implementation decision.


D036 implementation/assessment outcome — C068:
Astra authored d286fe7 (four INT00 files) in an isolated worktree; a fresh native
Sol6.1 context approved the exact commit. SOL's601df87 cherry-pick is byte-identical.
Consumer tests8892440 add five pure composition cases. The unrelated probe race
fix92732afa is separately reviewed; it changes only diagnostic shutdown handling,
not product authority or historical live acceptance. Root full422 PASS22.424s and
all seven source hashes are recorded in co-int00-20261009/verification.json.

Exact claude/claude-opus-5-5 via CO0.4.5 independently assessed the shared-wire design
as ALIGNED at9390c38, with no design blocker. SOL inspected/applied the sole note
and confirmed its protected inputs and source92732afa hashes at the review base.
Taska9fdddb584e241b99ad1c748b49fcbb7 is verified for the bounded document verifier;
there is no CO code-review step or whole-product verification in that flag. Two
calls completed. Its predecessorad95757c7dd847fcbcabfd3903bec53c completed one call
but failed plan_invalid (instructions5795>4096 bytes); no worker/verifier/file write
occurred. Both outcomes are retained, total3 new Native Opus calls. The corrective
prompt requested<=1200 bytes; actual1367 satisfied the runtime4096-byte bound,
not that stricter prompt target. No runtime limit was changed.

SOL dispositions of the design note:
- The author-time pending statements are superseded by current STATE/ACCEPTANCE and
  verification, preserving the exact author snapshot. D036 replaces only the old
  model/sequence assignment, not INT00 semantics.
- The root branch lineage is a698391 ->601df87 ->8892440 ->92732afa ->9390c38.
  Every supplied source hash at92732afa matches the review base. Source authoring,
  synthetic consumer work and the independently reviewed probe fix are distinct.
- The note's phrase "both condition check enums" is imprecise: one CheckKind enum
  with three values is shared by DraftCondition and Condition. This wording does
  not change the code or accepted design. Wrong-kind decoder errors remain bounded.
- Full v5 service adoption, host authority, persistence, providers, live UI and
  usefulness remain unproven. A parsed Ref/value is never operational authority.

Select the next bounded preparation unit proposed by Opus: TSK-01 C03.create and
C02.get_work over an isolated mock SQLite schema. Scope includes host condition-ID
issuance, nonexpanding host/request Grant intersection, zero budgets, atomic
intake/event storage, key replay/conflict and not_found/stale/rollback tests. SOL
owns shared schema/integration, with isolated implementation and an independent
exact-commit review before adoption. No real DB/model/connector/UI is needed.
This is a technical next-work selection within D036; it is NOT_RUN and does not
activate the full candidate plan or create a new human approval request.


## D-037 — scoped AGY qualification and TSK01/1 intake disposition, 2026-10-09

Actual owner turns in PAL人間判断 were read directly:
01a11e23-a42e-7431-aefa-10c2fdcb00d2/userMessage01a11e23-a4ad-7c20-a99c-449c3e161ea7
approves AGY Opus5.5 when the official Claude route is limited, including necessary
private PAL materials, and requires independent work to continue.
01a11e25-7a70-72d0-ba3b-694d51b6dd21/userMessage01a11e25-7aeb-70e0-9a88-3154f0532061
authorizes the specified PAL directory and a narrower dedicated work directory if
needed. This does not authorize home-wide trust, publication, new auth or extra cost.

Automatic review approved startup and exact workspace trust only for
`/Users/hattoritoshiyasu/Documents/PAL/agy-work/intake-review-20261009` after that
owner instruction. The earlier home-wide startup was refused and never retried.
The exact trusted path was read back; no global trust override was used. Actual
CLI banner1.3.2, existing Google AI Pro session, `Use AI Credits` OFF, Claude/GPT
weekly71.83% and five-hour100% remaining were observed before calls. No billing or
login setting changed. The earlier language-server1.3.1 observation remains a distinct
observation, not evidence that this task updated software.

Two sequential direct AGY calls requested `claude-opus-5-5-high`, plan+sandbox,
with PAL-only synthetic contract inputs. First call SUCCESS in74.895s returned REFINE;
follow-up SUCCESS in40.583s returned ALIGNED. The second stream init independently
echoes the exact model ID and shows only user_input/system_message/agent_response
step types, no tool steps. Its327.037s/2-turn result metadata is conversation-cumulative,
not the second call wall time. Original staged input hashes match. Raw streams may
contain reasoning/account data and are retained locally, not in this repository.
[Qualification](evidence/operations/co-int00-20261009/agy-qualified-settings.json),
[refinement receipt](evidence/operations/co-int00-20261009/agy-refinement-receipt.json),
[initial review](evidence/operations/co-int00-20261009/agy-intake-review-v1.md),
[corrected review](evidence/operations/co-int00-20261009/agy-intake-review-v2.md).

SOL rejected the first review's zero-budget/empty-capability denial and its source
check before BEGIN: exhausted budgets remain valid stored values, and immutable Ref
IDs do not make availability immutable. Opus explicitly withdrew both recommendations.
Adopt TSK01/1 scope before implementation: strict C03 create/C02 get_work, host-only
request_scope, nonexpanding grant, same-transaction required source_gate, atomic
intake/event/replay, replay-before-current-checks, missing revision=>not_found.
The root scope follows exact C02 fields (expert is in create output) and permits
embedded immutable conditions/grant/bindings to avoid redundant persistence tables.
The gate is trusted host code with no I/O or transaction control; it is no new
capability for models. Replayed intake grants no current execution authority.

[TSK01/1](docs/design/contracts-v5/TSK01-SCOPE.md) is authorized unused preparation;
real MEM availability, PRI authorization resolution, shared C14 services, historical
revisions, execution owners, providers and product activation remain NOT_RUN.
AGY is not a CO adapter. D036 allows this direct fallback; no new engine/state or
claimed CO verified flag is added. Use one AGY call at a time until actual route
concurrency is qualified. CO0.4.5 current capacity snapshot has0 reserved/executing
on both adapters, host cap12 each; that is neither vendor quota nor30-way proof.
Assign isolated AGY Opus5.5 High implementation, native Astra independent boundary
analysis, SOL integration, then a separate independent code review after output.
No technical human decision or old unknown-call cancellation/retry is implied.


D037 implementation-route correction (before adoption): AGY's first code-generation
request failed with explicit schema-key INVALID_ARGUMENT400 and no code. The corrected
envelope used fixed module/tests/note keys. That call exited0/reported SUCCESS, but
stderr says `print timeout after 7m0s with turn in progress; returning partial output`.
Host wall425.622s is measured; CLI duration0 is not useful. JSON is unterminated, so
root rejects whole-unit completion. Only the fully closed module string12465bytes,
hash29f5162c..., was recovered, syntax-checked and retained as unverified. Complete
tests/note are absent. [Receipt](evidence/operations/tsk01-20261009/author-receipt.json).

AGY conversation67432c30-a8e8-4660-8425-8c3a55feff4e has unknown remote terminal
status; no retry/resume/cancellation was issued. Its text-only stream has no tool
steps. Local exit is not proof remote inference stopped. No new AGY call until
reconciled. The two completed design reviews remain useful; their success does
not qualify this larger structured code-output request.

stderr also says `--mode plan has no effect while slash command expansion is disabled`.
Earlier records describe requested flags, not proven plan enforcement. Observed
no-tool streams and isolated material scope are separate facts; do not rely on that
ignored flag as a permission boundary. No setting or permission bypass was used.
Future route checks must resolve effective mode and final-turn status with supported
controls. No new human technical approval is created by this implementation defect.

Continue through the owner's approved native fallback. Astra now authors completion
and tests in the isolated candidate worktree; it no longer independently reviews
this unit. Separate Sol6.1 reviews the completed exact commit and root consumer
changes. Root owns adoption. Condition IDs are unique within each immutable Brief
addressed by WorkRef (consistent with C09); no cross-Goal registry is required here.
Default UUIDs avoid ordinary reuse; injected collisions test the actual Brief/Goal/
event uniqueness boundaries. This clarification adds no product authority.


D037 supported-control check: official AGY documentation describes interactive
`--conversation ID` as loading the named conversation, and stream ACTIVE/DONE
states separately from result status. The failed code stream has2423 ACTIVE agent
updates and no DONE; init reports request-review. Root proposed loading only that
exact conversation, without a prompt, from the same approved narrow workspace.
Automatic approval review rejected it before startup because it might resume or
duplicate the still-unknown generation. No same-operation workaround was used.
The concrete command, risk and optional scoped approval were sent to PAL人間判断;
no actual owner response is inferred. This does not block the native completion.
[Control evidence](evidence/operations/tsk01-20261009/agy-deferred-route.json).


D037/C069 actual unit outcome: native Astra completed author commit3e828019 with
14 targeted tests; the recovered module's hash is unchanged. Root cherry-pick9689462
preserves all three authored files, then8db45fd adds four synthetic consumer cases.
Separate native Sol6.1 APPROVES exact8db45fd; root source hashes match and full440
PASS22.989s, exit0. TSK01/1 unused preparation is MET. Details and retained failed
attempts are in evidence/operations/tsk01-20261009/verification.json. Real PRI/MEM
source/permission authority, history, C14 sharing, execution/services/providers/UI
and human value remain NOT_RUN. The current receipt supersedes author-time pending
review/full-suite text; it does not rewrite author provenance or promote product
acceptance. Next dependency is the shared MEM/TSK same-transaction source boundary.

## D-038 — checkpoint continuation and requested loop proposal, 2026-10-09

Actual owner instructions were read in PAL人間判断, not inferred from its agent:

- Turn01a11f76-dac6-7462-959a-a7ab1326f91a, message01a11f76-db05-7470-8f4a-2e5dacf60cf1:
  the owner challenged why development stopped after the expected-design evaluation.
- Turn01a11f77-8c93-7560-9709-5e08d419c3e4, message01a11f77-8cf6-75d3-8302-701c63715b49:
  「閉ループで開発できないの？」
- Turn01a11f78-c488-75f1-b09f-97f95f3edb55, message01a11f78-c4ce-7133-b8c7-d949f7a50aab:
  「チェックポイントを置く分にはいいけど設計とズレてないとか、ズレていても対処がわかるとかは待つ必要ないからさ、作業続けていいよ」
- Later turn01a11f7a-198f-7852-8cfc-1312922a471d, message01a11f7a-1c51-7271-b1ff-c3fa639e3c29:
  「あなたの考え開発閉ループ作ってみて、それを私もみてから、実際にやってみようか」
- Latest read turn01a11f7b-b6c0-7ad2-9c1e-66f85947d02a, message01a11f7b-b701-7593-8476-a575d9863aad:
  「実装、検証、評価、改善。このループってことね」

The continuing rule is implement → verify → assess against accepted design → improve
or select the next unmet dependency. A checkpoint or reviewer approval alone never
requires owner confirmation. Clear corrections within accepted scope proceed with
reverification. Only a material goal/scope/acceptance change or genuinely new authority,
cost or noninferable owner judgment blocks its dependent work. No schedule restart,
unknown-call resume, access-refusal bypass, authentication, payment or publication.

The later request asks to see the proposed loop before trying it. The human lane
has shown that proposal and the owner has restated its four-step meaning. The agent's
suggestion of a separate approval gate is not an owner instruction. Root initially
overinterpreted the sequencing as requiring another explicit start authorization;
that interpretation is withdrawn. No new approval is inferred from the restatement:
the existing explicit continuation and existing AGENTS loop remain the authority.
The proposal introduces no scheduler, new execution route, scope or permission.
Proceed within that scope after technical prerequisites, without a new human wait.

Root's C069 turn termination was an incorrect continuation decision, not evidence of
a project-wide technical block. Existing AGENTS development-loop item10 already
required continuing the next authorized item. The corrective step is to record the
next concrete dependency and its actual dispatch/reason before concluding a checkpoint;
do not add a scheduler or new approval mechanism. See docs/DEFECTS.md.

Current independent work: native Astra analyzed transaction/ownership boundaries;
separate native Sol6.1 derived adversarial acceptance conditions, both read-only at
666506a. Both identify existing-work invalidation as required before execution use.
The proposed MEM01 scope is in docs/design/contracts-v5/MEM01-SCOPE.md. Official
CO0.4.5 Opus5.5 consultation taskb52e1ef96fbc482e88bb5c002b686a1b has actually
started on committedc3ace7a. No code/test change or MEM verification is yet claimed.
C069 source440-test evidence
remains historical to8db45fd; no unchanged suite rerun is needed for this record.

D038 technical adoption: actual Opus5.5 review recommends connecting queued-work
invalidation and public C14 events now, rather than more record-only preparation.
Adopt that recommendation with the exact shared API in MEM01-SCOPE.md. SOL owns TSK
source registration, transaction-bound public Result callbacks and integration;
Astra owns MEM record storage/read/stop/search, with separate Sol code review.
Use sanitized canonical replay identity and the existing imperfect sanitizer.
Opaque internal keys use canonical arrays to avoid separator collisions. Optional
C11 fields are omitted, and empty search means recent eligible records.

Reject the review's claim that a callback COMMIT after writes can be fully rolled
back. Collaborators are trusted host methods, not a sandbox; tests prove the actual
methods preserve transaction ownership and that ordinary failure rolls back. A
committing collaborator violates the contract and cannot receive a rollback claim.
Unsupported affected work states or missing source coverage fail the whole stop.
Running/notes/verification/real-service obligations remain unmet before activation.

CO taskb52e1ef96fbc482e88bb5c002b686a1b completed both exact Opus5.5 calls and emitted
the complete6885-byte REFINE response; its6000-byte document verifier failed. Preserve
failed/verified:false and the original note. SOL's design consultation/disposition
is distinct from CO document verification and future code/product verification.
No blind rerun, relaxed PASS or runtime edit is needed to use the observed advice.

D038/C070 execution outcome: source013bf52 connects actual MEM and TSK in isolated
SQLite, including queued invalidation, notification, reopen, two explicit lock
orders and post-write rollback. Astra's three author files remain byte-identical
to b35d508; SOL's TSK/consumer changes have separate native Sol6.1 APPROVE. Root
full471 PASS23.782s/exit0; related45 pass. No product/real-provider activation follows.
The current receipt supersedes the implementation note's author-time pending status.

The next dependency is actually dispatched, not just named: CO task04bc81e770ea479da9ed4b9b38df6628,
base5c427f0, TSK03/1 read-only durable C14 event delivery, SWE-2 High Free author
and separate Opus5.5 reviewer. Fresh official Devin3000.11.3 reports existing login
and exact swe-2-high Free; no new auth/cost/fallback. Native Astra analyzes the
independent TSK02 control/step boundary while this runs. The first corrected
implementation→verification→independent assessment→next-dispatch loop is observed;
ongoing success and complete PAL delivery are not inferred from one cycle.

D038 TSK02 technical disposition: Opus5.5 task0f5365d4c1ba438396ed08a16da2fab2
completed both calls and returned a full REFINE consultation. Its12000-byte document
verifier failed; keep that result and original response, no rerun just to shorten it.
Adopt the corrected connected report/lookup mock, durable lease/call lifecycle,
nonrefunding finite work+host budgets, immediate structured controls, source-stop
and latest-intent precedence described in TSK02-SCOPE.md. Required and optional
sources stay distinct. TSK is sole owner; RUN has no persistent competing state.
Full MOD raw output/replay and orphan recovery remain explicitly incomplete.

Clarify two limits in the advice: a committed admission is already owned/in-flight,
not proof of actual Python entry. A last pre-entry check cannot make physical entry
atomic with another connection's control; late results are fenced and slot retained.
An ended call with lost in-memory output is also not permission to recompute. The
mock wrapper, not a supplied stop boolean, observes cessation. Shared C13 Step shape
is preserved; lookup truncation is host metadata. Technical choices add no new owner
approval gate or external activation. SWE consultation precedes substantial code;
isolated Astra authors TSK, SOL integrates mock flow, separate Sol6.1 reviews.

TSK02 implementation consultation d3ad7fc12edc4abf89b66d3f46f93ba8 completed through
exact SWE-2 High Free; CO verified the bounded review artifact, not implementation.
Adopt its reservation lease/epoch/index binding, one-shot draining clear, process
invoker dedupe, step readiness, optional-source exclusions and budget headroom.
Astra separately found the same unadopted-output/yield gap and supplied strict host
query shapes. Ordinary yield cannot discard an unfinished returned call. Preserve
C13 owner-intent precedence: reject SWE's blanket refusal to release fenced output
on pause/draining, and its stronger old-epoch restriction. The owned lease and Goal/
revision permit freeing only occupancy, never stale result adoption. These rulings
are technical applications of the consulted scope and C13, not new product authority.

D038/C072 outcome: TSK02/RUN01 source ea2e8fa has author34, actual connected14 and
full531 PASS23.350s, independent native Sol6.1 APPROVE and exact CO Opus5.5 ALIGNED
(task6bd433a2799a49d2b27d5c5bc9708e7d). CO verified the review document only; the
reviewer ran no commands, and root binds command/source/hash/full evidence separately.
The callback-signature and interruption rollback defects have real consumer/fault
regressions. No Goal completion, persistent live use or recovery is inferred.

Adopt Opus F1: transient local unavailable must not terminally fail otherwise safe
work. Before admission, yield safely; after return, bounded same-input idempotent
local write retries, then retain occupancy if persistence remains unresolved. Never
retry the callable from a receipt or reset ambiguous ownership. Isolated Astra now
implements RUN01/2 from edfad06; separate Sol reviews it. This is a technical fix
within existing authorization, not an additional recurring owner checkpoint.

Adopt the next value direction: mock compose -> saved draft -> TSK attachment,
before VER/complete. Stage ART's immutable bytes/current-source readback first,
then connect artifact-kind dispatch/current-set binding with the RUN improvement;
do not mark the full compose path complete at the storage checkpoint. SWE task
dc4fbad81715497481bb66a5e02f8f23 is currently consulting the proposed storage scope.
ART keeps conservative actual-call dependency provenance, so model omission of a
source cannot evade reference stop. Completed-state history/source-stop must be
handled before complete becomes reachable. Orphan lease recovery and actual real
provider cessation remain separate requirements before activation.

D038 ART storage disposition: SWE scope consultation dc4fbad81715497481bb66a5e02f8f23
returned REFINE with five API/error/receipt/read/dead-end clarifications. Apply them
in ART01-SCOPE before dispatch. TSK authorizes the exact started compose action and
returns conservative actual-call record dependencies; ART owns immutable bytes and
historical receipts, not task state or completion. A compose step remains unbound
at this storage stage; do not describe it as the complete compose path. Reject the
advice's implication that failed work can simply be reclaimed: failed is terminal.
Next binding/RUN stage is explicitly required by the Opus milestone direction.


D038/C073: RUN01/2 and TSK save authorization at1be000a pass full543/23.484s, separate
Sol reviews APPROVE. Preserve first-hook review findings and red/green reproduction.
SWE binding consultation f4cba212 completed and advises REFINE. Adopt R1-R9 with the
explicit narrow compose-result source exception and trusted-callback rollback limit
in ART01-BINDING. TSK/RUN preparation against this fixed API is independent of the
unavailable ART implementation; component doubles do not count as connected proof.
ART task917989d447f94a09869f7b05e9870d3a s1-a1 timed out after900s, with unknown
outcome/process/quota and no selectable retry. No returned files, verifier or diff.
Preserve the pause; investigate read-only. Do not retry/resume/switch/cancel, directly
edit CO state, or start a duplicate ART implementation. The old unknown SWE/AGY calls
also remain preserved. Current stage is not a saved draft or completed Goal.


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


D038/C074 accepted: ART01-store/1 + ART01-bind/1 at source2e8dfcf pass full605
(23.880s, exit0), actual temporary-SQLite consumer18, ART owner20 and TSK owner52.
Separate Astra approves ART98b8f12; separate Sol approves TSK/RUNd6e0a72 and actual
consumer2e8dfcf. Exact CO Opus5.5 task7cd3d55711f04fee95e26435f00fe3a3 is ALIGNED,
no current-scope blocker. It ran no commands and saw the full-suite receipt only;
CO verified the note structure, while Root binds actual tests/source independently.
Source is actual immutable saved/attached drafts under mock execution, not VER,
complete, live service, full v5 activation or usefulness. Original unknown CO/AGY
calls remain untouched; native storage provenance is explicit.

Adopt Opus's two staged next dependencies: deterministic C09 storage first, without
completion; then C10 complete only together with completed-history source-stop and
terminal-safe lease handling. Under current monotonic epochs/append-only sets and
irreversible reference stop, VER can derive valid/invalidated from current WorkRef,
set and source gate without a second invalidation state engine. Unavailable owner
checks are unavailable, not proof of invalidation or success. Semantic and unbuilt
source-fetch checks remain unknown; no model claim or changed condition is MET.
SWE consultation will refine the exact same-TX APIs before substantial persistence
implementation. This is a technical continuation within D038, not an owner gate.


D038 VER01 technical adoption: CO SWE consultation e2477652c7ce43cbb9e20a91386fe2e1
completed with REFINE. Adopt its deterministic storage/current-status/strict-owner
boundaries in VER01-SCOPE, preserving existing authority error precedence rather
than its contradictory blanket queued-state test. Current source gate uncertainty
is an error, not a status. Structural artifact_saved does not verify arbitrary
description quality; semantic/source_fetched remain unknown. Split immutable
in-memory tests from the smaller SWE code-only module assignment; Root owns TSK
callback/actual connection and a separate reviewer assesses exact source. No C10,
new model path, state engine, new permission, or unknown-call retry is introduced.


D038 COMPLETE01 design consultation72fabf04 (exact CO Opus5.5) returned REFINE.
Root adopts R1-R8 in the proposed scope before SWE persistence consultation: exact
host epoch, strict owner comparisons/error precedence, ended-call predicate,
historical completed-source progress notices, no non-MET zero-cost yield loop,
no release after complete, forwarding-closure wiring and canonical host keys.
R4 needs no extra result field: MEM validates closed work_refs and ignores values;
retain only epoch-invalidated works in that list and use the completed work's
progress event for historical notice. New field would needlessly alter MEM.
This is design refinement only; implementation remains gated by the pending SWE
consultation and Stage A VER evidence. No new owner decision or external action.


D038 COMPLETE01 technical adoption: exact CO SWE-2 High consultationd8bd21a2
returned REFINE after Opus72fabf04. Adopt the frozen complete/terminal/history
transaction and error order plus host dispositions in COMPLETE01-SCOPE. TSK and
RUN may now implement independently by file ownership from this shared seam;
complete remains unaccepted until all three safety parts and actual connected
consumer tests pass. Default mock runner still requires explicit VER wiring.
No semantic model/verifyAction, general recovery, UI/provider activation, new
authority/cost or unknown-call retry. Root current VERfab7c77 is independently
approved; full regression and its milestone review are tracked separately.


D038/C075 accepted: sourcefab7c77 deterministic VER/current-status integration
passes650 host tests/45 focused and independent Sol rereview. Exact CO Opus5.5
task0e78d5da is ALIGNED, no current-scope blocker; its verified note is not a test
execution. A proven invalidation may short-circuit diagnosis of co-occurring
corruption; both remain non-valid. TSK context review provenance stays3f37f78
(Astra), with finalfab7c77 actual consumer covered by Sol/Root. Continue the already
dispatched COMPLETE01 TSK/RUN work, not a new owner approval gate. No product/UI,
semantic, recovery or unknown-call acceptance is implied.
