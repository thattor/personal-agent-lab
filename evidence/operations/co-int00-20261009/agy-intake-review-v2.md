# AGY Opus 5.5 High — bounded TSK intake refinement

Requested model `claude-opus-5-5-high`; direct AGY CLI route. Final public response follows.

**ALIGNED**

The corrected boundary is consistent with the C03, C02 and C14 excerpts. I withdraw two points from my first review. Rejecting zero limits or an empty capability intersection contradicts INT00/1. Checking sources before the transaction leaves a real gap, because C05 can stop a reference without deleting it. There are no blockers left in this isolated unit. Below are choices that follow from what Root has already decided, so they need no approval.

## Choices to state in the unit spec

1. **Order of steps.**
   - Pure shape and strict-type validation runs first, outside the transaction, giving `invalid_input`.
   - Then `BEGIN IMMEDIATE`.
   - Then look up the `C03.create` key. An equal input returns the stored result; a different input returns `conflict`. Either way the transaction ends with no writes.
   - Then compute the Grant intersection and check that the target repository is in it, otherwise `denied`.
   - Then `source_gate`, then the writes, then `COMMIT`.
   - The authorization checks come **after** the replay lookup. That way an equal-input replay returns only the original stored result, even if host config or the gate has changed since.

2. **Rejections are not saved.** `invalid_input`, `denied`, `not_found`, `unavailable` and `conflict` leave no key, row or event behind. A same-key retry after the source is restored is treated as a fresh create. This matches "no saved partial rows/event/key".

3. **Gate contract enforcement.**
   - Any return value other than the four allowed ones means `unavailable`.
   - An exception means `unavailable`, followed by a rollback.
   - If `conn.in_transaction` is false after the gate returns, the gate committed or rolled back on its own: return `unavailable` and write nothing.
   - The gate is called before any write, so a misbehaving gate cannot commit partial state.

4. **What the gate checks.** `origin_record_ref` (kind must be `record`) and every entry in `context_refs`. `target.files[].ref` is a repository revision, not a C03 `Ref`, so it does not go through `source_gate`.

5. **Grant fidelity.** Zero limits and an empty capabilities list are saved and read back exactly as given, never as null or "unlimited". Limits must be strict ints ≥ 0: `bool` and negative values return `invalid_input`.

6. **Abort before commit.** Use an existing injected seam, such as an `id_factory` that raises when the event ID is generated after the earlier inserts. No new framework.

## Minimal tests

**Grant**
- An exact intersection with a zero limit and empty capabilities is saved and read back unchanged.
- A target repository outside the intersection returns `denied` with no effects.
- Free-text constraints leave the Grant unchanged.

**Source gate** (synthetic table in the same DB)
- A missing row returns `not_found`.
- A row stopped before create returns `denied`.
- A raising gate returns `unavailable`.
- A gate returning an invalid value returns `unavailable`.
- A gate that commits returns `unavailable`.
- In every case: no goal, condition, grant, binding, event or key rows.
- The gate sees `in_transaction == True` and the same connection.

**Replay**
- Close and reopen the temporary DB, then replay the same key with equal input. The result is identical, including condition IDs, and there is one work row and one event.
- Stop the source, then replay. The stored result still comes back, with no gate call and no new effects.
- Any changed field returns `conflict`, including `request_scope` or condition order.

**Atomicity**
- An abort before commit leaves every table empty.
- A same-key retry after that abort succeeds.

**Busy**
- A second connection holds `BEGIN IMMEDIATE` with a zero timeout. Create returns `unavailable` and writes nothing.

**`get_work`**
- After reopening: revision 1, epoch 0, `queued`, formal condition IDs, the stored Grant, the bound expert, empty artifact and question lists.
- An unknown goal returns `not_found`.
- `revision=2` returns `not_found`.
- `0`, `True` and `"1"` return `invalid_input`.
- The read makes no writes.

**Event**
- Exactly one `accepted` event, carrying the `work_ref`, written in the same transaction.
- The internal writer never commits.

## Gaps in the real MEM/PRI services (not blockers here)

- **PRI:** the trusted semantic resolution that produces `request_scope` is NOT_RUN. Intersection protects the host ceiling but does not prove the scope matches what the user authorized.
- **MEM:** the real source authority and C05 reference-stop are not built. The synthetic gate only proves the seam and the atomic ordering.
- **C14:** the shared transaction owner and the public `append_event` are not implemented.
- **Execution owners:** admission must re-check current host, Grant (including zero budgets) and source authority. A replayed create result grants no current execution authority.
- **Other deferred items:** the startup lock, historical revisions (NOT_RUN), and `stale` mapping for state changes against an expected revision.

