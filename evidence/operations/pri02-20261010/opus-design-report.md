# C081 / PRI02 design consultation report

**Constraints followed.** I used no tools, files, commands, tests or browsing. I read only the three input texts. This chat's model selection is Claude Opus 5.5 (High). The host's recorded route and model are the authoritative record. Your `/plan` flow normally writes a plan file, but you ruled out file operations, so the report is inline.

**Limits.** The PRI01 source and tests were not supplied. Every PASS or APPROVE figure in C081 (full 1058, Astra 53, fixed 39, binding 8, process 5, TSK, WIRE) is a host claim I have not checked. This report checks design intent and contract consistency only. It does not approve code.

---

## 1. Verdict on C081: **ALIGNED** (design level)

**Intended purpose (matches).** The slice delivers what PRI01 promised:
- ordinary sentence → same-Goal question/answer/change → saved draft → fresh structural check → readback;
- immediate control and record-stop with no model call.

Responsibilities stay separated:
- MEM owns bodies and TSK owns Goals, leases and budget.
- PRI owns only metadata, refs, hashes and the call ledger.
- The host owns routing, controls, stops and final acceptance.
- The model only proposes. It gets no Grant, completion or source-selection power.

**Value.** All five C15 calls are labelled as cooperative in-process mocks. The report claims no semantic, provider, usefulness or whole-product PASS. That is the correct boundary.

**Contract consistency.** I found no contradiction across these:
- submit identity and the crash gap;
- reads that never trigger a callback;
- the single compare-and-swap that grants one winning call;
- no SQLite transaction held across the callback;
- not_entered recorded only when the local ending is confirmed;
- uncertain dispatch is held and settled only by startup receipt lookup;
- the terminal row and C14 event commit atomically;
- C14 holds only a fixed host notice.

The four fixed issues are the right class of fault for this design: stop after consume, error leak, one-sided mismatch, and non-atomic settlement.

**F5 closure.** I judge Root's actual-exposure refinement to be sound. This is my own assessment, not a claim about the unreceived earlier report. It applies the right information-flow rule: a reply or effect can only depend on text the model actually saw. So the closure must include every exposed C11 body, and every dependency of every visible candidate even if uncited. A withheld candidate contributes no text, so it must not block unrelated new work. It stays sound only if all three of these hold:
- **(a)** Withheld-candidate metadata is produced by the host and never derived from the body. That includes titles and any summary.
- **(b)** The fingerprint includes `text_withheld`, so a withheld↔visible change makes the turn stale.
- **(c)** The parser rejects any withheld candidate as an answer or change target. Your "withheld selectors" and "withheld A + new B" cases cover this.

**Clarifications to record (not blockers for C081):**
- **N1.** Only create/change have an atomic `context_refs` source gate at dispatch. Model-proposed pause/resume/cancel, answer and memory-stop have only the best-effort recheck just before dispatch. That leaves a window where a source stopped after the callback returned can still drive, for example, an irreversible cancel. Either state this residual window explicitly, or pass the exposure closure to those owner calls if their public API already accepts it.
- **N2.** For the first profile, consider requiring `answer_record_ref` to equal the current turn's original record. This narrows the accepted wrong-but-listed risk at no cost to the proven flow, which already uses the "saved original user answer".

---

## 2. Recommended next contract: two stages, one adapter

PRI01's constructor and `recover_turns` qualify only `managed-inprocess-mock/1`. No existing public API gives a smaller integrated seam that fits. The order should be:

- **Stage T: separately frozen one-call transport proof.** A standalone runner outside PRI01 authority. Use the existing qualified Devin text host unchanged, through its supported external interface. No `co_v4` import into the PAL runtime and no `co_v4.task run`.
- **Stage N: trusted native C15 profile** (for example `managed-native-text/1`) inside PrimaryHost. Fixture-tested first, activated only after T.

Build the adapter once. Its request validation, ending taxonomy and evidence record should be the same in T and N, so T's evidence is about the component N will use.

### Invariants to freeze before code

**Binding**
- **B1. Request.** A canonical C15 request hash is persisted at admission. The adapter refuses any mismatch in call_id, reservation_id, role, output_kind or source_refs against the durable row. It sends only the system and user messages.
- **B2. Effective identity.** Route, model, effort, CLI version, binary digest and profile digest come from trusted effective selection and are checked against the frozen profile and the constructor's `model_id` **before reserve**. Any mismatch → never entered, with no charge consumed. If a pre-reserve access or tier check would itself call the provider over the network, it needs explicit separate allowance; otherwise record it as a gap.
- **B3. Correlation.** Bind the native attempt/session ID (hashed in public evidence). Completion must correlate to *this* attempt's original prompt.
- **B4. Process.** Bind the owned child handle plus PID, start time and parent durably **before entry**. A PID alone is not evidence, and PID reuse cannot revive it.
- **B5. Side evidence.** Use a separate PRI-owned record keyed by call_id with its own canonical hash, cross-bound to the call row. Add no fields to the C15 wire. One-sided corruption fails closed.

**Entry boundary (missing from the proposal; must be per CLI)**
- **E1.** Entry is the first moment prompt bytes may reach the provider. If the CLI takes the prompt in argv, spawn counts as entry. If it takes stdin or an ACP prompt, the first prompt write counts.
- **E2.** Persist an "entering" marker durably before that moment. Any failure before it → never entered. Any failure after it → unknown.

**Ending taxonomy**

| Ending | Condition | Adoptable? |
|---|---|---|
| `not_entered` | Failed before E1, confirmed | no; charge stays consumed if already reserved |
| `raised_before_entry` | Exception before E1 | no |
| `returned_bound` | Correlated completion **and** drained EOF **and** observed wait | yes, then PRI01-WIRE + source/fingerprint/owner gates |
| `returned_unbound` | Output arrived but any part of completion/EOF/wait missing | **no**; treated as unknown |
| `admitted_unknown` | Timeout, response loss, parent death, kill | no; held |

**Lifetime and unknown handling**
- **L1. Deadline.** Freeze 60 s per attempt, starting at entry. Then cancel via the qualified attempt if the profile defines it, then bounded local cleanup. Local reaping is recorded separately from remote cessation. The ending is always unknown.
- **L2. Output size.** Drain and discard output above the 8192-byte wire cap up to a hard ceiling. Over the cap → returned_bound with a failed parse. Over the ceiling → kill → unknown.
- **L3. Recovery split by phase.**
  - *Call phase* is provider-specific. Native unknown rows stay held, and mock `recover_turns` must refuse to settle them.
  - *Dispatch phase*, after a `returned_bound` ending, runs inside the PAL process. PRI01's qualified receipt-lookup recovery stays valid there.
- **L4. Held does not block.** Held native turns must not block readiness or other sessions, and calling `run_turn` again never re-infers. This is safe because the attempt has no external capabilities: PAL adopts output only through the owned return path. A provider that keeps running remotely costs quota but cannot cause a PAL effect. Settling the turn separately from the call (call stays unknown forever) can be frozen later.
- **L5. No recovery shortcuts.** No automatic retry, route switch, resume, refund or forced release. A user's new submit is a new turn with a new charge, never an automatic retry.

**Control, source and counter**
- **C1. Controls.** control and stop_reference stay on short `guard.operation`. The native wait holds only `guard.activity`, with no Primary mutex and no database transaction.
- **S1. Source.** The full PRI01 gates apply unchanged: recheck before entry, after return and before dispatch; terminal reply validation in the same transaction. A stop after entry suppresses the reply and any effect.
- **K1. Counter.** One reserve+consume = exactly one native attempt. A durable entered marker refuses any second send for the same call_id.
- **K2. CLI-internal retries.** Document whether the CLI retries internally. If that cannot be observed, record it as a gap and label the evidence "one CLI prompt", not "one provider request".
- **X1. Context.** Inventory the fresh workspace's ancestry, config, plugins, tools and skills (the runbook records an observed skill read). Use an allowlisted environment and no credentials in the request. Label output as possibly influenced by non-PAL native context; this is a provenance gap, not a source-stop gap.

---

## 3. Necessary fixes and acceptance cases

### Blockers before freezing Stage T
1. Entry boundary (E1/E2) for the exact Devin text host interface.
2. Ending taxonomy, including `returned_unbound`, and persistence order (B4 before E1).
3. Deadline and cleanup (L1), output ceiling (L2), CLI-retry statement (K2).
4. A fresh access/tier check immediately before entry, with no possible paid fallback. If the CLI could silently substitute another model or tier and the effective model is not in the result, record the gap and do not claim identity.
5. Evidence schema (B5) and minimized D045 publication: hashes, exact versions, bounded status only.
6. Attempt ledger: freeze the exact cases. Recommendation: attempt 1 is an ordinary new_work request over synthetic C01. Attempts 2–3 are independent single calls over synthetic question/answer and change candidates, each run only if the previous ending was `returned_bound`. Any other ending stops the sequence. Ceiling 3.

### Blockers before freezing Stage N (do not block T)
7. The adapter boundary for the PAL runtime: either a minimal PAL standard-library adapter (needs its own qualification), or an explicitly adopted external-process interface. If an adapter process sits in between, the process tree gets more levels and the cessation scope must say so.
8. Explicit profile identity in the constructor; recovery split by phase (L3); readiness with held rows (L4).

### Fixture acceptance cases (fake transport, labelled; before any real Stage-N call)
1. Failure before E1 → not_entered; after E1 → unknown.
2. Output but no EOF or wait → returned_unbound → no reply or effect.
3. Completion correlated to another attempt or session → unknown.
4. Timeout → cancel + reap recorded separately; held; no retry.
5. Parent SIGKILL during wait → restart: mock recovery refuses the row, readiness proceeds with it listed as held, and `run_turn` again makes no call.
6. Parent death during dispatch after a returned_bound ending → PRI01 receipt lookup commits or interrupts.
7. Cancel and stop_reference while the native wait is blocked.
8. Source stop during wait → reply and effect suppressed.
9. Identity, version or tier mismatch → never entered, no charge.
10. Over-cap, invalid UTF-8 or non-JSON output → returned_bound with failed parse, no fallback.
11. Second send for the same call_id refused.
12. One-sided corruption of side evidence → fail closed.
13. Environment allowlist; no credentials or paths in the request.
14. Full PRI01 regression is unchanged; the mock profile cannot be constructed with native configuration.

### Real-proof acceptance (Stage T)
Record outcomes (a) transport identity and finite calls, (b) bound completion/EOF/wait, and (c) PRI01-WIRE parse result separately. Any result is recorded. Outcomes (d), (e) and (f) belong to Stage N and the later usefulness judgment.

### Useful later (non-blocking)
N1/N2, turn/call settlement split, real multi-turn proof inside the product, Codex and Opus route qualification, a quota collector, and the authentic usefulness judgment.

### If the Devin Free route is unavailable
Record the real boundary and make no fallback. These can still proceed:
- the Stage-N host contract and fixture tests (1–14);
- the recovery phase split;
- the N1/N2 clarifications;
- the adapter-boundary decision (item 7);
- design of the analogous rule for real Expert calls (no MockRunner inheritance).

---

## 4. Readiness for the next preparation: **REFINE**

The direction is right and the scope is small. The proposal is missing a few precise items that change outcomes:
- the per-CLI entry boundary;
- `returned_unbound` as non-adoptable;
- preflight before reserve so a config failure does not burn a charge;
- the recovery split by phase;
- held rows not blocking readiness;
- the CLI-internal retry statement;
- the frozen case list and stop-on-unclean-ending rule.

Once Root folds blockers 1–6 into the Stage-T freeze, no further consultation is needed for T. Stage N needs items 7–8 frozen and fixture cases 1–14 green before any real integrated call.

This report is design evidence only. It is not approval, execution permission or a claim of success. Root reconciles it against the actual APIs and adopts the precise scope.

