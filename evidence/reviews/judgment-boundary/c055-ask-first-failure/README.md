# C055 — explicit ask-first request bypassed

First UI-CLARIFY attempt on46bd418 / product53a616 fails the original frozen contract.
The user explicitly required asking for the missing date, start time and location
before using them. Primary replaced that requirement with placeholder drafting;
Expert completed one710-byte draft without either a pre-Goal grouped question or a
persisted Expert question. The artifact also adds an unsupported relative time
(“もうすぐ”). No fixed second answer was sent and no rescue/retry was attempted.

The ordinary Chrome UI accepted the first input, displayed completion and opened the
actual artifact. The saved bytes match the host receipt, Goal/Attempt, revision/epoch
and fixed acceptance. That integrity PASS is separate from semantic FAIL. Original
state, body, binding and bounded-stop records are retained with byte hashes. Two
native slots of three were consumed; the unused slot was not repurposed. The owned
host exited0, PID was absent and port returned ECONNREFUSED61 after148.173seconds.
The ignored runtime DB/proof remain intact; no canonical repair occurred. Inputs
are controller-authored synthetic tests, not an owner usefulness evaluation.

Diagnosis: Primary's generic-draft-now / ask-only-if-unusable instruction failed to
preserve the explicit ordering constraint. It silently substituted placeholders
although the user did not request a blank template. A receipt proves saved bytes,
not adherence to the user's meaning. This finding stops the affected candidate's
remaining UI sequence; TARGET-C and COMPOUND remain NOT_RUN. The original ABS-A2
refusal remains untouched and is not replaced by this test.

Next: obtain the already-requested official Opus challenge, record the smallest
repair before editing, preserve the ask-first constraint in Primary's semantic
contract, then freeze and verify a new candidate. Reuse existing host safeguards;
no keyword router, new schema, review-created owner gate or weakened acceptance.
C053 full268 PASS applies to the unchanged pre-repair code, not to a future repair.

Additional retained observation: C054 ABS-C2's Primary specification, also displayed
in its acceptance acknowledgement, uses “her help” for Mika although gender was not
provided. The final Japanese artifact contains no gender claim and still passes its
frozen artifact-only oracle. This does not qualify the acknowledgement/specification
as grounded. The original after.json already preserves the exact text. Track the
unsupported inference under the existing no-invented-personal-facts boundary; do not
hide it or expand the current ask-first repair into a new feature/rule system.
