# C088 milestone and next frozen scopes: independent design review (Opus)

Single report step, 2026-10-10. This is a document-only design review of the supplied
frozen scopes, README and evidence. No source, tests, tools, provider or external
context were used. Code and test facts are attributed to Root receipts:
LEGACY01 `verification.json`, PRI02-DIAGNOSTIC `verification.json`,
`model-feasibility.md` and `native-n2-summary.json`. Items marked *Inference* are
reviewer reasoning, not observed facts. No source review is claimed and no hash was
computed. The prior C087 Opus planner proposal (plan_invalid) is not used as approval.
This review is a new C088 checkpoint, not a retry or resume of any earlier task.

Standing boundaries, unchanged by this review:

* Whole goal NOT_MET.
* N2 and every other UNKNOWN stay UNKNOWN.
* No N3, T2, real Expert, call or envelope is authorized.
* Old DBs, conversations, history and evidence are preserved.
* No CO, state or runtime edits. No new auth, cost, service or guarantee weakening.
* Local fixture or code approval is not native, model, semantic or human usefulness,
  and it is not whole-goal completion.
* Root owns adoption and integration.

## Cross-cutting findings

**X1 Baseline ancestry is not established.**

* Both new scopes freeze base `fff19cc`.
* LEGACY01 was frozen at `dbf0df1` and its source receipt is `0e5cdf0`.
* The coordinator base is `01ae956`.
* The supplied documents do not state whether `fff19cc` contains the integrated
  LEGACY01 deletion.
* Root receipts record 1210 cases at `69c6e22` (PRI02-DIAGNOSTIC) and 930 cases at the
  LEGACY01 source, with 280 deleted test methods. 1210 - 280 = 930.
* *Inference:* LEGACY01 was applied to the 1210-case tree.

Correction: Root states the ancestor relation in each adoption note. Root also states
the expected baseline for the phrase full current suite must pass, which is 930 plus
the new cases. If either scope base predates LEGACY01, rebase before authoring.

**X2 Integration order.** The two scopes have disjoint write sets. PRI02 appends to
`pal/native_text_v5.py` and changes the wrapper. UI01 adds new files only. Root should
still integrate sequentially and run the full suite after each integration. No scope
change is needed.

---

## C088

**Verdict: REFINE** (evidence-record correction only; no source or scope change)

**User value.** The milestone removes a startup path that launched the old engine.
README now honestly states mock default, HTTP/UI NOT_IMPLEMENTED and no replacement
web-server command. This is an interim regression: there is no runnable UI at all. It
follows the owner instruction that compatibility is not required. It is acceptable only
because UI01 is the next step. Deletion completes no product capability.

**Ownership and authority.** The split is minimal and separated:

* Astra owns deletion-only source.
* A separate Sol context owns the entry documents.
* Root owns shared records and integration.
* A separate Sol context performed source review (APPROVE per receipt).

No contract authority changed.

**Satisfied per Root receipt:**

* Exact deleted-path inventory, including the old pal modules, `pal/web`, the old live
  scripts, their exclusive tests and `tests/ui`.
* 280 deleted methods.
* Full suite: 930 cases, exit 0.
* Primary lifetime fixtures: 5, exit 0. Expert lifetime fixtures: 6, exit 0.
* Three mock demos, exit 0.
* real_provider_calls 0.
* Retained current-v5 test and fixture inventory.
* Unknowns, DB, conversations and evidence preserved.
* whole_goal NOT_MET.
* Fixtures with historical-looking names (`p002_real_ui_v1`, `stable1_*`) were retained.
  This is consistent with the rule that a name is not a deletion criterion.

**Material findings:**

* **C1** The receipt has no explicit field for acceptance bullet 1: current
  pal/scripts/tools import closure reaches no removed module and `pal.sanitize` is
  unchanged.
* **C1** The receipt also has no explicit field for bullet 3: `pal.server` is
  unavailable and no current instruction advertises it. These are only implied by
  `current_v5_source_unchanged`, the full pass and reviewer APPROVE.
* **C1** README (supplied) satisfies bullets 2 and 3 for itself. CODEX-PROMPT, AGENTS,
  SPEC and DESIGN were not supplied, so their state is unverified here.
* **C2** The scope requires current-test and fixture dependency proof for the deleted
  tests. The supplied record shows what was retained, not why each deleted file had no
  v5 dependency. The 930 count must not stand in for that proof, and the receipt
  correctly does not present it so.

**Smallest corrections.** Root adds a new C088 acceptance receipt or ACCEPTANCE entry.
The protected `verification.json` is left untouched. The entry cites or records:

1. The import-closure check command and result, including `pal.sanitize`.
2. An `import pal.server` failure plus a search over current mandatory docs and model
   inputs.
3. A pointer to the author or reviewer deleted-test dependency trace.

If these already exist in other Root receipts, citing them converts this verdict to
ALIGNED.

---

## PRI02-MODEL-DIAGNOSTIC

**Verdict: REFINE**

**User value.** Preparatory only.

* Fixture completion yields zero real Devin observations.
* It does not narrow the N2 cause. Per receipt, N2 has `effective_model` null,
  `effective_model_verified` false, `recognized_effective_model_advertisement_observed`
  false and `status` unknown.
* Value appears only after a separately frozen, finite actual case.
* The scope is proportionate: additive, local 0600, unqualified, bounded.

**Authority unchanged, per scope text:**

* `NativeTextBuffer.finish` and `NativeReturned.validate` are not relaxed.
* Original null/false fields are not rewritten. There is no synthesized ACK or verified
  field.
* No inherited session or prompt IDs.
* Callbacks are deliveries, not wire count or order.
* Stop happens before write.
* No TSK/ART/READ/replay entry.
* No RPC or set_config additions.
* The capture hash change invalidates the old envelope without new pin keys.
* The test list already includes the case where a null/false original model is still
  refused despite a matching hint.

**Ownership.** The sequence is minimal:

1. Independent Sol writes fixed tests and records RED first.
2. A pure-class author implements the class.
3. Astra implements the wrapper after the tests exist.
4. Reviewers differ from authors.
5. Root integrates.

Note: authorship through the CO SWE-2 High route is a coding route, not a PAL native
call. Its output is not model evidence and counts toward nothing for N2 or N3.
*Inference:* Root should confirm that using it does not consume, release or alter the
original held devin slot recorded in `post_capacity`.

**Material findings:**

* **P1 Legacy model-field blind spot.**
  * The feasibility receipt says installed CO recognizes legacy
    `models`/`currentModelId`/`availableModels` (`devin_selection.py:52-86`).
  * The collector projects only `configOptions`.
  * A relevant delivery that carries model data only in the legacy shape is retained as
    `options=[]` and `hint=null`.
  * That record cannot be told apart from no advertisement, which is exactly the
    ambiguity N2 left.
* **P2 Write point is unspecified for other entered endings.** The scope defines write
  points only for strict success and generic entered failure. It is silent for:
  * the own stop attempt raising;
  * BaseException after entry;
  * failures after `ending.json`.
  Authors and fixed tests could diverge on stop-before-write.
* **P3 Hash encoding is unspecified.** The `session_sha256` input encoding is not
  defined, so test expectations are not determinate.
* **P4 Hint null is ambiguous.** A null hint is not evidence of absence. Later reporting
  could misread hint counts as advertisement evidence.

**Smallest corrections (scope text plus fixed tests before RED freeze):**

1. **P1** Add one closed per-observation boolean, `legacy_model_fields_present`. It
   reports presence of a top-level `models` key only and copies no values. This makes
   the observation key set 10. The minimum alternative is an explicit limit sentence
   stating the blind spot. The reviewer recommends the boolean.
2. **P2** Add one sentence: the file is written only at the two named points; every
   other entered path writes no file; no write precedes completion of the stop attempt;
   the diagnostic never delays BaseException propagation. Add one test asserting no file
   on the post-entry BaseException path.
3. **P3** Define `session_sha256` as SHA-256 over the exact UTF-8 `sessionId` bytes, in
   lowercase hex64. State that it is a local correlation token, not binding proof.
4. **P4** State that the options array, not the hint, is the primary diagnostic data.
   Add a static test that no TSK/ART/READ/replay or validation path imports
   `NativeModelDiagnostic` or reads `model-observations.json`.

---

## UI01

**Verdict: REFINE**

**User value.** This is the highest near-term value. It restores a runnable local
surface after C088 and labels mock status and test replies honestly. The scope is
correctly limited: fresh loopback, a new disposable DB, mock-only, no native option or
fallback, existing public owners only, no SQL status edits, and no duplicate state
machine. Prototype routing is not natural-language capability.

**Ownership.** The split is minimal: a Native Sol author, independent tests and review,
and Root running the HTTP suite before a browser check. Independent test authorship is
qualified by the words as available (see U6).

**Material findings:**

* **U1 The shutdown hold conflicts with TemporaryDirectory.**
  * `TemporaryDirectory` has an implicit finalizer that runs on GC or interpreter exit.
    It can delete the DB while a held worker still runs. This contradicts never delete
    while worker runs.
  * Worker daemon status is also unspecified. Non-daemon threads can hang exit. Daemon
    threads die before the finalizer deletes data.
* **U2 A queue-full refusal can strand a turn.** Refusal after `submit` leaves a stored
  pending turn that nothing will run, because same-key replay cannot start it. The user
  sees pending forever.
* **U3 Progression triggers are unspecified.**
  * Only a new turn enqueues work.
  * The bound-answer route is not named (turn text or control).
  * The scope does not say whether a successful resume enqueues a progression.
  * The documented create, ask, answer, compose, VER/complete, readback example needs
    several progressions. *Inference:* owner MockRunner semantics were not supplied.
  * Without explicit triggers, answered or resumed work stalls, or the author invents a
    loop.
* **U4 The UI can be framed.** The Host, Origin and JSON-only boundary covers CSRF and
  rebinding, but not framing. The pause, cancel and source-stop controls can be
  clickjacked.
* **U5 The owner-refusal status code is unspecified.** The HTTP status for refused owner
  Results is not defined, so independent tests are not determinate.
* **U6 Independence is optional.** The words as available make independent tests
  optional.

**Smallest corrections:**

1. **U1** Use `mkdtemp` with explicit removal only after `close()` returns true. Declare
   workers daemon so interpreter exit cannot hang. When held, leave the data on disk.
   The demo prints a pathless hold notice and exits nonzero. Add a test that data exists
   after `close` returns false.
2. **U2** Reserve a queue slot before `PrimaryHost.submit` and refuse with a bounded 503
   Result before storing. Release the slot on replay, conflict or owner refusal.
3. **U3** Fix a closed trigger list: an accepted new turn, including a bound answer turn,
   and a successful resume control. Each runs at most one `run_turn`/`run_once`.
   Nothing else triggers a run. Document each example step with its trigger.
4. **U4** On every response send:
   * `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'`
   * `X-Content-Type-Options: nosniff`
   * `Cache-Control: no-store`
   * `Referrer-Policy: no-referrer`
   Add header assertions to the tests. These remain stdlib-only.
5. **U5** Use one mapping: owner-decided outcomes, including refusals, return 200 with
   the owner Result. Only transport and route errors return 4xx.
6. **U6** Make distinct-context independent tests mandatory before integration. If they
   are unavailable, the scope waits; it does not self-review.

---

## Summary

| Scope | Verdict | Blocking kind |
|---|---|---|
| C088 | REFINE | Root acceptance-record citations only |
| PRI02-MODEL-DIAGNOSTIC | REFINE | Scope text and fixed tests before RED freeze |
| UI01 | REFINE | Scope text before authoring |

None of these verdicts authorizes a call, qualification, envelope, N3, T2, real Expert,
CO/state/runtime change, or a whole-goal or usefulness claim.
