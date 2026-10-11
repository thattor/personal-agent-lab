# PAL INT00/1 milestone design-alignment review

Reviewer: independent Opus 5.5 design-alignment context. Subject: PAL-v5-common-wire / INT00/1, authored by native gpt-6-astra and reviewed by a fresh gpt-6.1-sol context. Review base: 9390c38a101ff6f71a39b5cd6cc4bb38fc2fd05c. I read only the seven declared inputs. I ran no tests, commands or hash checks. Every execution result below is as recorded by SOL. Root SOL owns adoption and integration.

Verdict: ALIGNED

I found no concrete design blocker for the pure wire milestone:

- Its section-3 values and C12 Action shapes match PAL-contracts-v5.
- It stays inside the scoped pure-parser responsibility.
- Each U1-U10 finding has explicit handling or a named downstream owner.

This is a design-alignment verdict only. It is not product acceptance, v5 adoption, CO-task completion, or evidence that any service works.

Contribution:

- Delegated value: the milestone delivers a shared, stdlib-only, immutable wire layer (pal/contracts_v5.py) and a 119-case synthetic fixture that downstream producers and consumers can reuse. It prevents each module from reinterpreting section 3/C12 on its own. Covered rules: exact keys, strict types, closed enums, Draft/formal Condition separation, zero as an exhausted (not unlimited) budget, and a single flat Action `kind`. This is enabling work, not user-facing value.
- Responsibility separation: the module mints no IDs, holds no state, performs no I/O and claims no authority (module docstring; parse_model_* docstrings). The model-boundary parsers enforce only exact (kind,id) Ref membership. The host shape parsers do not. This matches C12 (known Ref selection allowed, no new formal IDs) and leaves TSK/EXE/VER duties with their owners. Authorship (Astra), code review (Sol6.1, sol-independent-review.md) and this design review were done in separate contexts.
- Section 3 / C12 consistency: each of the following corresponds to the contract text:
  - WorkRef: nonempty goal_id, revision>=1, epoch>=0.
  - Six Ref kinds and both condition check enums.
  - Brief/Target fields, and Grant/Limits.
  - Result: eight error codes, value and error mutually exclusive.
  - The six C12 Actions with exactly C12's fields; lookup source_refs is optional.
  - Compose media types match C08.
  - Operate arguments must be a JSON object. Nested Ref-like data is treated as adapter payload, and this is documented.
- U1-U10 disposition:
  - Resolved in code: U3, U5, U8, U10.
  - Resolved at the model boundary: U4 (an unprovided Ref is invalid_input).
  - Deliberately deferred with named obligations:
    - U1: hosts map not_found/stale/conflict.
    - U2: providers bind their own Result decoders.
    - U6: VER checks artifact provenance.
    - U7: adapters enforce resource rules. At this layer issue_numbers may be negative and repository/path may be empty.
    - U9: hosts enforce grant non-expansion and fencing.
  - The deferrals match design-disposition.json and are not defects. None of them is proven yet.
- What the evidence proves: verification.json records only synthetic results:
  - 15 targeted tests, 119 fixture cases, 3 doctests.
  - 11 consumer-composition tests (5 new) on a synthetic harness.
  - 22 probe-regression tests.
  - Root full suite: 422 tests, exit 0, status PASS, at source_commit 92732afa3f4dcaf84ddf7c821e22b35be883ed54, with seven recorded source_hashes (e.g. pal/contracts_v5.py 683ddeea...).

  These cover pure wire/helper behaviour only. CT labels in the fixture mean parser coverage, not completed service CTs.
- Still unproven: C01-C15 services, TSK authority and fencing, persistence and the Operation ledger, shared-transaction races, real GitHub/provider reads, saved artifact/Ref provenance, a full Goal flow, live UI, and human value.
- Limits of this review: I did not inspect opus-design.txt, the D036 record, the test files, the logs or the base tree. I cannot confirm that base 9390c38a contains the hashed files.

Boundaries:

- The old SWE CO task 6a9dea446fa241ceb6ee876bbdb08be9 remains unknown and untouched; verification.json records no retry, resume or cancel. Its design output is used only as a hash-recorded input (design_output_sha256).
- D036, as cited by the implementation note and the SOL review, authorizes an isolated alternate native implementation and an independent review. It does not cancel, complete or supersede the old task, and it does not change accepted v5 semantics.
- This review wrote only milestone-review.md. It changed or started nothing else: no contract, canonical doc, code, test, DB, service, runtime/state, auth/billing, other project or route.

Next:

Recommended unit: the TSK-01 work-intake core (part of INT-01, D track). It implements C03.create and C02.get_work over an isolated SQLite schema and consumes contracts_v5 values. In one transaction it must:

- accept a DraftBrief and mint formal Condition IDs;
- store the Brief, the Grant, the origin ref and the accepted event. The Grant is the intersection of host config and the request and is never wider;
- enforce key idempotency;
- map U1 errors: unknown goal -> not_found, revision mismatch -> stale, same key with different input -> conflict.

The unit has no model, EXE, UI or GitHub dependency.

Why this unit: every later contract (C04/C07/C08/C09/C10/C13) fences against the WorkRef and Grant that TSK owns. This unit turns INT00 values into the first owned authority and persistence boundary. It also discharges U1 and part of U9 instead of adding more parser surface.

Must verify:

- CT-01/CT-02: the same key returns the same result; a different input returns conflict with no change.
- CT-24: draft/formal ID separation holds through create.
- Grant non-expansion, with zero limits preserved.
- The not_found/stale mapping.
- No model or external I/O inside the transaction.
- Rollback leaves no partial rows.
- The full regression stays green at an exact recorded commit with source hashes.
- An independent exact-commit review.

Even after this unit, real GitHub, Goal completion, UI and human value remain unproven. INT-02/INT-03 follow.

Remaining design problems (for SOL disposition; none is a blocker):

1. INT00-IMPLEMENTATION.md still says the full regression, independent review and consumer check are pending. That text is from authoring time and is superseded by verification.json and sol-independent-review.md. A canonical record should note the supersession.
2. INT00-SCOPE prescribed a three-step CO sequence with SWE-2 High implementation and Opus review. The actual route (Astra/Sol6.1 under D036) should be recorded as its governing replacement.
3. The verification.json source_commit also contains non-INT00 changes (consumer pipeline test, live_cancel_probe fix). Their adoption should be dispositioned separately from INT00/1.
4. This review did not verify how review base 9390c38a, implementation base a6983916 and source commit 92732afa relate.
5. A wrong Action kind passed to a subclass from_json reports 'invalid enum value'. This is minor and bounded.
6. PAL-contracts-v5 is still a design candidate with no independent v5 re-review (section 9). INT00 alignment does not adopt v5.
