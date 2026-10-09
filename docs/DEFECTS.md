# Defects and prevention

## 2026-10-09 — inline document verifier exceeded a CLI argument bound

SOL passed a multi-assert Python -c argument longer than CO's512 UTF-8 byte
per-argument limit (installed task/spec.py). CLI returned spec_invalid before
creating a task or model call; capacity stayed0. The orchestration helper then
tried to store the absent session ID, masking that immediate command result.

Preserve the preflight JSON. Move the same document checks to a saved PAL script
included as a protected read, keeping normal CLI argv below the bound. Print the
command result before storing a session ID, and store it only when present.
Next related invocation checks argv bounds and treats exit2 as a pre-task input
error only after confirming no task/attempt was created. CO/state/limits are unchanged.

## 2026-10-09 — milestone note lost source attribution while shortening

Task G's first note exceeded the declared500-token limit and blurred the full399
root suite with the122-test verifier subset. Independent Opus requested bounded
wording and accurate Mock/lambda description. The allowed repair fixed those, but
grouped the overlap count/time under verification.json, whereas those detailed
numbers come from three-way-proof.json. Re-review caught the missing source;
G ends failed/review_unresolved, verified=false. Source code has no blocking finding.

Preserve both reviews and the475-token candidate. H owns only the explicit source
line correction with its own independent review and document verifier. No code
implementation or unknown task is resent. Next assessment: leave margin below
the word limit, count markdown tokens locally and keep source attribution when
shortening. Verify the exact requested edit and report a failed CO task honestly;
do not convert successful tests into review approval. H verified the exact one-line
correction and independent review approved it; final476 tokens, source unchanged.
G's failed status and both reviews remain intact. This closure verifies the stated
document requirement, not a general improvement in model accuracy.

## 2026-10-09 — decoder test helper forwarded an assertion keyword

The first SWE EXE02-file/1 test run failed with TypeError: its assert_error helper
forwarded msg to decode_file via **kwargs, so the malformed Base64 cases did not
reach the decoder. The failure log and initial output are preserved. CO's one
allowed repair replaces that assertion keyword with subTest context; all17 invalid
Base64 cases remain and28 tests pass. Decoder source is unchanged by the repair.

Separate Opus review approves that version. SOL also adds the suggested public
case for an oversized declared size with invalid Base64, pinning validation order.
Next related change: inspect test-helper keyword forwarding and require the
invalid-input cases to run, rather than removing them to make the suite pass.
No production validation or acceptance was weakened. Evidence:
evidence/operations/co-update-045-batch2-20261009/task-d-initial-verify.log.

## 2026-10-09 — byte-buffer error retained a caller-supplied code

Independent Opus review of EXE02-bytes/1 found that PayloadLimitError compared
an arbitrary code using equality and retained that object when it equalled
"limit". SOL reproduced both a retained str subclass and an invoked hostile
comparison in error-code-before.log. Normal buffer calls passed constants, but
the public error constructor did not satisfy its fixed-value boundary.

Require an exact str before comparison and always store a module constant.
The public regression now rejects both caller objects without invoking their
comparison; final22 buffer tests PASS. Extend the existing strict-type check
to public bounded-error fields when wiring these helpers into a host; this is
a small code/test rule, not a new approval gate. A fresh milestone review checks
the corrected source. Copy/pickle and threaded buffer use remain outside this
single-executor preparation API. Evidence: co-update-045-batch2-20261009.

## 2026-10-09 — EXE02 request keys used equality instead of exact type

The SWE-generated request constructor compared set(arguments) to the required
keys. A str subclass equal to "repository" was accepted despite the intended
strict-key contract. Independent Opus review identified this gap; SOL reproduced
it with a failing public-API test (21 tests, one failure in strict-key-before.log).
The cause is set equality checking values without enforcing each key's type.

SOL now checks exact str key types before set comparison or field lookup, and
the same regression plus both component suites pass39 tests. Keep this check
when extending the C07 constructor; run the public strict-key rejection case and
the full regression before wiring it into a host. No service/grant/DB behavior
changed. Further independent review targets the corrected source. Evidence:
evidence/operations/co-update-045-20261009. The constructor remains unused by PAL.

The scoped Opus design also adds a63-bit positive issue-number boundary so decimal
formatting cannot raise CPython's giant-integer conversion exception. This local
preparation constraint is explicit in PARALLEL-SCOPE-1.md; it proves no issue exists
and does not grant a capability. The ART helper still checks size after encoding;
an early memory guard and direct-dataclass consistency are optional future consumer
concerns, not product acceptance or a reason for an extra approval loop.

## 2026-10-08 — C064 component readiness displaced the product-value checkpoint

The owner rejected the C063 conversation/draft-only trial as meaningful PAL usefulness,
while explicitly allowing necessary component tests. The implementation has a durable
local-draft Expert control lane but no external-information/task connector. The docs
already distinguish that limited milestone from the overall assistant. Nevertheless,
the release handoff asked for usefulness of that narrow screen without first resolving
its contribution to the owner's desired connected work. No overall release was actually
declared; the error was work selection and presentation, not a false historical release.

Evidence: [direct owner sources and code map](../evidence/operations/c064-owner-value-gap.json),
SPEC's Stable-1 local-only limit, runtime.py's local_draft capability and prior C061–063
release handoffs. Existing G001 checkpoints were insufficiently applied: their conclusions
did not redirect the next work away from component refinement toward integrated value.

Correction: record the evaluation as received/non-PASS, stop asking the owner to test
the same draft-only screen, and obtain one official Opus milestone direction review in
the design lane. Preserve component proofs; do not infer missing code from the complaint
or new connection permission from the desired outcome.

Prevention: at Issue entry/closure state design role, new practical value, why this work
is needed now and the remaining gap. At milestone boundaries or repeated/direction failures,
Opus checks those conclusions and the next work choice. Reuse existing records; no review
per wording change or extra micro-approval. Next verification: the C064 review must yield
a minimal evidence-bound connected-work proposal, and the next owner evaluation must show
that integrated task rather than a component test. This prevention is recorded; its later
product effectiveness is not yet proven.

Brief sequence: D021/P002 defined a local-draft milestone. D029 moved meaning/target
selection to the model. Repeated C038–C060 model-quality repairs and cohorts stayed within
that narrow task; D031 then explicitly stopped quality loops. C061–C063 nevertheless
presented the component-ready draft flow for owner usefulness. C064's direct negative
feedback showed the missing connected-work value and led to a pause/design rebuild.
These facts support a work-selection/acceptance-framing failure. The inference is that
local pass conditions displaced the project-level outcome; model incapability, an absent
Expert control component, or lack of owner interest in the actual goal are not established.

Latest correction: preserve this record, pause product work, and rebuild small milestones
around Expert instructions and actual work. Conversation/draft composition is delegated
to the model. P001v3 is still an unreviewed proposal, not proof that the prevention worked.
Opus milestone review has not completed: preparation failed before invocation and the
design chat was archived. Verify preparation files and successful delivery before claiming
review progress; never count a failed preparation as a consultation.

## 2026-10-08 — C063 source pin still called the prior product current

The first full suite after the duration change passed276/277 tests; one repository
freeze test still required the entire checkout to equal C059 producte851cae0. The
validator correctly rejected the changed native/server/UI files. This was a stale test
integration assumption, not a model failure or permission to rewrite the old freeze.
Preserved the failing log at evidence/reviews/two-hour-trial/full-red-freeze.txt and the
original C059 manifest bytes/hash. The test now pins that historical manifest, requires
its rejection against current source, validates the new C063 freeze and permits exactly
the three reviewed changed files. No cohort/oracle/provider run was changed or repeated.
Next product changes must record a new scoped source freeze before the full-suite source
pin check. This regression validates the historical/current distinction, not prose quality.

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

## C026 initial run record failure
Follow-up to C025 found MatrixRunner.__init__ starts watchdog/acquires journal before initial run.started append; append failure escapes before the caller obtains the runner. The test-first reproduction asserts zero stop calls (red), and inspection identifies the acquired resources. Initialize all close fields first, wrap watchdog start/initial append, and use the existing guaranteed cleanup path on exception. Green assertions verify actual fd closed and actual thread stopped, one scripted-provider stop, no generation, and preserved empty journal. Full170 PASS15.236s. Prevention: check both acquired-object startup and fully returned-object teardown for evidence-sink failure; constructor failures before these initialized resources remain outside this test. No false complete record or historical evidence repair.

## Invalid human-judgment escalation — 2026-10-07

Mistake: controller escalated form-only input handling and exact notice wording as
HR-INPUT-001, and the human window asked a sentence-level usefulness question. Cause
established from D027 review/proposal and authentic human-window turns: reviewer caution
was treated as owner authority, and implementation convenience displaced the natural
conversation goal. The old blocked observation also became stale after later answers.
Correction: D028 withdraws the question and wait; D029 restores LLM semantic intake.
Prevention: before escalation identify the noninferable fact and material consequence;
use latest authentic owner messages; reviewer advice is not a permission source. Keep
one end-to-end usefulness evaluation after a working candidate. Verification: existing
HRs reclassified and human window notified; effectiveness at future checkpoints remains
to be observed. Wrong-target code defect stays open until implementation/tests pass.


## C029 cached Primary replay after reference-stop

Independent source review found Runtime reused a completed Future on same-key replay after a source was forgotten. Store's guarded reply correctly withheld content, but cached Future bypassed it. Corrected: share Futures only for pending inference; terminal replay resolves a fresh source-guarded reply with no model/effect. Reproduction test verifies original Friday content disappears from the replay after explicit reference-stop and provider call count stays one. Raw audit rows remain under accepted reference-stop semantics. Next replay-boundary changes must test a source mutation after completion, not only before commit.

C029 test integration observations: template fixture incorrectly emitted Expert JSON for new PRIMARY calls; corrected fixture branches on DRAFT, preserving the same negative Expert assertion. A targeted module import exposed an existing discovery-only import; corrected to package import. Original targeted failure output retained. Full196 final suite passes with source fixed throughout. Historical live harness could not use DRAFT-only permits for new PRIMARY calls; protocol guard now refuses live setup before any auth/proof consumption, and old fixture tests explicitly seed Expert work. This is not new live qualification.


## 2026-10-07 C030 runtime-envelope test observer race

Observed: qualification-full-initial.txt,211 tests, one failure: after the first partial answer, the envelope test expected waiting_input but read running. Source evidence: Runtime's worker can set idle after an earlier claim found no work while a new wake is already queued; idle is not a per-Goal completion receipt. The test used that unsupported completion assumption. Product outcome failure was not established.

Correction: tests/test_runtime_envelope.py waits for the specific Goal to leave queued/running, then retains all original expected-state/question/receipt assertions. No product, acceptance or frozen Primary prompt change. Verification:20 repetitions of the previously failing two-answer case PASS; final211 full tests PASS18.056s. Previous failing log retained. Prevention applied to this module and the new qualification path: judge committed per-input/per-Goal outcomes, never an idle flag alone. Next related observer work must use the same evidence boundary; this does not prove every older idle-based test is race-free.

## 2026-10-07 C031 ambiguous semantic oracle and overstated controller diagnosis

First actual Primary run queued a draft for PHA03/1 while the frozen oracle expected
background-only. The controller described it as a future-only preference, although the
input had no future/defer/background-only signal. Independent corpus author conceded
implicit drafting is plausible; official Opus agreed65.429s. This establishes an oracle
ambiguity and reporting overstatement, not a conclusive model defect or exoneration.
Preserve original FAIL/raw files/DBs/hash chain. Correct the public and written diagnosis
by annotation, never edit the old judgment or resample it. No product/prompt change.

Prevention: semantic gold cases must be decidable from the offered context at that turn;
a planned future turn is not available evidence. Use independently frozen contrasts for
clear background, natural elliptical delegation, and same-Goal additional constraints.
Retain strict safety/grounding/target gates even on ambiguous cases. Next check verifies
old cases are excluded from the new cohort and untouched unexecuted cases stay byte-
equivalent in content; real semantic behavior remains to be measured. No new approval
question or explicit-command grammar was introduced.

C031 verification also exposed the same idle-event observer assumption in
`test_runtime.test_negative_capability_and_canonical_mutation_proposals`: an expected
failed Goal was observed as running. The first213-test output is preserved in
qualification-cohort-full.txt. Runtime.idle is a worker wake flag, not a per-Goal result;
startup claim-none/deliver can set it while a new admission wakes work. Reuse the C030
prevention: the four automatic-work tests in this module now await canonical state
leaving queued/running, then retain their exact completion/failure/receipt assertions.
No Runtime or provider change.20 repeated capability-negative tests passed; next full
suite verifies the corrected observer. Blocking-executor tests keep their explicit
start/release barriers. This correction is test evidence, not live model qualification.

## 2026-10-07 C032 controller promoted optional format concern into failure

PHA09/2 met its frozen local-only/recipient/content/routing observations. Controller
stopped over an added sent-materials premise and signature placeholder. Official Opus
review51.043s distinguishes possible minor premise drift from routine format choice;
no actual Expert artifact defect was observed. Stop exceeded frozen criteria. Preserve
all raw evidence/stop labels; annotate the reasoning error, no re-score or resample.
Do not add hypothetical artifact consequences or formatting preferences to a pass gate.
Next cases will be judged against exact precommitted observations; actual artifact
quality is checked in the separate required UI/Expert path. No prompt/product change.

## C034 browser observer scope and screenshot handling

Direct artifact navigation returned ERR_BLOCKED_BY_CLIENT, while following the actual
UI link and selecting only its exact known URL successfully displayed the HTTP200
artifact. Root cause of direct-navigation failure is unconfirmed; not a product failure
or an excuse to suppress browser protections. Broad tab inventory was rejected by
automatic approval review for unrelated private metadata. Use known owned URL binding,
not broad discovery, for subsequent artifact checks. Verified on both actual artifacts.
Alternate clipped capture produced distorted wrapping; retained alongside inspected
native full capture. Cause unconfirmed. Use native capture and inspect before publishing
visual evidence; do not claim the distorted image is observed product layout. No global
permission change, browser override or heavy new approval procedure introduced.

An inline metadata update failed source decoding before any edit; the following tool
batch nevertheless committed the already-green evidence without that intended update.
Correct the missing metadata in a subsequent commit, retain history, and stop dependent
mutations on any nonzero command result. Use explicit UTF-8 source encoding or structured
patches for non-ASCII text. This did not change product code or any runtime database.

## C035 observer timing and fixture schema

The actual UI cancel probe observed running, then the AX target disappeared before the
Stop click could be dispatched. Final canonical records contain resume/claim/completion
but no cancel input/event. Preserve NOT_VERIFIED; do not infer a cancellation product
defect or rerun until a favorable timing result. Independent review recommends a direct
Stop on an already-paused fixture for UI/control transport, with current deterministic
barriers proving in-flight fencing separately. That scoped zero-generation UI check
passed: only the chosen Goal cancelled, other Goal unchanged, zero attempts/receipts.

Initial transport-only fixture omitted the helper's required empty questions list;
setup failed before server start or any provider call. The partial DB is retained in
runtime/primary-ui-cancel-c035-03. Inspect the existing helper's schema before constructing
the replacement; the complete contract was fixed before new Store creation in04. No
SQL repair/reuse of the failed setup. This is an observer/setup mistake, not model proof.

An initial read-only database export encountered artifact BLOB values unsupported by
JSON. No file or canonical write occurred. The next export explicitly records UTF-8,
size and SHA256 for each BLOB, then independently matches HTTP bytes to host receipts.
Do not stringify byte objects or silently omit artifacts from evidence.

## C036 evidence accounting review

Independent review found two malformed new-run histories that the read-only verifier
would accept: a finished accepted/skipped sequence without any call evidence, and a
duplicate capture overwriting a previously judged action before a conditional skip.
The verifier checked aggregate counts and the latest capture rather than requiring
one ordered successful call/capture/judgment per accepted turn. No real run used the
new extension yet; this is a test-evidence verification defect, not product behavior.
Repair with focused malformed-history regressions and minimal lifecycle/duplicate
checks before actual model use. Preserve the initial226-test green log as intermediate.
Next verification must prove both histories are rejected and genuine conditional
execution/skip histories still verify; do not edit an old journal to make it conform.

Verified repair before live use: recognition-verifier-red.txt retains both failures,
recognition-verifier-green.txt32 focused PASS; recognition-full-final.txt228 full
PASS21.995s. Independent focused re-review clears both findings. Per-turn ordered
prompt/permit/start/proposal/return/capture/judgment binding and duplicate rejection
now enforce the pre-existing evidence contract. No old journal was edited.


## C037 observer API assumptions

The first fresh-auth precheck assumed supervised_text returned a CompletedProcess and
accessed .stdout; the helper actually returns a sanitized string. It failed after an
auth read but before proof creation or generation. Preserve precheck-error.json; inspect
the helper contract and parse its string directly. The corrected bounded read passed.
No fallback, model retry, credential storage or canonical mutation occurred.

New target-crash tests initially assumed inspect() exported selections. It does not;
Store.selections() is the documented code-level getter. Both failed test logs remain in
judgment-boundary/. Correct the observer, then verify the actual transaction/replay
invariants. Do not modify product exports merely to fit a guessed test projection.


C037 initial full-suite invocation lacked loopback bind permission:14 HTTP/runner setups
raised PermissionError at socket.bind, with no assertion failure. Preserve
recognition-suffix-full.txt as environment-limited. Same source under the approved
local-HTTP test execution scope passes234 tests in21.970s. Use that scope for later
full suites; do not edit product code, omit HTTP tests or call the restricted run green.


## C038 — optional personalization blocked a sufficient draft request

Observed English R02 and Japanese R10 on unchanged product1a14de9 both return a
recipient/contribution question without creating work; frozen generic-request oracles
require delegation. Original first attempts and stopped runs remain in judgment-boundary
recognition-run-r01-r08/ and recognition-run-r09-r16/. Two misses fail15-of-16.
Opus identifies the ambiguous threshold: optional details do materially change wording,
and the explicit-generic cue can read as necessary. This is a supported contract-wording
diagnosis, not proof of statistical model behavior from two translated cases.

Correction adopted before implementation: change only the Primary threshold to useful
general output vs essential unavailable purpose/user-owned choice; carry unspecified
values explicitly and preserve no-invention/nonrequest/authority rules. Existing native
Expert instructions remain unchanged. Prevent recurrence by measuring unseen clear-purpose
requests, genuinely missing choices and nonrequests fixed before edit, alongside fixed40
regression; no regex patch or changed expected result. Current25 host/runtime tests PASS;
actual revised-model behavior and affected artifacts remain NOT_RUN until bounded runs.


C038 qualification implementation review also found subset-only/empty product freeze
acceptance and validation after one-use proof consumption. Exact product-set comparison
and pre-proof/pre-owner-claim validation close these measurement holes; old manifests
remain unchanged. The first verifier update rejected the original pre-cohort journal
because it lacks even cohort metadata. Readback identified its original corpus/manifest
hashes; exact hash-bound legacy validation restored all six historical runs without
rewriting them. An independent code review also caught paired missing fields comparing
None == None in new bindings; required hash/identity presence and fixture binding now
reject these. Focused regressions and full suite must pass before any actual run.

A standalone py_compile command hit macOS's configured bytecode-cache write boundary
outside this checkout. AST parsing succeeded, and subsequent checks use python3 -B; no
source repair or broader cache permission is needed. This was tooling environment, not
a syntax/product failure.


## C039 — announced partial work bypassed the whole-request boundary

On product7c284733, N22 asked to draft and send. Primary narrowed this to a local draft,
producing one queued Goal, violating the frozen none/zero-Goal oracle. The actual stored
reply preserves spec's do-not-send wording but omits the explicit cannot-send explanation;
no rendered UI was audited. No worker or external task effect ran. R01–16 all recognized,
N01–21 passed; failed N22 and unexecuted N23/N24 remain preserved in clarification-run-*/.

Official Opus89.16s agrees the prompt's 'do not silently perform a partial compound request'
is ambiguous: an announced partial task can seem allowed. General drafting guidance may
reinforce it; the older product did not execute N22, so causal regression attribution is
unproven. Correction adopted in D029/C040: whole-request unavailable-action gate before
drafting; remove the contradictory permission, distinguish assistant-send from drafts the
user sends, and permit a later acceptance of a local-only offer. Primary only; host/native/
Expert remain unchanged. Prevent recurrence with the unchanged fixed40 plus a pre-edit
independent12 including over-blocking and separate-offer acceptance contrasts. Actual
revalidation remains pending. N14 re-asking after 'Not yet' stays a quality observation;
no new acceptance failure or unrelated fix is introduced from it.

Reviewer control: advice to require owner threshold approval or owner escalation after
one more failed candidate conflicts with D028. Keep technical diagnosis/review autonomous;
only real authority/noninferable-value/material-scope decisions go to the human window.

## C041 — record-only scope confused with local drafting scope

Raw N17 proposal on product60df1d0e creates a local draft from 'Record only: make a draft
invitation.' Host applies the proposed action; input text is intact. One queued Goal,
zero workers/artifacts/external task effects. Fixed run stopped; N18–24 and other current
cohorts NOT_RUN. Independent audit/archive in compound-run-n01-n24/; no canonical repair.

Official Opus86.848s and independent source audit identify missing current-authorization
precedence: accepted SPEC limits override preparation, but prompt emphasizes content-type
exclusions and useful-draft delegation without stating that recording/discussion/deferral
frames govern embedded task wording. Whether C040 caused the behavior remains unknown;
C039 had only one passing N17 sample. Native system has no demonstrated conflicting rule.

Correction adopted before edit: one general scope-precedence rule, distinguishing actual
current delegation from recorded/discussed commands, while local-draft-only/no-send and
later delegation remain supported. Separately authorized controls/memory use existing
forms; a control merely recorded is not authorization. Keep other product modules intact.
Prevention: unchanged fixed40 plus new pre-edit independent12 with over-blocking contrasts,
source freeze before disclosure, first-attempt failure retention. Later explicit-contract
failure requires capability/variance diagnosis rather than blind phrase accumulation.
Actual repair validation pending; deterministic suite is not semantic PASS.


## C042 verification — make the actual crash injection stop at its named boundary

The first valid targeted run failed the before-model marker assertion even though the
child exited by SIGKILL. The callback sent SIGKILL from the inference thread and returned
directly toward provider.complete. Signal delivery versus thread advancement is a
supported explanation, not a directly traced scheduler cause. No other provider path
exists for that fresh zero-Goal fixture. Preserve intent-limits-crash-race-red.txt.

Test-only correction: block the callback after os.kill while real process termination
occurs. Keep the subprocess timeout, actual -9 exit, both marker expectations and all
restart/interruption/no-replay/no-Goal assertions.30 repetitions with60 real kills PASS;
75 focused and249 full tests PASS. This improves injection precision without weakening
recovery acceptance or editing frozen product code. The next crash-boundary check must
verify that the injector itself cannot advance past the requested boundary.

An earlier command referenced nonexistent tests.test_primary_crash and is retained in
intent-limits-targeted-command-error.txt. Actual module discovery identified
tests.test_primary_runtime; only its subsequent successful run counts. Verify existing
module names before composing a targeted test command.


## C044 - missing details became an unsupported future promise

Actual UI ABS-A1 first attempt adds a promise to announce details later. The original
request and actual Primary spec contain no such commitment. Artifact/HTTP/receipt bytes
match, so this is semantic output failure, not persistence or transport corruption.
Official Opus and independent Astra apply the existing unsupported-timing rubric: FAIL.
The missing explicit Expert prohibition on invented commitments/status and omission
guidance is a plausible cause; model internal causality remains unproven.

Correct only the Expert instructions constant; preserve supplied and explicitly requested
creative content. No keyword filter, extra user question, criteria change or canonical
repair. Original evidence ui-c044-absence-failure/ is retained. Prevention verification:
new-candidate original absence cases plus two disclosed supplied/creative counterexamples,
one attempt each; current65 focused and249 full tests PASS but real semantics NOT_RUN.

The first Unicode fixture-save shell command failed with Python Non-UTF-8 SyntaxError
before creating the file; the controller mistakenly continued a separate prompt patch.
No live call happened. The fixture was then saved/validated via apply_patch, honestly
recorded as post-edit/pre-live disclosed regression, not pre-edit unseen evidence. Use
UTF-8 file tooling and verify successful dependent preparation before continuing.

## C045 - observation boundaries and unfinished-cancel timing

ABS-A1 read-only summary assumed a Goal specification field; actual specifications are
in revisions. Corrected observer after KeyError; no additional input or model call.
TARGET-B audit initially expected every Attempt unchanged after cancel, but the targeted
waiting Attempt must become fenced (Store._fence428-432, cancel561-563). Corrected exact
expected transition and verified unrelated rows unchanged. Next audit must derive
permitted target transitions from existing contracts before whole-table comparisons.
The independent audit also corrected an input-only manifest assumption: usable prior
context may accompany the original input. Original snapshots/DBs were not edited.

ABS-A2 artifact navigation reported ERR_BLOCKED_BY_CLIENT and displayed ChatGPT blocking.
Cause is not established; source-only inspection found no artifact-route change. No
product repair or semantic verdict follows this environment finding. Retain screenshot,
stop owned host, and leave NOT_VERIFIED without alternate content access.

RUNNING-CANCEL completed before the first post-input metadata observation. Like the
historical C035 timing miss, this cannot prove unfinished cancellation. No cancel was
submitted after completion, no artifact body inspected and no retry made. Next change
must be a reviewer-checked, predeclared test scheduling arrangement using an existing
fault seam, with unchanged real model data and host rules; it is not verified yet.


## C047 — verification harness failures preserved before actual execution

The sandboxed unchanged249-test baseline produced14 loopback PermissionError failures.
The authorized loopback-enabled run passed249; these were environment setup failures,
not assertion/product defects. Both logs retained. Subsequent missing-module RED,
reserved journal `scope` collision and unnormalized non-Git preflight error are retained.
Nest result payload beneath a nonreserved field and normalize preflight failures before
proof/provider work; do not weaken journal metadata validation.

One success test compared a retained rejection to a two-key dictionary even though the
host also supplies sequence metadata. Fix only the assertion projection while preserving
exact count, bound Attempt and reason. Child deadline verification initially used
communicate(), closing stdin and accidentally exercising EOF instead. Keep stdin open
until child termination and assert each exact run.closed reason (EOF, signal, deadline).
The consumed-proof fixture also mixed /var and canonical /private/var source paths;
resolve the disposable fixture root, then test the real proof marker. Original focused
failure remains; final19 PASS4.028s. These are test setup corrections, not product fixes.

Independent Astra identified a real harness publication race: after checking one snapshot,
watchdog closure could occur before a second unchecked snapshot was recorded as PASS.
Serialize release/result publication with closure; validate and record the same final
snapshot with fresh source/deadline/open checks. Deterministic close-wins and expiry-
during-final-snapshot regressions prove no PASS journal entry and zero artifacts after
the race. No actual provider run occurred with the faulty harness. Final full268 PASS
24.048s; script remains frozen during tests/live. Next related audit must check publication
ordering as well as host correctness, and verify child tests reached their claimed cause.

C047 actual observer: screenshot API returns raw JPEG bytes; a data-URL assumption raised
before the cancel input. Save returned bytes directly; exactly two planned UI inputs
still occurred. AX reports a receipt summary as a button but its DOM role lookup matched
none; fresh observed exact text opened it. No product changes or extra model calls.

More materially, initial controller closure audit used connect_ex!=0 and could mistake
sandbox EPERM for port closure. Independent auditor identified its own sandbox denial,
exposing the same limitation. Preserve controller-audit-initial.json, then verify from
authorized loopback context: exact ECONNREFUSED61 and ProcessLookupError for owned PID,
plus actual terminal exit0. Corrected report cites teardown-check.json. Next network
closure audit must record errno and treat permissions/timeouts as unknown, not closed.

## C049 — access refusal was recorded without completing safe diagnosis

C048 preserved the denied content correctly but its next action merely waited for an
allowed path, without an official settings/support investigation or concrete owner step.
This process gap is evidenced by c048-blocked-audit.json and superseded STATE text;
the original browser failure's technical cause remains unknown.

Following explicit owner-directed investigation, C049 inspected retained evidence and
unchanged source, verified official diagnostic/support guidance, and attempted supported
read-only settings/policy access. Those tools refused access; no workaround followed.
HR-ACCESS-003 now asks for exact visible Browse default/site-rule values without change,
and a private support draft is prepared. This is a real inaccessible environment fact,
not a routine technical choice shifted to the owner.

Next access incident: distinguish a prohibited content retry/bypass from independent
safe diagnosis; complete available documented diagnosis and give the exact remaining
observation or support route before describing only passive wait. Current correction is
verified as an actionable handoff, not as browser-access resolution or release PASS.

## C055 — generic drafting overrode the explicit question order

Actual first-attempt UI evidence on46bd418 shows Primary converted “ask me for these
three facts before using them” into “leave them blank.” Expert then generated a saved
artifact; the host correctly recorded bytes but cannot prove semantic task adherence.
Cause is the conflicting Primary generic-now / ask-only-if-unusable preference;
it needs an explicit ordering for a user-imposed ask-first requirement. Preserve the
failure and obtain the focused review before changing that prompt. Verification must
cover ask-first plus normal generic drafting, known context, requested placeholders
and creative permission so the repair does not restore unnecessary questions.
No keyword detection, host schema or new owner gate is justified by this defect.
The unsupported “soon” phrasing is retained in the failed artifact, not omitted from
quality assessment. Repair and new-candidate proof are still pending at this checkpoint.

Additional retained observation: C054 ABS-C2's Primary specification, also displayed
in its acceptance acknowledgement, uses “her help” for Mika although gender was not
provided. The final Japanese artifact contains no gender claim and still passes its
frozen artifact-only oracle. This does not qualify the acknowledgement/specification
as grounded. The original after.json already preserves the exact text. Track the
unsupported inference under the existing no-invented-personal-facts boundary; do not
hide it or expand the current ask-first repair into a new feature/rule system.

## C058 — unsupported future plan entered the Primary specification

R15 asks for an invitation with an undecided date. Actual Primary adds an instruction
to promise later contact, without source support. Generic useful drafting was correctly
chosen but the model supplied a sender commitment as conventional prose. Host source/
Goal checks cannot certify every semantic claim in spec. This is the C044 commitment
class one boundary earlier, not a need for lexical routing or owner approval. Preserve
first FAIL and review the smallest Primary grounding clarification before implementation;
verify explicit promises, fiction, unknown facts, generic drafts and ask-first contrasts.
The C054 unprovided gender observation remains part of the same grounding boundary.

Operator findings: an interactive CLI launched from a stdin heredoc closed immediately
with zero generations. Preserve it; use python -c/retained PTY and confirm a live session
ID before submitting the first input. The corrected launch reached actual cases, verifying
that correction. Its900s watchdog later closed after N23 capture but before judgment.
Do not extend/resume or mark the run complete. N23 is a separately cited post-run audit;
N24 is uncalled. Keep per-run wall bounds and avoid unrelated work during active windows.
A proposed suffix was not executed after the later R15 product failure.

C059 review preparation quoted a fragment of C054's negative instruction; Opus then
misread it as requiring impact. Actual full clause forbids results/benefits/impact.
Keep original packet, append the full clause/disposition and reject that unsupported
claim. Next reviewer briefing preserves complete negation/modality; current response
was checked against the source before adoption, with no extra review call.


D031/C060 disposition: the owner ended additional conversation-quality optimization.
C044/C054/C058 editable-prose shortcomings remain retained observations/old failures, but
are not release blockers under the new explicit policy. Repeated affected-corpus/wording
checks had become larger than the desired initial-use value. Prevention is the adopted
scope boundary: perform checks for actual missing functions, authority or data integrity;
do not reintroduce prose tests as safety tests. No automatic-learning fix is assumed.

## C062 — preview access report and misleading sandbox probe

Owner reported the Stable-1 preview would not open. Human-window plain sandbox curl
returned exit7/HTTP000, but development's permitted read observes the same PID65929
alive, health200 and DB integrity OK; actual Chrome page remains visible. Reproducing
plain sandbox curl gives the same exit7. The owner browser/device cause remains UNKNOWN.
The later proof expiry explains unavailable inference, not inability to load HTML.
Evidence: evidence/operations/c062-preview-unavailable.json.

Correction/prevention: report probe execution context, separate host liveness, actual
browser reachability and generation authorization; one sandbox refusal is not a server
downtime diagnosis. Before an explicitly requested rearm, verify the actual intended browser page rather
than relying only on an HTTP probe. Keep the existing pending device question, with no
duplicates or broader network exposure. C062 applied this by selecting the actual Chrome
PAL tab, then restarting once with fresh official proof on the same DB/URL. New visible
proof-valid/16remaining and health200 were verified; the owner's own reachability/use is
still unconfirmed. Do not turn that uncertainty into a claimed owner success.

C062 documentation correction before push: a broad substring replacement matched the
Goal paragraph instead of Exact next action and removed intervening STATE headings in
an unpushed commit. The diff review caught it; restored those sections byte-for-byte
from the previous commit and applied only within the anchored Exact next action block.
All section headings and operating-authority/phase/design/checkout blocks were compared
and retained before amending. Future small STATE edits must check their section bounds
and resulting heading list. No product source, runtime database or remote record changed.

## C065 — CO submission boundaries and reviewer assumptions

The coordinator manually transcribed a wrong full baseline SHA before inspecting the
completed `git rev-parse` result. CO rejected the input before any task/model call.
Correction: use the measured `a2d627238c72c61ae9b0ad7b9c7555bd84393dcb`; next submission
must resolve and compare the SHA before constructing the command. Do not infer a full
SHA from a short commit label. [Submission record](../evidence/operations/co-int00-20261009/submissions.json).

The first real task failed its verifier canary under the outer restricted sandbox,
with0 calls confirmed by CLI status. The approved host execution retained CO's own
isolation. Restricted full tests likewise failed localhost bind, while host full277
tests passed; an execution-context refusal is not product failure or permission to
remove containment. Check the actual failed boundary before replacing a run.

Opus returned a valid JSON plan whose design instructions were4435bytes, above CO's
4096-byte limit. No implementation had begun and the call was completed. The scoped
replacement explicitly limited each instruction to1000bytes and referenced the shared
scope rather than repeating it; actual819/815/840-byte steps were accepted. Keep this
bounded-plan rule for the next task. No output, journal, route or CO source was edited.

The design then incorrectly equated `raise ... from None` with removing raw exception
context. Python3.13 locally proved the context remains. The cause is confusing display
suppression with retained objects; preserve the original review, verify the generated
error path and require bounded errors without decoder context. Current implementation
and independent review must demonstrate the outcome before this is called fixed.

The actual SWE-2 High implementation call then hit the900-second deadline. CO reports
unknown result/process outcome and no selectable retry/switch. No code was received.
The root cause (provider delay, prompt/output size or other remote condition) remains
UNKNOWN; the83,547-byte prompt is an observation, not proof of the cause. Preserve
the paused report and do not claim the remote request stopped or bypass it with a
new same-work run. A supported recovery or confirmed outcome is required first.
If a later new unit is legitimately possible, reduce generated-output scope while
keeping the same shared contract and complete case coverage. This prevention is
proposed and has not been exercised or proved effective.

A follow-up multi-file documentation patch assumed ACCEPTANCE.md had a bare filename
heading. The atomic patch guard rejected it without changes. Read the actual heading
before applying the corrected patch; check section headings and diff bounds before
the next canonical-record edit. This does not require another review/approval gate.


## 2026-10-09 — retained trial freeze was assumed to be the current product

The first full regression after adding the two preparation modules ran316 tests
and failed one RepositoryFreezeTests case. The test passed the retained trial
freeze to the current-product validator as if it still covered every product file.
The validator correctly rejected the expanded file set; its security behavior is
unchanged. The test's old current-version assumption caused the error.

Retain the exact trial manifest and add its literal SHA256 assertion, read it as
historical evidence, preserve its comparisons with older freezes, and assert that
current-product validation now rejects it. No old proof is renewed or rescored.
The existing added/removed/symlink fail-closed tests remain intact. Next product
file-set change must keep historical hash assertions and demonstrate old-freeze
rejection rather than regenerating historical manifests or weakening validation.
The original full failure remains in full-unittest.log; rerun full regression on
the corrected source and obtain independent review of the exact test diff.


## 2026-10-09 — milestone note misassigned Operation to INT00

The new independent milestone design/note named Operation as an INT00 shared type,
although INT00 owns WorkRef/Ref/Action/Result and C07 Operation belongs to EXE01.
The note also exceeded its600-word output envelope. A separate CO review returned
request_changes on both plus a stale hash-check dependency statement. One bounded
repair corrected ownership, moved already-confirmed hashes to verification and
reduced the note to486 whitespace words; re-review approved the exact new version.

Cause: the note generalized across C07 and INT00 instead of checking the scoped
owner/type list, and its author claimed length without the stated counting rule.
Preserve original design/initial findings and final note. Next milestone handoff
must use the current scope's actual owner/type list and mechanically check any
explicit output bound. This correction changes no product code or permission.
Evidence: co-update-045-20261009/task-c-initial-review.json and milestone-review.md.
## 2026-10-09 — incomplete diagnosis of an unknown Native call

The previous continuation stopped at the CO unknown report without correlating the
Native PID, per-run logs and persisted session. That left the next technical action
too vague. This is an investigation gap, not evidence that Devin was still running.
The targeted follow-up identified unique-cobweb, exact prompt bytes, input-only
session nodes, absent local PIDs/groups and unchanged task files. No old state was
rewritten and no vendor timeout cause was invented. Next unknown call: distinguish
process, model output, file effects and controller record; use existing logs/session
metadata and report the specific missing recovery condition before deferring.
The read-only session listing needed an approved host scope because its CLI creates
a log outside sandbox roots. No trust override, resend or public support submission
was used. See co-int00-20261009/diagnosis.json for the actual bounds.

## C068 — deadline shutdown race and misleading command wrapper

The first full419 regression failed the existing CancelProbe deadline subcase:
serve_operator observed an expired deadline before the watchdog marked it closed,
then treated the ordinary stop as an operator failure. An unchanged rerun passed;
that did not resolve the race. New deterministic tests reproduced expiration before
watchdog close and close between loop checks (two errors); general rejection stayed
an error. Source inspection confirms the time/check interleaving, with no INT00
runtime import or source dependency. Preserve both full419 outcomes.

Correction: a private RunRejected subtype identifies only closed/expired checks.
serve_operator handles that stop with idempotent close_run; the existing first
reason, cleanup and no-result-application behavior remain. Other rejections still
fail. The related22 cases and independent Sol6.1 review passed; full422 passed after
integration. This does not requalify historical live source freezes or restart a
trial. Next shutdown change must rerun the deterministic interleavings and preserve
ordinary pin/rejection errors, zero saved effects and lock release.

The first shell wrapper also used zsh's read-only `status` variable and exited1,
hiding the subprocess exit status. Before reading the retained log, SOL's retry
justification incorrectly called the tests successful. The log actually had one
failure; no acceptance row was promoted from that claim. Subsequent verification
runs use the test command directly, inspect its exit code and final log, and bind
both to the source commit. Do not infer test success from completion or a wrapper
error. Evidence: co-int00-20261009/full-initial-wrapper-error.log,
full-pre-fix-retry.log, deadline-before.log, deadline-after.log,
full-integrated.log and sol-independent-review.md.

## C068 — oversized planner instructions in a design-assessment task

CO taskad95757c7dd847fcbcabfd3903bec53c completed one exact Opus5.5 planner call,
then rejected its5795-byte instructions against the installed4096-byte field limit.
No assessment worker, verifier or file write ran. The Native admission records a
confirmed stop; this known terminal plan failure is distinct from the old unknown
SWE call. Preserve plan_invalid and verified=false. The corrected bounded task
asks the planner for<=1200-byte instructions referring to the goal, without drafting
or predetermining the assessment. Future assessment requests keep plan instructions
brief; no runtime/state edit or limit bypass. Evidence: milestone-plan-failure.json.
