# VER01/1 implementation note — pal/verification_v5.py

Scope: VER01-SCOPE Stage A only. Deterministic saved verification. No Goal
completion, provider, semantic model, EXE evidence, UI, budget spend, or use of
earlier PAL code. Stdlib plus public `pal.contracts_v5` only; storage layout is
private (`v5_ver_body`, `v5_ver_replay`) and no other owner's SQL is read.

## Design

`VerificationStore(connection, *, context, artifact_inspect, source_gate,
id_factory=None)` mirrors `ArtifactStore` conventions: idle
`isolation_level=None` connection, schema under `BEGIN IMMEDIATE`, readonly
collaborators wrapped in a savepoint guarded by `in_transaction` and
`total_changes` checks.

- `verify({key,work_ref,artifact_refs})`: closed-input validation
  (artifact-only refs, SQLite int bounds, nonempty key); canonical replay of
  the original input before any callback (differing input -> conflict); TSK
  `context(conn, {work_ref}, purpose='save')`; exact ordered set equality else
  conflict; per-artifact inspect binding (exact Ref, Goal/revision match else
  stale, older artifact epoch allowed); ordered union of required context
  records and artifact dependencies gated once; fixed-order checks —
  `artifact_saved` met iff the verified set is nonempty else unmet,
  `semantic`/`source_fetched` always unknown with fixed reasons. Input,
  conditions, bindings, source union, checks and receipt commit atomically.
- `get_by_key({key})`: historical receipt only, strictly re-validated against
  the stored record; never grants authority.
- `get_verification` / `inspect`: stored record is re-validated (canonical
  input, exact fixed condition IDs/order, recomputed deterministic checks,
  artifact bindings, conservative source union; corruption -> unavailable,
  no repair), then compared against `context(purpose='status')`, the exact
  current ordered set, current artifact integrity and the source gate.
  Explicit stale context, legitimate ordered set append or denied source evidence
  -> `invalidated`; not_found/unavailable context -> same error. Same-WorkRef
  condition/required-ref changes, set shrink/reorder and uncertain owner errors
  -> unavailable. Current artifact metadata including its original epoch must
  match the immutable snapshot exactly. `inspect` is readonly on the caller's active
  transaction.

Errors: malformed caller input -> invalid_input; ordinary Exception ->
unavailable with rollback; BaseException -> rollback then re-raise. Messages
are bounded and contain no private input.

## Verifier

Declared verifier (executed by the coordinator, not this worker):

```
python3 -I -S -B -m unittest discover -s tests -p test_verification_v5.py -v
```

No pass claim is made here; unit-test success would not establish product
completion, actual MEM/TSK/ART integration, or C10 readiness.

## Remaining limits

- A trusted collaborator's COMMIT inside a guard cannot be undone (documented
  limit shared with ArtifactStore).
- `semantic` and `source_fetched` stay unknown; no evaluator/EXE owner exists.
- C10 control integration and terminal-safe lease handling remain out of scope.
  Root separately adds real-owner integration, reopen and two-connection cases;
  their evidence is not attributed to this SWE author.

## Independent integration corrections

Native Sol review of candidate9147584 and Root strict probes reproduced malformed
fixed context and overly broad invalidation. Root rejects empty/duplicate owner
sets and dependencies, empty Conditions, out-of-range ART metadata, unsupported
owner errors, and non-verification read refs. Current artifact WorkRef is compared
in full. The id factory is guarded before writes so premature COMMIT cannot cause
autocommitted partial VER rows. No guard can undo a collaborator's own commit.
Nine independent integrity methods reproduced20 failing subcases; after fixes all
45 focused tests pass (12 actual connection,8 TSK context,16 original acceptance,
9 integrity). Full regression and independent rereview are recorded separately.
