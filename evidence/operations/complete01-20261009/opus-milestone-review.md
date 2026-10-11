ALIGNED

# C076 / COMPLETE01 milestone review (Opus)

Reviewer provenance: Opus 5.5 (`claude-opus-5-5`), implement-worker step of the host's controlled pipeline. The host fixed the model and route. Tools were disabled. I ran no tests, read only the supplied snapshot, and activated nothing. The verdict on line 1 applies only to C076 at source `bdce832b8fdb68f6317c033155474a4204703189`.

Labels:

- **[R]** receipt-backed: verification.json or independent-review-initial.json, not re-executed.
- **[U]** unsupplied fixture or log: exists per the records, but I did not see it.
- **[I]** inspected file in the supplied snapshot. When [I] is applied to a test, it means I read the assertions. The pass status is still [R], via full711.

## Evidence base

- [R] Full suite: 711 tests, exit 0, 24.789 s, `python3.13 -E -s -B -m unittest discover -s tests -v`. Environment: authorized host temporary SQLite, loopback and child processes. Not CI or a live service.
- [U] `full-integrated.log` was not supplied. I rely on the source-bound receipt and its SHA-256 list. I cannot confirm that the snapshot bytes match those hashes.
- [R] TSK review: native Astra author, separate native Sol6.1 reviewer. APPROVE at `a48d0cf3`, 46 tests.
- [R] Final RUN review: native Sol6.1 (`/root/int00_sol_review`). APPROVE at `bdce832`, 30 tests (immutable16 + actual8 + strict6), 0.142 s, plus probes for unknown VER errors and same-lease reentry.
- [R] Initial RUN author: `CO task39213ad4 exact devin/swe-2-high Free`, written against immutable16.
- [R] Initial review: native Sol6.1, separate context, source `9f31ba9c`, REQUEST_CHANGES. It found three defects:
  - C02 request shape mismatch (actual8 methods / 10 failures).
  - VER ambiguous/invalid_input released work as failed.
  - Retained reentry omitted diagnostics.
- [I] Method counts match the claimed classes: 9 actual TSK, 8 actual RUN and 6 strict methods.
- [U] Not supplied: TSK22 (`test_task_completion_v5.py`), RUN16 (`test_mock_completion_v5.py`) and the shared `test_verification_connection_v5.py` stage/compose/verify/stop fixture. The actual tests depend on that fixture, so their staging fidelity is receipt-backed only.

## Assessment

**Value.** [I] A saved draft reaches `completed` only through `TaskStore._complete`. On the same transaction it re-reads VER's saved typed result and requires all of the following:

- the current WorkRef;
- the whole ordered artifact set;
- the fixed Condition IDs;
- registered, gated sources;
- `valid` status, with every check MET.

Neither an Expert report nor a saved body can complete work. This is real local safety value, but not usefulness. [I] `_checks` marks `artifact_saved` MET whenever the current set is non-empty, and marks every semantic or source_fetched check `unknown`. So today only artifact_saved-only Briefs can complete, and for those, completed means a draft was saved. The milestone states this limit honestly.

**Owner and contract coherence.** [I] Ownership is separated:

- TSK alone writes state, lease, flags, events and replay.
- VER alone derives checks and status.
- ART owns bodies.
- MEM owns the source gate.
- RUN holds no persistent state. Its receipt validation is defensive, not authority, because TSK revalidates.

Key replay precedes authority. A missing collaborator returns unavailable after the authority checks. Inspect runs under the frozen savepoint and total_changes guard, including failure cleanup. The completion path uses no cross-owner SQL.

**Structural checks vs semantic quality.** The separation fails closed. [I] An unknown check cannot complete (`conflict`), and `test_semantic_or_source_fetch_unknown_cannot_complete` asserts an unchanged DB dump. [I] The result event text `work completed from saved verification` does not say *structural*. Any display must add that label; this is a READ01 item.

**Complete/current authority.** [I] Claim increments the epoch, so epoch equality binds a verification to the current lease. New attachments, yield/reclaim and source stop each make an older verification stale. The new-attachment/new-epoch test and the two-connection ordering tests cover this. A new-key complete on completed work returns `denied` (no active lease) under the existing precedence. Consumers must therefore read state rather than infer from the error code.

**Stopped-source history.** [I] For completed work, `invalidate_by_refs`:

- leaves epoch, state and artifact set unchanged;
- emits one fixed-text notice per completed Goal, listing only that Goal's registered stopped refs.

After the stop:

- VER status becomes `invalidated`;
- ART verification reads are denied, and user_view returns `usable=false`;
- same-key complete and verify replays return the original history;
- a shared completed/running stop is atomic, including when the notice write fails.

**Lease and response-loss safety.** [I]

- **Committed but lost completion:** replays once with an identical request.
- **Persistent loss:** returns unavailable. The lease is already inactive, release returns `denied`, terminal states are preserved, and the next claim moves on without another model call.
- **Uncommitted ambiguity:** keeps occupancy. Same-lease reentry reaches the finalize seam before any inference.
- **Persistent verify loss:** yields, then re-verifies at the new epoch without inference.
- **Interrupted writes:** each actual completion write rolls back under RuntimeError, KeyboardInterrupt and SystemExit.

**Correction sufficiency.** [I] All three retained defects are corrected in the inspected code:

- `current_artifacts` sends `{goal_id, revision}`.
- Unknown verify/complete codes now return unavailable without release; the strict tests cover ambiguous, invalid_input, not_found and limit.
- Retained completion reports the saved finished Steps and only call IDs observed through `get_call`.

[R] An independent re-review approved the corrected source. [I] No Condition or budget was loosened.

## Non-blocking notes (not C076 blockers; no owner gate)

1. [I] Verify `conflict/stale/denied` still routes through `failed()` to `release('failed')`. With actual owners these codes imply a TSK fence, and release then derives paused, queued or cancelled. An unfenced owner disagreement, however, would make the Goal terminally `failed`. This is practically unreachable in single-runner composition. When RUN is next touched, either return to the loop as complete does, or pin the intended behavior with one doubled-owner regression.
2. [R] The TSK46 approval is at `a48d0cf3`, but the receipt hashes `tasks_v5.py` at `bdce832`. Add one canonical line stating that the file is unchanged since the review, or giving the delta.
3. In the milestone prose, "Exact CO SWE-2 High" abbreviates the receipt's `exact devin/swe-2-high Free`, and "Sol" omits Sol6.1. Keep verification.json as the exact canonical provenance.

## Remaining product gap

- [I] **Restart liveness.** If an uncommitted completion stays ambiguous across a process restart, the single host-wide active lease (`v5_tsk_one_lease`) remains held by an old runner identity. There is no supported adoption path, so all work stops until recovery exists. This fails closed; it does not corrupt anything.
- [I] **Waiting-input stop.** `invalidate_by_refs` rejects any registered `waiting_input` work as unavailable. Once questions land, that will block global source stop.
- **Still unfinished:**
  - C11 verification display;
  - PRI/provider/UI;
  - semantic evaluation and source fetching;
  - questions/change;
  - general recovery;
  - v5 activation;
  - human usefulness.

## READ01: REFINE

These are next-scope refinements only; none is a C076 blocker. Resolve them in the READ01 contract through the existing Root/SWE consultation, not an owner question.

**C14-to-body consumer value.** The consumer is useful and concrete. C14 result refs are the only durable way for a user, or a host whose completion response was lost, to see what completed and whether it is still usable. That value holds only if the consumer:

- labels the model as mock and the verification as structural;
- shows TSK state separately from `usable`.

**observed_at.** [I] MEM and ART return a stored creation time; VER stores none. Using the read-snapshot time is the smallest honest choice, but then one C11 field carries different meanings per owner. Refine:

- State the per-kind meaning: for verification, observed_at is when the usability snapshot was taken, never the verification time.
- Add an injectable `clock` to VerificationStore, as MEM and ART have.
- Capture the time inside the read transaction.
- Keep it out of the content and hash.
- Render it as "read at".

This needs no schema change and no backfilled dates.

**Fixed projection hash and usable.** I agree that content excludes current status, so the hash stays fixed. Refine:

- Fix the encoding as `contracts_v5.dumps` UTF-8.
- Consider adding each artifact's public C08 `hash`/`bytes`, so the consumer can show that the inspected body is the verified one.

[I] Note that `invalidated` conflates three causes: source stop, epoch supersession (yield/reclaim/cancel) and set extension. The consumer should say "not current". It should say "source stopped" only when a notice event names that ref.

**All-invalidated purpose denial.** I agree; it is conservative. No READ01 caller uses model_context or verification, so keep those purposes conformance-only: uniform `denied`, documented as also covering supersession, with minimal tests.

**Smallest API and consumer.**

- `VerificationStore.read({ref}, *, purpose)`, plus `clock`.
- One closed host reader over explicit MEM/ART/VER owners.
- One consumer function that:
  - pages EventReader;
  - selects `result` events and completed-history notices;
  - dispatches refs by kind (not position) with user_view;
  - reads TSK `get_work` state;
  - returns a structured inspection plus plain-text rendering.
- A demo script is optional and must use a temporary directory.

**Missing acceptance tests.**

- observed_at is excluded from the hash, using an injected clock.
- Epoch-only invalidation of a non-MET verification keeps identical content and gives `usable=false` with "not current" wording.
- Completed+valid and completed+stopped are shown with TSK state rendered independently.
- Multi-artifact result order is preserved.
- Completion is discoverable via C14 after a committed-but-lost response.
- Pagination works past `page_size`.
- Note/source/receipt refs return unavailable without fallback.
- Rendering includes the mock and structural labels.
- The consumer never calls model_context.
- Reads leave `total_changes` and the DB dump unchanged.

This review implements and activates nothing. It adds no permission, cost, service or provider use.
