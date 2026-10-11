# C091 — native checkpoint design reassessment (Opus 5.5, document review)

Reviewer: CO task-profile Opus 5.5, document-only design review of
`docs/design/contracts-v5/PRI02-N3-REASSESSMENT-REQUEST.md`. Inputs are the seven
supplied readable files only. Receipts (N3 summary, C089-C090 verification,
native-route feasibility note) are treated as attributed original/independent
facts. This is not source review, not a provider entry, and not native
qualification. This review's own successful Opus 5.5 task run is not evidence
for any PAL native profile. Root owns dispositions, integration and any later
freeze. This review authorizes no entry.

## Verdict: REFINE

The direction is sound. C091 was correctly consumed and correctly not
reinterpreted. The local first-overflow sidecar may proceed as local source work
once two wording gaps are closed (C1, C2 below). The binding constraint on
progress is not PAL observability. It is the absence of any CO-supported public
effective-model evidence seam. No further native diagnostic should be scheduled
until the decision-changing question in section 4 has a CO-owner answer.

## 1. What C091 established, and its limits

Attributed facts (native-n3-summary.json, freeze section "Actual C091"):

- The single allowance was consumed exactly once: invoke 1, entry 1, effects 0,
  exit 1 after 20.708 s, error type RuntimeError, native outcome UNKNOWN.
- Transport qualification is NOT_PROVEN. Qualified semantic output is NOT_RUN.
  No NativeReturned was saved.
- The original ending looks clean at the transport level: execute accepted,
  completed, end_turn, owned exit 0, stdout EOF validated, zero tool events,
  zero pending permissions, and a confirmed stop that matches the original
  cessation.
- The original effective model was null and unverified. Model binding is
  `invocation_bound_only`.
- The model diagnostic record was INCOMPLETE with 0 retained observations and
  0 hints.
- Unqualified text was saved (61 chunks, 160 bytes) and was not evaluated.
- Postchecks held: originals unchanged, inventory counts 4 and 6, absence
  preserved, own capacity restored. The Devin executing 1/reserved 0 count
  matches the pre-existing held baseline in the freeze, not a new hold.
- The independent Astra receipt audit matched 23/23 checks. It did not
  independently reconstruct the raw session or prompt hashes.

What C091 shows:

- The bounded single-entry machinery works end to end: entry, stop-before-write,
  zero effects and postchecks.
- The diagnostic file was written on a failure path without disturbing the
  original outcome, so noninterference held in practice.
- The unchanged strict gate refuses a null/false original model, as designed.

What C091 does not show:

- That model metadata was absent. `all_model_metadata_absent` is NOT_PROVEN.
- Which collector bound overflowed. `overflow_boundary` is NOT_PROVEN.
- The unique cause of the RuntimeError. A clean transport ending plus a
  null/false original model is consistent with strict-gate refusal. It is not
  proof of it, and missing frames must not be used to diagnose it.
- Anything about model identity, usefulness or transport qualification.

## 2. Local first-overflow sidecar (PRI02-MODEL-OVERFLOW/1)

The scope is well bounded:

- Existing limits, the nine-key snapshot, projections, strict ending,
  NativeReturned and replay are unchanged.
- The marker set is closed and finite, holds counts and reasons only, and
  carries no raw lengths (`observed_at_least` is limit+1).
- It is capped at 4096 bytes and refuses rather than truncates.
- It is best-effort and noninterfering, sits after the stop, and is omitted on
  pre-entry or NeverEntered.
- Fixed tests come before the author, and the reviewer is separate.

Its value is real but narrow. It is prospective only and cannot be applied to
C091. Its decision value is also capped by its own exclusions:

- (a) A marker showing that the model option exceeds a bound (for example
  value_count/select_options) cannot by itself lead to a retained hint. Bounds
  may not increase under this scope, so that would need a separate bound scope.
- (b) Even a retained valid hint stays unqualified and cannot satisfy the strict
  original-model gate.

Therefore no sidecar result can turn the next native case into anything other
than the same strict refusal. The feasibility note says the same: do not spend
another real call to obtain the same refusal.

The scope justifies itself as cheap observability hygiene, not as a path to
qualification. That is acceptable if stated explicitly (C1).

A spec-level constraint follows from the supplied scope text. This is an
inference about the documents, not a statement about the source or the failure:

- Under PRI02-MODEL-DIAGNOSTIC/1, overflow freezes the previous valid prefix.
- A count overflow at observations needs 32 retained observations, but C091
  retained 0.
- So if the C091 INCOMPLETE arose from a collector bound, it occurred on the
  first relevant delivery (observe or verify_session). The candidate reasons
  are option_count, value_count, token_length or record_bytes, never
  observation_count.
- This holds only if the implementation has no other path that sets
  incomplete. That needs Root/source-owner confirmation; it is not asserted
  here.

## 3. Native Claude route

Attributed source/metadata facts (feasibility note):

- CO native Claude host and adapter exact-pin 2.1.285.
- The installed binary is 2.1.291, and no 2.1.285 binary is present.
- Native Claude validates original model-bearing init/assistant/result frames
  internally.
- Its public cessation/collect_output does not expose those frames or an
  effective-model receipt.

The route is therefore unavailable to PAL as-is. The prohibitions in the note
are correct: no version-constant swap, no older binary fetch, no private-field
scraping and no Claude-as-Devin masquerade. This is a CO-owner dependency, not
PAL work.

## 4. Minimum corrections

- **C1 (overflow scope, wording):** State that sidecar completion is not
  decision-changing evidence and is not a basis for any new native entry,
  repeat diagnostic or N4. Record caps (a) and (b) from section 2 explicitly.
- **C2 (overflow scope, joint interpretation):** Define the joint reading of
  the two records:
  - original INCOMPLETE plus sidecar `not_observed` = incompleteness from a
    non-overflow path;
  - sidecar file absent = unknown;
  - `overflow` = first collector-bound refusal only.
  - None of these states means metadata is absent or identifies a cause.
  Add fixtures for a first-delivery (retained_index 0) refusal of each
  non-count reason, for both observe and verify_session.
- **C3 (sequencing):** Mark further native diagnostics on the Devin swe-2-high
  route and on native Claude as deferred pending the CO-owner answer in
  section 5. The sidecar may proceed only as local source work under its
  existing fixed-test and review plan.
- **C4 (receipt hygiene, optional):** In any later public summary, report
  whether model-overflow.json is present together with its status and reason,
  never site values beyond the closed enum, and keep raw-hash non-reconstruction
  explicit as in C091.

None of these corrections weakens a gate, adds a route, auth, cost or service,
or edits CO or state.

## 5. Decision-changing question and CO-owner request

Decision-changing question:

> Does any CO-supported native route (Devin swe-2-high, or Claude at a
> CO-supported version) expose, through a public, versioned interface, the
> original provider-confirmed effective model bound to the exact
> prompt/attempt that PAL's strict gate requires?

- If no: further native diagnostics cannot change the outcome. Native
  qualification work should halt at the design level until CO provides such a
  seam.
- If yes: design the PAL mapping and all consumers (Primary, Expert, TSK and
  replay) before any entry.

Proper CO-owner compatibility/evidence request, raised in CO's own scope, with
no PAL edits to CO:

1. **Supported version policy for native Claude:** will CO re-pin, or support a
   qualified range including 2.1.291, under its own qualification process?
2. **Public effective-model receipt:** a minimized, versioned receipt from the
   already-validated original model-bearing frames, bound to prompt/attempt
   identity. It should carry a model id and a validation boolean, with no raw
   frames.
3. **Devin binding:** whether the Devin route can ever supply an original
   effective model beyond `invocation_bound_only`, or is structurally
   invocation-bound. If it is structurally invocation-bound, PAL should record
   that the strict gate is unsatisfiable on that route.
4. **Compatibility commitment:** the seam's stability and version-change
   signalling, so PAL envelopes can pin it.

Until CO answers, the original UNKNOWNs, the held baseline and the consumed
C091 allowance stay as recorded. Real native UI, authentic usefulness, release
and the whole goal remain NOT_MET.
