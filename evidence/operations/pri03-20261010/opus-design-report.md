# PAL C083 / N2 / PRI03 Native Expert: design review

**Basis.** This review uses only the inline documents at a332c53 and the host observations you attributed. No tools, files, tests or provider calls were used. **[HOST]** marks your post-snapshot claims, which I have not verified. **[PROP]** marks my proposals for Root to freeze. This report creates no hashes, test results, effective-model evidence or execution-mode claims.

## 0. Verdicts

| Item | Verdict | One-line reason |
|---|---|---|
| C083 checkpoint (failed N1 plus corrected source) | **REFINE** | The correction is minimal and stays inside NATIVE-ACP01/1. Several ordering and receipt rules (R1–R5) need fixing before any entry. |
| N2 distinct corrected-candidate MAX1 | **ALIGNED, conditional** | It is the minimum useful next proof, but only under the stop, unknown and success rules in §2. |
| PRI03 Native Expert preparation | **REFINE** | The three TSK-owned operations and TSK raw retention are right. Four items must be frozen explicitly: prepared-phase recovery, the ended-call consumer matrix, binding Steps to stored bytes, and the order in which wrapper bytes get qualified. |
| Whole goal | **NOT_MET** | Unchanged. |

---

## 1. C083: what it contributes, its limits and the remaining proof

**Contribution to the product.** C083 turned an UNKNOWN real call into two specific, reproducible defects in the qualification path. Neither is a product-semantics defect:

- **Version boundary.** Public AcpTransport compares stripped `devin version` stdout exactly. The wrapper supplied `3000.11.3`, but the binary prints `devin 3000.11.3 (9c803229faa4)` (PRI02-N-SCOPE §C083; native-n-summary.json `diagnosis.verified_mechanism`).
- **Diagnostic gap.** The original OperationReply was not retained, so N1's unique cause cannot be determined after the fact (`original_unique_cause: NOT_PROVEN`).

The correction fits the frozen boundary:
- It keeps the closed pin schema.
- It adds one fixed transport-version constant, checked in `_fresh_pin` and passed to the original `DevinHostConfig.expected_version`.
- It retains the typed execute reply, a NeverStarted reference or null, the cached status and `protocol_diagnostic`/host observation, and the single stop outcome.
- It adds no status pumping and makes no CO edits.

**[HOST]** Candidate source is 808b05f3…, wrapper SHA256 ac1250b1…, Sol source review APPROVE on fixed35, and Root full1161 PASS in 30.939s with exit 0. These are source and fixture claims only.

**Evidence limits (must stay explicit):**
1. N1 stays UNKNOWN and consumed. `entry_observed:true` and `actual_prompt_submission:NOT_PROVEN` are both true at once. Devin `executing:1` fits either a session that really started or a pooled lease that was never released after a pre-spawn refusal. The current evidence cannot tell these apart, and C083 must not choose one.
- The `stop_status:error` result is not evidence that no session existed.
- The constructor fixtures (3 PASS, zero real calls) show the mechanism can happen. They do not show it happened in N1.
2. Full1155 and [HOST] full1161, the five owned-process fixtures, and the profile/qualification digests (`profile_is_successful_qualification:false`) are all local preparation evidence.
3. `model_requested: swe-2-high` with `effective_native_model_observed: null` means the model has not been observed.

**Design drift check.** No drift toward a second engine, CO edits or relaxed criteria was found. Three small drift risks need closing:
- **(a) Pinning to one build.** The full-build constant ties the envelope to a single build. That fails closed, which is correct. But a CLI auto-update between preflight and execute moves the refusal from the wrapper's own pre-entry check to the transport's post-entry check (see R1).
- **(b) Stale line references.** PRI03 cites line ranges at 190fcc4. The candidate is now 808b05f [HOST], so the freeze must re-base every citation.
- **(c) The 60-second whole-call deadline is unchanged.** That is correct for comparability, but N2 must not shift it silently.

**Minimum remaining proof for this checkpoint.** One distinct real invocation on the corrected candidate. Its own original receipt must show:
- State.COMPLETED, original end_turn cessation and a matching StopReply.CONFIRMED;
- effective model observed as exactly `swe-2-high`;
- no tools or permissions;
- correlation, EOF and owned-process wait;
- `NativeTextBuffer.finish` and `NativeReturned.validate` against the exact C15 request, profile and attempt;
- the ending persisted before return;
- its own lease released by CONFIRMED.

That is exactly N2 (§2).

**Refinements before N2 entry:**
- **R1.** Put the version check in preflight, before `on_enter`, so a wrong build produces the bridge's own pre-entry `NativeNeverEntered` and consumes zero provider allowance. Also add a fixture where the binary changes after preflight. The transport must then refuse after the marker, and the typed public NeverStarted must be preserved and shown releasing the lease. This is the path N1 could not demonstrate.
- **R2.** Write the diagnostic record after the single stop attempt is issued, never in front of it. Test that a failed diagnostic write still produces exactly one stop and stays UNKNOWN. The scope requires this; the freeze should name the fixture.
- **R3.** Bind the retained-observation schema as a closed key set: `attempt_ref`, `status`, `reason`, `never_started_ref|null`, `cached_status|null`, `protocol_diagnostic|unavailable`, `host_observation`, `stop_outcome`. Keep raw content local and publish hashes in the public summary.
- **R4.** Put capacity arithmetic in the freeze. Record the pre-entry Devin `executing`/`reserved` values (currently 1/0 [HOST]) and require `executing + reserved < 12`. If the N1 slot changes between freeze and entry, stop and re-freeze. A change is new information about N1 and must be recorded, not interpreted.
- **R5.** The N2 summary computes `profile_is_successful_qualification` only from the receipt checks in §2, never from digests.

---

## 2. N2: distinct corrected-candidate MAX1

**Verdict: ALIGNED, and the minimum useful step.**
- Nothing smaller proves the transport.
- Using a different synthetic request keeps it from being a retry of N1 or T.
- Running Native Expert real calls first would build on an unproven transport and double the cost of any rework.

N2 covers only the Primary-role wrapper bytes. It does not qualify later Expert-role wrapper bytes (§3, F9).

**Freeze contents (Root):**
- **Case.** A unique case ID, attempt root and empty owned workspace, all distinct from N1 and T paths.
- **Request.** A new synthetic request whose C15 `request_sha256` differs from N1's `native_request` receipt hash and T's request. Zero PAL effects and no business data.
- **Nonce [PROP].** Include a fresh random nonce in the prompt as a recorded content-correlation observation. Do not make it a pass/fail gate, because transport qualification must not depend on model compliance.
- **Bound identities.** Candidate commit, wrapper SHA, executable SHA, exact version stdout, runtime module hashes, pin, qualification envelope and profile. Recompute and compare all of them at preflight; do not copy them from this note.
- **Test evidence.** The full-suite result with its log hash at that exact commit, finished before entry. Plus the independent operator review hash.
- **Current checks.** Free catalog, auth metadata (metadata only), AGY overages OFF and no new auth or cost. Also the capacity guard (R4) and the canonical ledger file checks already in NATIVE-ACP01.
- **Admission.** Ordinary public gate, pool and ACP only. No touching N1, T or old CO calls.

**Stop and outcome rules:**

| Observed | Classification | Effects |
|---|---|---|
| Any guard mismatch before `on_enter` | `refused_pre_entry` | Zero provider calls. The case ends; another attempt needs a new freeze with the new guard values. |
| Exact public NeverStarted for this request, retained typed reply | `not_entered` (clean) | Allowance consumed, CO releases the lease, NOT qualified, no retry under this case. |
| COMPLETED, but any receipt check fails (wrong effective model, tools, missing CONFIRMED, buffer/validate mismatch) | `ended_not_qualified` | Release only if CONFIRMED. Retained. NOT qualified. |
| Anything else after entry: timeout, stop error, parent death, diagnostic loss | `unknown` | One supported stop, retained, slot held (Devin executing becomes 2), case consumed. |
| All success conditions in §1 hold, ending persisted, post-run Devin executing back to the pre-entry value | `qualified_transport` | Bounded connection prerequisite only. |

**Further rules:**
- **No N3 after a second UNKNOWN.** Two consecutive UNKNOWNs point to a systemic transport issue, so the next step is a design checkpoint rather than another actual call.
- **Not counted as success:** profile or qualification digest, requested model, nonce presence on its own, local fixtures, or a normal-looking dict.
- **What success still does not prove:** Expert semantic behavior, Expert-role wrapper bytes, native Primary UI adoption, usefulness, or absence of provider-internal retries.

---

## 3. Native Expert preparation: minimum freeze

The PRI03 analysis of the gap is correct:
- `end_call` takes only `{call_id,outcome}`.
- `get_call` has no request or output identity.
- `_recover_owned` turns orphan admitted calls into `interrupted` because a mock lock is held, which proves nothing for native calls.

I also agree with Root's preference: TSK owns raw output plus hash plus ending, instead of deferring raw retention. Without it, a lost `begin_step` response or a returned-without-Step call cannot be adopted honestly. C15 (`MODは生のモデル結果…保持し…同じcall_idの同入力は…保存結果を返す`) would also stay unmet.

**[PROP] freeze items:**

**F1. Native side table owned by TSK.** For example `v5_tsk_native`, written only by TSK. Columns: `call_id`, claim WorkRef with epoch, `lease_id`, index, `reservation_id`, `request_sha256` (computed by TSK from the canonical C15 request, never supplied by the caller), canonical `profile_json` and qualification hash, ordered supplied refs, `attempt_json|null`, phase (`prepared|entering|unknown|returned|not_entered`), `ending_json`, `ending_hash`, `output_text` (bounded UTF-8 ≤32768 bytes), `output_sha256`.
- For native rows, the call row's binding hash covers both sides. Mock rows stay exactly call-only.
- A native call with no side row, or a mock call with an extra one, makes every consumer return `unavailable` before any write.

**F2. Admission and entry.**
- `admit_native_call(request, *, c15_request, profile)` runs every existing `admit_call` check and additionally requires:
  - role `expert`, `output_kind=expert_action`;
  - `work_ref` equal to the claimed WorkRef;
  - C15 `call_id`/`reservation_id` equal to the admission fields;
  - C15 `source_refs` equal to the supplied refs, which must cover every exposed C12 body and eligible historical provenance.
- It consumes once and writes phase `prepared`.
- Equal replay returns a receipt only; a different body or profile conflicts.
- `provider.preflight()` runs before `reserve_budget`. Refusal means no reservation.
- `enter_native_call(call_id, attempt_ref)` is the provider's `on_enter`. It rechecks the lease, epoch, absence of control flags, and availability of required ⊆ supplied refs inside the transaction, then moves `prepared→entering` exactly once. A different attempt conflicts.

**F3. Ending.**
- `end_native_call(call_id, returned|never_entered)` validates `NativeReturned.validate(request_sha256=stored, profile=stored)` and that the stored attempt matches. It writes evidence, `ending_hash`, output text and `output_sha256` (cross-checked), the phase, and TSK status `returned` in one transaction.
- `NativeNeverEntered` is accepted from `prepared` or `entering`, settling as `not_entered`.
- `mark_native_unknown(call_id)` (from `entering`, idempotent) handles every other exception or timeout. It writes no ending and no output and does not refund.
- On a lost ending-write response, the same input may be retried locally a bounded number of times. Never retry the provider.

**F4. Source-gated original-call replay.** `get_native_output(call_id, *, lease_id, work_ref)` returns stored text only for that call, only under current authority, and only if all supplied refs are still usable. Otherwise it returns `denied` or `stale`, and the text is retained but never re-input. This is the C15 same-call replay.
- **Explicitly out of the first slice:** adopting into a new-epoch Step across a restart.
- Label the result "C15 native-Expert subset: saved result plus same-call replay. No MOD-wide ledger, no work-less native calls."

**F5. Steps bind to the stored bytes.** For native calls, `begin_step` re-parses the stored output with `parse_model_action` against the stored supplied refs and requires a canonical match with the runner's Action, or TSK parses it itself. A runner can then never adopt an in-memory text that differs from the persisted hash.
- A malformed Action is a known-ended adoption failure, with no repair inference.
- `operate` and model `verify` remain unavailable.

**F6. Every ended-call consumer goes through one TSK helper** that validates both sides and returns the call's profile kind. The consumers are:
- `begin_step`, `finish_step`, `authorize_artifact_save`, `ask`/`_ready_to_close`, `complete`, `release` (including CHANGE01 old-lease release);
- `get_call`, `get_execution_context.step_sources`, `_old_calls` and integrity readers, `invalidate_by_refs` draining, RECOVERY01/02, READ01 history and C14 event emission.

Fixed tests run one corruption matrix (side deleted or replaced, wrong attempt or model, bool index, partial ending, wrong-role reservation, extra mock side) against all of these consumers.

**F7. Historical facts are immutable.** Stored endings, evidence, completed Goals and prior receipts are never rewritten. Recovery writes new rows with profile-aware event kinds and text, for example `native_held` and `native_returned_unadopted`. Existing mock event identities and replay keys stay unchanged.

**F8. Native-aware recovery.** Native rows are excluded from `_recover_owned`.

| Phase at restart | Recovery action |
|---|---|
| `entering` / `unknown` | Held. Zero settlement writes (no epoch bump, no abandoned Step, no interrupted). `finish_startup` stays not-ready. |
| `returned` without a Step | Release the old lease with reason `native_returned_unadopted`. Output retained (F4), Goal requeued by C13 precedence, no automatic adoption. |
| Started compose with a validated ending | Use RECOVERY02 adoption after the native ending check. |
| `prepared` | **Scope conflict, freeze explicitly.** PRI02-N's "admitted/entering → unknown" wording would hold the global lease even though the committed `entering` marker is the trusted precondition for execute, so `prepared` proves execute never happened. I recommend closing it locally as `not_entered_local` (budget consumed, distinct from provider NeverStarted). The lost-commit-response case is already `entering` and therefore held. If Root keeps the conservative rule, it should note that it accepts global held occupancy for a known-safe crash window. |

**F9. Order of wrapper qualification.**
- Adding the `expert/expert_action + work_ref` pairing to `tools/native_devin_text_v5.py` changes the wrapper hash, which invalidates the envelope.
- Do not merge it into the N2 candidate.
- After N2, review the narrow diff. The first real Expert case (§5, G7) then serves as both that envelope's qualification and the connection proof, under the same receipt rules as §2 plus the TSK rules.

**F10. Explicit non-callable NativeExpertRunner.**
- Constructor: `NativeExpertRunner(connection, *, tasks, memory, artifacts, verifier, provider)`.
- It refuses any callable or a MockInvoker, and requires `provider.profile` to be a NativeProfile. A `fixture` profile is allowed only under labelled tests.
- MockRunner and MockInvoker refuse native providers. Their default profile, schema and existing tests are unchanged.
- The runner owns no SQL and no persistent state. It uses only public TSK/MEM/ART/VER APIs.
- Shared context and dispatch helpers are extracted once, with identical mock behavior and no subclass inheritance of the mock end, exception or recovery logic.

---

## 4. Expert UNKNOWN holds the global lease

**Agreed first-slice position:** keep the held state honest. Allow structured controls, stop_reference and read inspection through the existing non-execution paths. Do not claim native conversation continues.

**Scope conflicts to name, not hide:**
1. **SPEC "Conversation"** ("remains usable while an execution Attempt is running"). While an Expert call is UNKNOWN, model-led Primary is not ready, so conversation drops to recording, controls and reads only. This is a disclosed degraded mode and a release-relevant gap, not compliance.
2. **No permanent exit.** Unknown lease clearing is prohibited, so one native UNKNOWN can leave the whole assistant permanently not-ready. That is acceptable for the bounded qualification case but not for real use.
- **[PROP, later slice] PAL-side retirement.** A text-only, no-tools native call whose provider object died with the process can never reach TSK `returned`, so it can never produce PAL effects. A later Root technical freeze could therefore add `unknown→retired_unknown`. It would free PAL's lease and fail or block the Goal with a reason, while writing no ending, giving no refund and leaving the CO capacity slot untouched.
- This differs from clearing a CO lease and from retrying. It is still outside this slice, and so are separating Primary readiness and multi-Goal native execution.
3. **Control semantics while held.** Pause or cancel record the latest intent (`pause_requested` or cancelled with epoch+1) but do not release. Release resolves intent only after a real ending. Stop_reference fences any future adoption.

**Minimal truthful shapes [PROP]:**
- **Startup result:**
  ```
  {status:"held", ready:false,
   held:[{goal_id, revision, epoch, call_id, profile_id, phase:"entering"|"unknown",
          since_event_id, reason:"native_call_unknown"}],
   available:["control","stop_reference","read"]}
  ```
  No model body, error text or PID.
- **C14 event:** `kind:state`, a fixed sentence such as "Task paused: provider outcome unknown; controls and history remain available", `refs:[]`, and the work_ref.
- **Turn submit while held:** MEC C05 append still records the user's text, with no model. The turn ends `failed`, `error.code=unavailable`, `reason=expert_unknown_held`, with no fabricated reply. Per C01, nothing re-infers it later.
- **Control receipt:** the existing C10 shape, plus `reason:"awaiting_provider_ending"` when release is deferred.

---

## 5. First implementation: modules, owners and gates

Fixed shared contract first: PRI03-NATIVE-EXPERT/1 written by SOL, containing F1–F10, error codes, receipt and event shapes, the consumer list and the recovery table. An independent Sol writes the fixed tests before any source.

| # | Module (single writer) | Files | Main tests |
|---|---|---|---|
| M1 | TSK native owner (one author) | `pal/tasks_v5.py` (side table, admit/enter/end/mark_unknown/get_native_output, consumer helper, recovery, held startup result) | PRI03 cases 2–8, 10–12; F6 corruption matrix; two-connection admission; unchanged mock recovery |
| M2 | Helper extraction (one author, before M3) | `pal/mock_runner_v5.py` → shared helper module | Existing MockRunner/MockInvoker tests byte-unchanged and passing; PRI03 case 1 |
| M3 | NativeExpertRunner (Root/RUN) | new `pal/native_expert_runner_v5.py` | Non-callable refusal, preflight before reserve, Action parsed from stored bytes, no SQL |
| M4 | Expert wrapper role (Astra, after N2 result) | `tools/native_devin_text_v5.py` | Closed expert validator, Primary schema unchanged, new envelope hash |
| M5 | Held surface (SOL) | `pal/primary_host_v5.py` / UI read | Held turn/startup/event shapes; controls work while held |
| M6 | Whole-route verifier (Root) | new `tools/verify_native_expert_lifetime_v5.py` | See below |

**M6 whole route** uses real temporary MEM/TSK/ART/VER owners and a native provider explicitly labelled `fixture`:
- C03-approved Goal whose conditions are **only `artifact_saved`** (and structural source checks), so completion is reachable without model-driven verification. Semantic conditions would correctly return `unknown`.
- Flow: claim → native compose → ART attach → fresh structural VER → complete → READ01 readback.
- Plus ask→answer pending link, pause/cancel/stop at each barrier, and SIGKILL/reopen at `prepared`/`entering`/`returned`/started-compose.

**Gates:**
- **G0.** Contract plus fixed-test hashes frozen before source.
- **G1.** M1/M2 pass, and every pre-existing test file is unchanged.
- **G2.** M3/M6 fixture whole route passes.
- **G3.** Owned-process crash barriers pass.
- **G4.** Independent review of each final source by a context that did not write it.
- **G5.** Root full suite passes at the exact commit, log hash bound, before any dependent claim.
- **G6.** N2 result recorded (in parallel with G0–G4; it touches no source).
- **G7.** Root freezes the real Expert MAX1. Success requires all of:
  - §2 receipt rules;
  - TSK `returned` with stored output hash equal to the evidence hash;
  - Action parsed;
  - if `compose`: ART saved, fresh structural VER met, complete, READ01 readback.
  - A valid non-compose Action is a known-ended connection result, not success.
  - UNKNOWN is held per §4, with no retry.
- **G8.** One genuine whole-flow usefulness judgment by the human. This is separate and cannot be replaced by G7.

---

## 6. Remaining gap to the whole goal

1. **No real native transport proof yet.** N1 is UNKNOWN, and N2 has not run.
2. **No real Expert behavior.** No real compose, ask/answer, multi-step progress or model-led verification. Semantic VER and the `operate`/GitHub-read connector (C07/EXE) are unbuilt in v5.
3. **No exit from held UNKNOWN**, and conversation degrades while held (§4).
4. **No native Primary UI adoption.** The Stable-1 model-led revalidation and the P002 clarification real proof (N1-09) are unfinished.
5. **Memory recall** is still limited to recent30 records and first20 notes, with no cross-conversation improvement.
6. **One authentic whole-flow usefulness evaluation** and the final release audit are outstanding.

Only the human can supply the judgment in 6. Everything else above is routine technical work under the existing owner approval and needs no new approval gate.
