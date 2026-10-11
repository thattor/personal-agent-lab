# PRI02-N3-DIAGNOSTIC/1 -- independent Opus5.5 design review

Reviewer: Opus5.5. This is a design review only. The reviewer is distinct from the proposal author, the operator author and the source authors/reviewers.

Inputs are the six supplied documents/receipts at review base 96e135b4e95a1325cd2c1b5b99efe90c40510b53. The receipts (verification.json, native-n2-summary.json, model-feasibility.md) are treated as attributed Root facts, not as source review by this reviewer.

No source, operator, runtime, provider or command was inspected or executed. Every hash below is quoted from the supplied files; none is new.

This review authorizes no entry, freeze or interpretation. Root owns all three.

## Verdict: REFINE

The proposal is a sound shape for ONE distinct, PRIMARY-only, unqualified diagnostic MAX1. It stays inside the D050-D053 and PRI02-MODEL-DIAGNOSTIC/1 boundaries.

Root may freeze it after an independent exact-hash operator APPROVE, but only with corrections C1-C7 written into the freeze text. These corrections:

- weaken no criterion and require no source change;
- close ambiguities that would otherwise let a predictable strict refusal be misread;
- stop the diagnostic classification from being settled by interpretation after the fact.

No finding requires STOP.

## What the receipts establish (attributed Root facts)

**N2 outcome.** N2 ended `unknown` after exactly one entry.

- Transport fields were clean: execute accepted, last status completed, `end_turn`, stdout EOF validated, owned exit 0, tool events 0, pending permissions 0, own stop confirmed and matching, Devin capacity back to the held baseline.
- Only the model fields failed: `effective_model` null, `effective_model_verified` false, `model_binding` invocation_bound_only.
- The independent synthetic probe shows that NativeTextBuffer.finish rejects that cessation with a model mismatch.
- Uniqueness of cause and the full frames are NOT proven.

**Feasibility (C087).**

- Installed CO recognizes only the legacy fields models/currentModelId/availableModels, and processes configOptions for mode only.
- ACP permits a model selector in configOptions, but its initial exposure is optional.
- Whether Devin3000.11.3 actually delivers that selector at the public hooks is unconfirmed.

**PRI02-MODEL-DIAGNOSTIC/1 source.**

- Verdict APPROVE, with fixed20/native151.
- Capture hash 8990510b5b793f4f1a58bb60567cc02e3c72c5a1462ae0c516a4bf60caeb12ea and wrapper hash 31e7deb9cb078f7ae411e00dc90bc3c74bb58b954666a0fd3d778e385713b5e6 equal the proposal's pins.
- Root full run on 0d60b6f610010467605b6f6b4d98cef2286978e0: 969 PASS, exit0, log 854e1b784e379a1e8ce6272fa49a1d614f8731ca94127fabf52a5c08356ce7bf.
- New model qualification NOT_RUN. Old envelope INVALIDATED. Original UNKNOWNs UNCHANGED.

## Value versus repeating a known failure

The strict gates are deliberately unchanged, and so is CO's observer. Therefore N3's native outcome is predictably the same as N2's: a strict model refusal after entry, classified UNKNOWN. That part repeats a known failure and adds no qualification information.

The only genuinely new information is:

- whether Devin3000.11.3 delivers a model selector through configOptions at the existing observe/verify_session hooks;
- what the preprompt current value is;
- whether that value changes during the turn.

Fixtures, documentation and installed vocabulary cannot supply this (feasibility: "unconfirmed"). It directly decides the next design fork described below.

The exposure is bounded: Free catalog, existing auth, MAX1, effects0, and N2 restored its own capacity. The case is therefore justified ONLY as a diagnostic. The freeze must say so in advance, so the expected refusal is neither a surprise nor a reason to repeat.

## Binding findings

**F1 -- Expected outcome is not pre-declared.** The freeze must record, before entry:

- The expected native_outcome is UNKNOWN (strict model refusal after possible entry), unless the original strict path passes on its own.
- That expected UNKNOWN is not new transport evidence and is not retried.
- It triggers nothing beyond the existing rule of no further entry before reassessment.

**F2 -- A strict PASS has no defined meaning.** CO's existing observer might unexpectedly verify the model, so that NativeReturned.validate passes. The freeze must then:

- bind that transport_qualification to this exact new candidate envelope, wrapper and capture only;
- not extend it to the old envelope, N4, real Expert or any modern profile;
- record that the collector contributed nothing to the pass.

**F3 -- semantic_output after a strict refusal is implied but not stated.** If no valid NativeReturned exists, semantic_output is NOT_RUN. The unqualified-output text must never be parsed for JSON/nonce into any PASS or FAIL. Only its existence and local hash may be reported.

**F4 -- diagnostic_availability is not a closed classification.** Two points are open:

- precedence between INCOMPLETE and AVAILABLE when an overflowed record retained an earlier valid hint;
- the boundary between ABSENT and UNAVAILABLE.

Close it with C3.

**F5 -- "binding-matching" is not enumerated.** The record must match exactly:

- version PRI02-MODEL-DIAGNOSTIC/1 and authority unqualified;
- request_sha256 of the persisted synthetic request;
- profile_sha256 of the new candidate envelope's profile;
- attempt_ref equal to the new full run_id/job_id/attempt_id tuple;
- requested_model_id swe-2-high;
- exactly the nine closed keys and the frozen limits.

Any mismatch makes the record UNAVAILABLE. A mismatching record is never repaired or reinterpreted.

**F6 -- Guard ordering merges two phases.** "Before importing bridge modules" can only cover local checks, because version/auth/catalog/capacity readbacks need the public runtime. The freeze must state three phases:

- **Phase A (no bridge or runtime import):**
  - operator self-hash, source/test/full-log pins and candidate byte-identity;
  - exclusive new case root creation;
  - all N1/N2 original-file hashes.
- **Phase B (public runtime imported, before invoke):**
  - fresh exact full version, existing auth, unique swe-2-high Free metadata;
  - capacity limit12 and baseline Claude0/0 Devin1/0;
  - new envelope build;
  - exclusive fsynced persistence of the request, case, max1, effects0 and operator hash.
- **Phase C (on_enter):**
  - full attempt-tuple comparison;
  - capacity and baseline recheck.

Any failure in A, B or C before native execute is pre_entry_refused. The operator review must confirm that the phase B imports perform no state writes outside the existing public gate/pool path.

**F7 -- The pin list is partial.** The scope pins only the wrapper and capture. The freeze must enumerate every pin from the attributed receipts:

- the four PRI02-MODEL-DIAGNOSTIC/1 file hashes;
- Root full log 854e1b784e379a1e8ce6272fa49a1d614f8731ca94127fabf52a5c08356ce7bf for 0d60b6f;
- candidate commit 4f0e12c719dbc6f7e34dc784388ae4d619161cd4;
- the approved operator hash.

The claim that 4f0e12c is byte-identical to 0d60b6f in production/tests is a Root claim. The operator must check it mechanically: the same importable/test path set and per-file hashes, with any difference refused.

**F8 -- N2 guard coverage is narrower than the available evidence.** The N2 summary lists six original raw hashes: case, entry, result, execute, diagnostic and stop. Guard all six before and after the case, not only case/entry/result. Guard N1's equivalents from Root's local record as well.

**F9 -- Independence record.** verification.json attributes three roles for the model diagnostic to the same model (gpt-6.1-sol) in separate contexts: pure author, fixed-test owner and independent reviewer. PRI02-MODEL-DIAGNOSTIC/1, however, assigned the pure class to CO SWE-2 High.

Root should record this assignment deviation and its acceptance of context-level independence for an unqualified collector. It is not blocking, because the collector cannot qualify anything. It must never be cited as model-diverse review for any future authoritative profile.

**F10 -- Naming versus the prior disposition.** N2's disposition forbids "N3" entry before design reassessment. The freeze must state that:

- this review plus Root's freeze constitutes that reassessment for this diagnostic case only;
- PRI02-N3 qualification, N4 and real Expert remain unauthorized;
- after this case, any further provider entry -- including a second diagnostic -- requires a new evidence-based reassessment, whatever the outcome.

**F11 -- Publication granularity.** available_values may reveal account or catalog entitlements. Publish only the derived facts in C6. Keep the full projection, session SHA256s and raw records local under D045.

## Smallest corrections (freeze text only)

**C1.** Add an "Expected outcome" paragraph per F1 and F2.

**C2.** State that when no valid NativeReturned exists, semantic_output is NOT_RUN, and unqualified text is never semantically evaluated.

**C3.** Define diagnostic_availability, evaluated in this order:

1. **UNAVAILABLE:** the file is absent or unreadable; not local 0600; invalid JSON; not the closed nine-key shape; authority is not unqualified; or any F5 binding mismatch.
2. **INCOMPLETE:** status is incomplete. Report separately, as a boolean, whether any valid hint was retained before overflow.
3. **AVAILABLE:** status is complete and at least one observation has a non-null effective_model_hint.
4. **ABSENT:** status is complete with zero hints. ABSENT means "not delivered as a unique `model` select at the public hooks". It does not mean that model metadata was absent or that the model was wrong.

**C4.** Enumerate the F5 binding fields and the F7 pins in the freeze.

**C5.** Write the guard phases A/B/C per F6, and extend the original-file guards per F8.

**C6.** Restrict the public diagnostic facts to:

- observation counts per hook and per shape, and the malformed count;
- whether an option with id `model` was present, and its type;
- whether the requested ID occurred in available_values (boolean), plus the value count;
- whether the hint equals the requested ID at the first preprompt_snapshot and at the last retained observation (booleans);
- the number of hint changes;
- the IDs of any non-`model` options whose category is `model` (IDs only);
- whether session hashes match across observations (boolean).

No raw values are published beyond the public requested model ID.

**C7.** Add the F10 sentences and record the F9 deviation.

## Minimum safeguards and conditions for any freeze

1. Independent exact-hash operator APPROVE, by a reviewer distinct from the operator author, covering:
   - AST, imports and pins; phases A/B/C; exclusive case-root refusal;
   - invoke and on_enter maximum 1; disjoint attempts;
   - no retry, resume, cancel or release, and no pumping after return or raise;
   - result separation and preservation of the original error.

   Fixtures use a fake bridge/runtime only.
2. Distinct identity: new call, reservation, record and nonce; new run_id/attempt_id; the existing PRIMARY job_id literal; a permanent0700 case root that is never reused, removed or overwritten, and is consumed even on refusal.
3. Zero PAL effects: no DB, Goal, ART, TSK, READ or replay. model-observations never enters ending.json, native evidence or replay.
4. NativeTextBuffer.finish and NativeReturned.validate unchanged. No modern profile is adopted. A hint never alters the original null/false fields.
5. A fresh exact-version/auth/Free/capacity baseline in phase B and again at on_enter. Only the existing public gate/pool is used, with no ledger or lease mutation. The held1 stays untouched.
6. Wrapper keeps its 60s deadline, RPC 10s, text-only and tool/permission-free rules, and writes the diagnostic exactly once, after its own stop.
7. Post-invocation capacity readback and original-file recheck happen without pumping. Any difference is preserved and reported, never forced.
8. Three independent result fields are reported. All N1/N2/CO UNKNOWNs are preserved verbatim.
9. Whatever the outcome, no further provider entry happens before a new reassessment.

## Residual uncertainty (not reducible by this case)

- This is a single sample of one version, catalog and time. Free routing and quota may vary (provider_quota was unknown in N2). A quota failure after entry would be an indistinguishable UNKNOWN.
- A delivered `model` currentValue reports selection state. It does not prove the model that generated the turn, and carries no ACK or generation-level guarantee.
- The callback lacks the outer session ID and the prompt RPC ID, so session_sha256 equality is diagnostic, not binding. Callback counts and order are not wire frames, and duplicates are possible.
- ABSENT cannot distinguish four cases:
  - the server omitted the selector;
  - a different option ID was used;
  - delivery went through an unobserved path;
  - CO filtered the data before the hook.
- N2's exception cause remains unproven, and N3 does not retroactively explain it.
- That a recurring strict refusal has the same cause is expected but not proven: an operator exception or class alone establishes no cause.

## Next design decision after observations

Whatever the result, the next step is a design decision, not another call.

- **AVAILABLE, preprompt hint equals requested, no changes.** Decide whether to open a separate authoritative modern-model profile contract. It would need exact UID semantics, request/session/attempt binding, later-change rejection, validation through storage/history/recovery/replay, and independent review. The alternative is a CO observer compatibility request through CO's own governed lane. Neither is adopted by this case.
- **AVAILABLE with a differing or changing hint.** Treat it as possible fallback or selection drift. The strict refusal stands, and the drift is reassessed before any profile work.
- **ABSENT.** The public hooks cannot supply effective-model evidence for this transport. Present the guarantee choice to the existing human-design lane: keep strict, with Devin primary unqualifiable, or adopt an explicitly versioned weaker invocation-bound contract. Never lower current acceptance silently, and never repeat calls to "try again".
- **INCOMPLETE or UNAVAILABLE.** Diagnose locally from fixtures and the retained records. Any repeat requires a new reassessment.
- **Unexpected strict PASS.** Record it per F2. Expert pairing still needs its own fixed tests, source, review, full run, envelope and distinct freeze.

## Non-claims

This review:

- inspected or executed no source, operator, runtime or provider;
- verified no hash;
- authorizes no entry;
- changes no original outcome.

Transport qualification, model verification, semantic output, real UI usefulness and the whole PAL goal remain NOT_PROVEN or NOT_MET as recorded.
