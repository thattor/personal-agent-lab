# Defects and prevention

## 2026-10-06 — correction stranded an in-flight slot
Failure: new deterministic test showed conversational correction disabled the old Record/notes but left its consuming Attempt running. Publication fencing worked, but the global slot could remain occupied.
Cause/evidence: `record(supersedes=...)` and `forget()` used separate invalidation paths; [regression test](../tests/test_controls_memory.py) failed with `running != queued` before fix.
Fix: both operations invoke the same host transactional source invalidation helper, fence current attempts, and requeue incidental context or wait on explicitly required sources.
Prevention: keep correction/reference-stop publication and slot-release checks in the full suite. Next boundary changes must exercise both paths with an in-flight Attempt. 20 tests green after fix, including 18 real SIGKILL crash boundary subcases. No runtime DB repaired.

## 2026-10-06 — startup checkout mismatch
Observation: supplied cwd had no HEAD/remote and lacked required new root documents. Initial lookup followed the old project-document pointer and a memory keyword search surfaced an old review entry, contrary to the explicit greenfield exclusion. That material was excluded from design/reuse input; no old implementation code was read/imported/migrated. This was a startup instruction error, not authorization to reuse the old project.
Correction/prevention: clone only the named GitHub repository into an independent checkout, read its ordered root documents and current master Issue. For this greenfield project, reject a checkout without the mandated root STATE/SPEC/DESIGN/ACCEPTANCE/DECISIONS before following other project pointers; skip memory queries that could retrieve excluded old PAL material. Preserved original workspace unchanged.

## 2026-10-06 — transitive memory reference stop
Review-driven finding: disabling a source alone still left an assistant reply derived from it eligible as later context. Fix: shared read boundary recursively verifies Record manifests and MemoryNote sources; raw derived records remain inspectable. Regression covers source→assistant→note propagation. This prevention is verified by the full 33-test suite.

## 2026-10-06 — native auth lost during environment scrubbing
Failure: initial live smoke failed with no receipts, preserving failed Goal and provider errors. Host auth status was logged-in, while the adapter CLI reported Not logged in.
Cause/evidence: read-only official auth status under minimal HOME/PATH environment reported loggedIn=false. Adding only USER/LOGNAME restored existing claude.ai Pro authentication. No Claude/Anthropic environment variables were present; no token extraction occurred. OS identity omission disrupted macOS keychain lookup.
Fix: allowlist USER/LOGNAME in both official auth preflight and native subprocess environment. API keys/tokens/config overrides stay excluded. Add deterministic env-isolation regression test. Capture sanitized failed stdout/stderr for targeted diagnosis only; vendor output does not become canonical success evidence.
Additional finding: live-smoke harness checked normal conversation created no Goal but initially did not reject a provider-unavailable response. Fixed to assert live responses are not fallback errors before continuing. Preserve the failed evidence as FAIL; do not edit its Goal. Next verification: repeat smoke in a separate synthetic DB after fresh official quota/cost check.

Test-harness follow-up: adding a durable reference-stop audit event made an assertion that counted all Records fail (3 vs 2), although both raw conversational Records were retained correctly. Corrected the assertion to count records without source_event_id and retain separate audit-vs-memory checks. No product behavior changed to make the test green.

## 2026-10-06 — plan-mode transcript in native draft text
Finding: host structural/hash checks passed, but readback of the first successful native draft revealed non-executed `<invoke Write>`/`ExitPlanMode` text around the requested draft. No tools were available; these were text, not authorized operations. The artifact was not a clean plain-text draft.
Cause: reused reviewer plan permission mode on the product text adapter, retaining a planning-oriented default system prompt.
Fix: product native adapter uses default permission mode with tools still empty, safe-mode/MCP-off unchanged, and explicit text-only system prompt. Product Executor requests draft text only. Live smoke now rejects pseudo invocation wrappers for its plain-text synthetic scenario; earlier candidate evidence remains partial. Reviewer plan-mode commands remain scoped to review. Next verification: clean native draft plus host receipts and no wrapper output, after fresh cost check.

## 2026-10-06 — natural control retry changed its resolved target
Finding: a retry of “forget that” could resolve a different latest source after the first request changed reference state, conflicting with the original idempotency key. Same issue could affect a retried natural cancel after another Goal arrived.
Cause: ingress hash included host-resolved routing fields instead of only the original client request.
Fix/prevention: Runtime captures original sanitized text and explicit client Goal/control fields before resolving natural intent; transactional ingress dedupes that immutable request and returns the original bound target/result on replay. Keep regression for repeated natural forget; explicit changed-payload key conflict tests remain. This is a dedupe bug fix within D-011/D-013, not a behavior reduction.

## Soak preflight: unbounded power history query
2026-10-06: First preflight failed visibly because full `pmset -g log` did not finish within 30 seconds. No canonical repair or soak clock started. Cause: historical system-log retrieval on every healthy measurement, although UTC/uptime showed no gap. Fix: retrieve bounded, filtered power evidence only when raw-clock comparison detects sleep/gap; unavailable evidence fails the run rather than silently excusing downtime. Next verification: fresh preflight must reach measurement and planned unfinished restart. Keep the failed run/log for inspection.

## Browser receipt translation
2026-10-06: Chrome automatically translated JSON field names/punctuation inside the session receipt, making copied text invalid JSON. This was observed through the browser DOM, not inferred from a screenshot. Added `translate="no"` and `notranslate` to the receipt, with HTTP assertion; browser recheck must show unchanged JSON. Ordinary UI text may still be translated. Synthetic browser sessions never count as human soak use.

## Monitor edit syntax caught by preflight
2026-10-06: A broad textual replacement while adding reconciliation misindented the second snapshot block. Preflight failed before starting any process/DB/soak. The library suite had passed because it did not import the entry script. Corrected the block; the attestation/atomic-export contract test now imports the actual monitor script, so this syntax gap is covered in the full suite. Continue to require the separate process preflight for lifecycle behavior.

## Follow-up registration argument
2026-10-06: Initial heartbeat registration was rejected before creation because destination/targetThreadId was omitted. Corrected to explicit current-thread destination/id; the app returned automationId pal-stable-0-soak-audit ACTIVE and its view card was read. No duplicate automation was created; scheduled execution remains unverified until an actual run. Next similar registration: provide explicit target identity.

## 2026-10-07 — recovered UI retained stale outage warning
Human screenshots showed unfinished work recovered and completed once, and the local artifact opened, but the UI still displayed State unavailable. Read-only host/restart/receipt evidence confirms healthy recovery; the warning was stale rather than canonical failure. Cause: refresh() set the warning in catch but never removed it after a successful parsed state response, including unchanged-state responses. Fix: clear only the exact state-fetch warning after successful JSON retrieval, preserving separate message-submission failures. Deterministic probe executes the actual refresh function with transport/HTTP/JSON failure then identical successful state, and verifies the unrelated submission warning survives. [Red evidence](../evidence/ui/recovery/before.txt), [green evidence](../evidence/ui/recovery/after.txt), [probe](../evidence/ui/recovery/check-refresh.cjs). Node is an existing local validation tool only, not a PAL/Python dependency; no install. Full Python suite remains stdlib.
Scope: obvious local UI bug fix under AGENTS routine-fix exemption; no design, criteria, state-machine or capability change, so no Opus/SWE gate triggered. No acceptance weakening. Original soak01 is INVALIDATED, stopped by owned monitor SIGTERM, retaining DB and fsync reset_required history. Previous human/restart proof is historical only and will not be carried into the fresh soak. Prevention: run this recovery probe after changes to refresh/error rendering; require successful unchanged data to clear fetch warnings. Next check: fresh baseline/run and first directly confirmed human receipt; no DB repair.

## 2026-10-07 — Native failure test used a worker hint as completion evidence
Scheduled follow-up full suite failed the new exhausted-provider visibility test: idle.wait returned but the inspected Goal was still running rather than failed. [Failed run](../evidence/tests/native-failure-wait-race-red.txt). Runtime._work_loop sets idle after an empty claim, while submit clears it after committing ingress; those operations are not a per-Goal completion barrier. The assertion treated the shared worker hint as proof that this specific Goal had already reached its terminal state. The exact failing thread interleaving was not instrumented; the observed intermediate state and source ordering establish the observer's unsupported assumption, not a canonical-state corruption claim.
Fix: this test waits up to the same2-second deadline for the actual persisted Goal to leave queued/running and still requires failed, no receipt, no mock fallback and the exact native invocation count. No production code, accepted behavior or criteria changed. [Full66 tests PASS](../evidence/tests/native-failure-wait-green.txt); [20 repetitions of all three provider-failure cases PASS](../evidence/tests/native-failure-wait-stress.txt). Prevention: new asynchronous assertions use authoritative Goal/receipt predicates or explicit barriers; idle alone is not a completion receipt. If a future product caller requires an idle synchronization contract, review and implement that separately rather than assuming this hint is authoritative. Owned live host/invariant check stayed healthy, no additional UI inputs/model calls or canonical repair.

## Response-style handoff edit observer — 2026-10-07
A UTF-8 stdin edit script failed parsing before any write (missing coding declaration), so the concurrently launched first regression run covered unchanged source. Corrected the script with an explicit UTF-8 coding header, verified the actual prompt diff, and reran the suite after the edit. Do not use a pre-edit green run as changed-source verification. Future multilingual stdin scripts must declare encoding before execution; source-diff confirmation precedes test evidence.

## Real response-style revalidation — 2026-10-07
First adjusted system prompt still yielded writing homework and falsely claimed PAL could not remember across conversations. Actual automated live outputs retained in evidence/functional/feedback-20261007; content-format checks alone missed these semantic failures, and result.json now explicitly marks FAIL. Cause: instruction did not explicitly exclude writing-first advice or distinguish host persistence from model session memory. Small clarification adds direct-question behavior and factual host-context explanation without new memory or canonical semantics. Prevention: revalidation must separately inspect these semantic constraints, not just names/sentence count; fresh live response and human review remain necessary.

## Final audit export/payload digest distinction — 2026-10-07
A controller audit initially compared the exported prompt text file hash with the stored runtime payload hash. The export adds one terminal newline; the actual runtime builder does not. The assertion failed before documentation updates. This is an observer-format mistake, not a provider/canonical defect. Exact payload digest now matches after excluding only the known export newline; audit records both export and payload hashes. Prevention: distinguish source payload from evidence serialization and check each command result before dependent recording/commit. No model rerun or canonical repair was needed.

## Development metadata batching / closed milestone assignment — 2026-10-07
Mistake: a multi-step GitHub metadata setup created root/future milestones/issues but stopped before writing its final receipt when CLI assignment of closed Issue1 to an already closed historical milestone failed. Cause of the CLI rejection is not established; read-only API confirms the milestone exists/closed and Issue1 is closed/unassigned. No product/canonical state corruption, issue reopen or duplicate creation occurred.
A proposed repeat was rejected by automatic approval review because it preceded read-only diagnosis. That rejected mutation was not bypassed. Controller read all actual existing IDs/states, resumed only unaffected ACTIVE/proposed hierarchy updates and represented the historical relationship by links; closed-milestone assignment remains unperformed.
Prevention: metadata batches must persist each created identity/readback before dependent operations; resume from actual IDs/state, never rerun creation blindly. For historical/closed association uncertainty, retain link-only tracking instead of manipulating completion state. Next condition: read existing metadata and scoped authority before any planned change, and save partial results before dependencies. This checkpoint re-read existing IDs and confirmed no duplicate future stages.
# Stable-1 classifier pre-release findings — 2026-10-07

Frozen baseline and independent failures are retained in evidence/reviews/stable1-classification. Initial broad substring grammar caused6/24 unwanted classifications and10/16 request recognition. First reviewed candidate lost a draft-action deferral prefix across clauses, creating a wrong Goal; question/comma splitting and narrow request morphology also missed requests/external explanation. Repairs scoped deferral before splitting, separated questions/sibling clauses, masked quoted payload, tied Japanese request verbs to imperative/polite suffixes, and persisted outcome/version atomically with existing ingress. Fixed40,20 edges,36 reviewer regressions and transaction/replay tests now have zero unwanted Goals; final unseen12 recall3/4 with one `草案` safe miss retained. Prevention: freeze before implementation, hash before opening reviewer cases, retain first failures, add regression cases, distinguish regression recall from new independent recall. No canonical rows were repaired. Known finite grammar limits remain subject to actual N1-07 evaluation.

One non-ASCII inline Python heredoc failed source decoding before any edit. Cause is only the reported input-byte decoding failure; terminal encoding origin not established. Retried the small fixture edit through structured apply_patch and verified parsed JSON and tests. Prefer structured patch for this fixture route; no global setting change.
# Issue4 synthetic parser regression — 2026-10-07

Exit source audit found a projection/application mismatch: the UI hid all choices
after any offered target's epoch changed, but the application checked only the
chosen target. Share one full-snapshot stale check for both paths; regression
claims Cedar then submits Birch and requires stale/no mutation.92 full tests PASS.
Cause: duplicated binding checks drifted while integrating the projection; next
selector changes must use/retest the shared predicate. No production UI exposure.

The first bounded-control parser interpreted `その下書き` as cue `そ` plus
possessive `の`, because the literal-cue regex alternative preceded the explicit
deictic alternative. Frozen matrix tests exposed five failures before deployment.
Correction: recognize the explicit deictic first. Prevention: retain both generic
deictic and named-target matrix cases and full-width correction-separator checks;
next parser changes must rerun them. Red and first-failure logs are retained in
evidence/reviews/stable1-targets/. Final91 tests PASS; no running host affected.

# Issue5 actual inferred-outcome finding — 2026-10-07

C1 real independent UI sample FAIL: source supplies organization of design discussion, but output additionally asserts smooth progress. Mechanistic cause observed: model generated an unsupported causal benefit despite existing contribution/achievement grounding instructions; exact backend cause is not established. Host correctly persisted and hash-verified the proposed text; host PASS is artifact integrity, not semantic correctness. Five-sample/six-call run stopped, all outputs retained, no replacement or canonical repair. Opus/SWE consultations pending for smallest grounding instruction correction. Prevention proposed: explicitly distinguish supplied actions from inferred results; reuse frozen absence probes and preserve failures/new-candidate boundaries. No claim correction implemented or verified yet.

Evidence-observer defect: initial Issue5 reconstruction serialized Store.context dictionary, but Runtime constructs WorkOrder.context as role/content tuple pairs. Independent Codex source audit caught mismatch. Original five misformatted files retained with `initial-format-error` suffix; formatter-exact pair-list reconstructions and hashes regenerated from immutable actual manifest/source rows, no new provider call or canonical write. Source/artifact/FAIL are unaffected. Prevention: reconstruct both boundary transformations (Store→WorkOrder→Provider), compare to literal actualformatter contract before claiming exact reconstructed prompt; no raw-wire equality claim. Administrative caps now derived from frozen host map rather than hand-total.

D026 repair implemented: no state/authority change, one additional grounding clause distinguishes stated actions from unsupported causal effects/benefits and permits own gratitude. Official Opus/SWE reviews completed before edit.92-test full regression PASS; no mirror-string test claims semantics. Actual repaired output remains unverified until new-candidate finite run2.


Corrective run2 finite verification: six fixed real outputs PASS without unsupported contributions/results; original FAIL retained, no universal guarantee. Observer-only assumptions (receipt goal_id rather than attempt_id join, English-only reply rather than bilingual status) raised errors before audit conclusions; corrected using actual schema/structured controlstatus and canonical event order. Prevention: inspect actual response schema and use ID joins/status rather than exact display strings. Non-ASCII heredoc decoding failed before writes; use structured patch for Japanese source/documents. These observer corrections caused no canonical repair, runtime change or new provider generation.


Human-handoff reception defect: the human window received direct responses after the prior terminal presentation readback, while controller later reported the old answer-wait state. No automatic return was configured, so successful handoff/presentation did not imply answer ingestion. Latest targeted thread pagination proves four direct response turns, including later correction; controller now stores source IDs/meaning and supersedes the old wait. Prevention: before describing a human blocker, read current window responses and page back through the presented judgment, applying subsequent clarifications. Distinguish pending human decision from received-feedback/controller reflection work; do not require answer repetition. No fabricated verdict or scope adoption.

## Resumed test environment observation — 2026-10-07

A documentation-only goal-resumption full test attempt reported eight HTTP setup errors, all PermissionError at socket.bind under restricted execution; remaining cases did not report failures. Original log: evidence/reviews/feedback-alignment/resumed-full.txt. Cause established by identical suite passing92/92 with explicitly authorized loopback execution, resumed-full-loopback.txt (7.916s), no source edits. This is an execution environment limitation, not evidence of a product defect. Next HTTP validation should use the authorized loopback test route rather than weakening tests or changing server bind behavior. No live providers or existing DBs involved.

## Official review capture deadline — 2026-10-07

SWE feasibility subprocess85010 reached the controller's300-second subprocess.run timeout, terminating the child with no captured response file. The wrapper did not catch TimeoutExpired or stream stdout, so partial response recoverability is unknown; do not infer vendor outage, semantic rejection, no persisted session, or successful consultation. Official devin list returned No session selected; no recovery is claimed. Record: evidence/reviews/feedback-alignment/swe-feasibility-completion.json. Next review wrapper must stream output and export the exact session with finally-completion metadata, so observation limits cannot erase diagnosis; narrow the source question only after this failure audit, fresh Free/auth proof and no paid fallback. No product changes were made.


## 2026-10-07 question-slice verification snapshot
The first full regression run loaded old schema-version assertions while the controller updated their source during that run. Three expected-version failures reported3 versus2; displayed traceback source reflected the edited file and could mislead diagnosis. No other failures, targeted rerun PASS. Cause: test-source edit overlapped a live runner. Prevention: finish all code/test edits before the final full run; record earlier output as diagnostic, never exact-candidate proof. questions-full-first.txt retained; questions-full-final.txt is the frozen-source rerun. Earlier sandbox full suite eight HTTP bind PermissionErrors were environment restrictions, not product failures; authorized loopback rerun retained separately. No canonical data repair.


## P002 template completion boundary — C018

Scripted provider on a81b930 returns complete with unresolved {{date}}/{{place}} for frozen T1. Host creates a draft receipt and pass outcome/completed Goal. Adopted P002 requires incomplete preview for unresolved factual placeholders. Root cause established at contract boundary: complete envelope syntax and UTF8/size/hash readback validate bytes, without explicit unresolved-template-token exclusion. Prompt instruction alone does not enforce the boundary. Repair pending official Opus/SWE reconciliation; preserve frozen case and negative evidence, no live run yet. Prevention target: regression covers complete proposals retaining explicit literal template tokens, verifies no draft/PASS/complete, alongside complete drafts without unresolved tokens. This is not a general semantic-completeness guarantee.

Observer corrections: initial Runtime.idle was already set and returned queued, so it is not a completion predicate; use canonical terminal-state polling. Second diagnostic used receipt.id as artifact ID, failing before saving; inspect the documented Store contract and use receipt.artifact_id. Final proof includes actual bytes with the correct ID. Initial inconclusive evidence is retained, no unsupported PASS derived.


## C019 outbox observer quiescence

Full151 run failed at RuntimeQuestionCrashTests whole-store replay equality, while all new boundary/gate tests passed. Runtime.idle covers the task lane only; submit returns an independent response Future that may append an assistant record between snapshots. Test did not await that reply or stop both lanes before testing outbox replay. Fix the observer by awaiting ACK response Future and closing Runtime after canonical question/receipt/completion assertions, then compare whole Store before/after repeated deliver. Keep the failed full output in gate-template-full-red.txt. No product state, acceptance weakening, or DB repair. Next replay audit must establish both-lane quiescence rather than infer it from task idle.

C018 repair verification: immutable eligible-only write/complete predicate with all admitted marker families and NFKC comparison, no stored-byte normalization or preview conversion. Five regression tests PASS including actual Runtime negative completion and retained noneligible literal-brace behavior; full152 PASS. Paraphrased blanks/noneligible semantic completeness remain unproven. C019 observer repair targeted actual three-SIGKILL test and full suite PASS after both-lane quiescence; original failing output retained.


## C020 evidence/gate metadata integration

First integrated journal/process tests failed before any fixture child started. Captured synthetic parent stderr identifies ValueError reserved metadata: GatedProvider used sequence for call ordering, while EvidenceJournal owns sequence for durable record ordering. Preserve live-evidence-integration-red.txt. Fix gate metadata to call_sequence; journal sequence stays protected. Next integration test must run actual gate events through the real journal before invoking any provider. Unit sinks that only append dictionaries did not detect this contract collision. No product/provider/auth change, no live generation or resampling.


## C021 observer and verification process
Initial observer confused Goal.state and outcome.check_status with question.status. Corrected against actual Store schema; the six-case fixture test now checks both terminal forms and prompt exclusion. Original missing-module test remains live-runner-red.txt. No product/DB repair. Next observer changes must map columns against source before execution. A second full suite was started before the first handle was terminal and used the same output filename. Both completed, but live-runner-full.txt is not final authoritative evidence. Retain it; poll each existing handle to terminal, then run once to a distinct live-runner-full-final.txt. Final164 tests PASS; no concurrent suite at final verification. Prevention: use unique output paths and wait for terminal before repeat.


C022 verification: source-frozen runner correctly rejected source drift during the first full167 run because the controller changed the operator entry module while that suite was live. Preserve live-operator-full-final.txt as failed evidence. Cause is verification sequencing, not a product defect; no weakening of pin checks. Subsequent full167 PASS15.806s in live-operator-full-green.txt with no source edits during run. Next source-freeze verification: finish all source edits, then run once, wait for the same handle to terminal before changing or repeating.


## C023 premature observation claim
T1 stale UI was observed, but the controller used a hyphenated artifact-status endpoint rather than the actual underscore endpoint. HTTP404 occurred; an independently sent case.accepted command prematurely claimed HTTP status/hash confirmation and advanced to P1. Original journal kept unchanged. After source route verification, readonly SQLite URI audit confirmed stopped source usable0 and unchanged retained bytes/receipt hash, recorded in live-c022/t1-stale-readback.json. This is DB proof, not retrospective HTTP proof. Next dependent evidence claims must wait for and inspect successful command result before accept/advance; separate observation failures from product failures. No model retry or canonical repair.

## C025 evidence-write cleanup failure
Injected startup config append raised before main's finally; the constructed runner was not closed. Injected terminal journal failure raised from gate.close_run before watchdog/host cleanup. These are controller failure paths, not observed live product failures. Two pre-fix failures are retained under evidence/reviews/feedback-alignment/operator-*-cleanup-red.txt. Fix: close the constructed runner on config failure; nested finally attempts watchdog, owned host, and journal cleanup independently. Prevention: test evidence-sink failure on lifecycle transitions rather than only successful logging. Full169 PASS15.399s; mocked collaborator assertions prove cleanup attempts, not actual disk exhaustion or successful OS resource release under arbitrary shutdown errors. Existing synthetic process-death tests remain distinct. Constructor partial-initialization and simultaneous multiple cleanup exceptions are not broadly proven by these tests. No historical journal rewrite/canonical repair.
