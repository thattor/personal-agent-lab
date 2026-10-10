APPROVE

# READ01 independent final review: source ff1a1cc

**Reviewer and basis.** I am Opus 5.5, independent of SWE b981736d/f2e11233, AGY Sonnet and Root. This review uses only the supplied snapshot. I ran no command, test or demo. I counted line numbers by hand from the snapshot (±2).

**Verdicts**
- **Code: APPROVE** for ff1a1cc as a whole.
- **Milestone: REFINE.** Only the evidence provenance needs fixing.
- **NEXT ASK01: REFINE.** This does not block READ01.

This approves current source only. It is not a retroactive approval of the original Sonnet candidate or of any earlier commit.

## Evidence limits
- **Full747:** 25.142s with exit0 is receipt-only (verification.json). No full log was supplied.
- **Focused36:** the log's names match the 36 methods in the four supplied test files (VER10/consumer11/regression6/connection9). I did not execute them.
- **Unsupplied dependencies:** the connection tests rely on fixtures I could not see (test_completion_connection_v5, test_mock_completion_connection_v5). They also rely on unsupplied modules (intake_v5, mock_runner_v5, artifact_content_v5, artifact_integrity_v5). I judged them by test intent plus the owner code I could see.
- **Original findings:** Opus531650's finding text was not supplied. I inferred the D1/D2/D3/F1 mapping below from the milestone, the receipt and the test names.

## Code inspection

### VER.read (pal/verification_v5.py:439-489)
- **Same snapshot.** A deferred BEGIN (:450) is followed by _stored, _current_status and the clock, all on one connection.
  - Every callback passes through _guard (:204-224), which uses a savepoint plus a total_changes check.
  - A mutating clock or owner therefore fails closed as unavailable.
  - A committing callback is detected, but rollback is not falsely claimed. This matches the frozen SWE disposition.
  - BaseException rolls back and propagates (:487-489).
- **Projection (:457-465).** It contains exactly work_ref, conditions, artifact_refs, artifacts{artifact_ref,hash,bytes}, source_refs and checks.
  - It excludes the replay key, step_id, artifact provenance, record bodies, read time and status.
  - dumps is sorted and normalized, and the hash is SHA-256 of the returned UTF-8 (:473).
  - So content and hash cannot change with invalidation or the clock.
- **Clock (:456; _read_time :43-53).** It is read inside the TX and must be a nonempty ISO-8601 value with zero offset. Naive, +09:00 and bool values are rejected.
- **Usability (_current_status :396-437).**
  - Context stale (epoch or revision) gives invalidated (:403).
  - Strict-prefix growth of the artifact set gives invalidated (:411-413).
  - Artifact-inspect denied or gate denied gives invalidated.
  - Any other mismatch or corruption gives unavailable.
  - Unknown or unmet checks stay usable=true. usable means the saved verification is still valid, not that checks are met.
- **Purpose denial (:467).** Any invalidation is denied for model_context and verification. user_view gets the identical body with usable=false.
  - Only a missing requested Ref is not_found. A status-context not_found becomes unavailable (:483).
  - Typed get_verification/inspect are unchanged, so C10 completion authority is untouched.

### HostReader (pal/host_read_v5.py:68-95)
- An invalid purpose raises ValueError before any dispatch (:79-80).
- Requests must be a closed {ref}.
- Only RECORD, ARTIFACT and VERIFICATION are dispatched. note/source/receipt return unavailable, and an unknown kind returns invalid_input.
- Each owner gets a fresh dict and a keyword purpose (:92).
- Exception becomes unavailable; BaseException propagates.
- checked_result (:53-65) requires the exact requested Ref and the strict body shape.

### Consumer (pal/read_consumer_v5.py)
- **Exact public calls only:**
  - get_events (:109);
  - get_work({goal_id,revision}) (:142);
  - reader.read(..., purpose='user_view') (:154).
- It has no writes, cache or private SQL.
- **Pagination (:99-135):**
  - Pages with no selected events still advance.
  - An empty page ends the scan with truncated=false and keeps its cursor.
  - A repeated or non-advancing cursor, or a malformed or non-Result page, fails.
  - Reaching max_pages after a nonempty page gives truncated=true with the last cursor.
  - _page enforces next_cursor equal to the last event id.
- Per-work and per-ref failures stay inside successful items. Separate works are never merged.

## D1/D2/D3/F1 and the six regression tests (judged from code)
- **Completed-history notice shown as an item.** _scan selects result events or exact-NOTICE progress events (:126-129), whether or not they carry a work_ref. Without a work_ref, the item shows unavailable work (:139-140) and is left out of correlation (:130). Fixed.
- **Unknown or malformed refs stay visible.** _parse_event deep-copies refs without validating them (:70-71), and HostReader turns each bad one into invalid_input with validity None. There is no page failure and nothing is dropped; order is kept. Fixed.
- **Malformed notice refs.** _ref_key removes non-Refs from the named set (:132-133). They therefore cannot produce a false 'source stopped'. Fixed.
- **Resumed window.** Notices come only from scanned pages. A stop recorded outside the window stays 'not current' (:164-169). This is conservative and matches scope.
- **Timestamp meaning.** render labels VER as 'Read at … not creation time' and MEM/ART as 'stored observation time' (:242-245). Fixed.
- **F1, optional C11 fields.** _BODY_KEYS/_OPTIONAL_BODY_KEYS (:15-17, :29, :40-43) accept a work_ref that is absent, null or valid, and a version that is absent or a string. They reject extra keys and non-string versions.
  - This matters for real MEM, whose MemoryStore.read omits work_ref (pal/memory_v5.py). Under the strict 8-key form, every record read would have been unavailable.
  - Fixed, and exercised on real MEM by test_three_real_owners and by the record section of the demo log.

**Test quality.**
- The six regression tests use protocol doubles, not real owners. Real-owner coverage comes from the connection file.
- In test_malformed_notice_refs, the final check that 'notice' appears in the render is satisfied by the event_id alone, so it proves little.
- These are weak spots, not defects.

## Nonblocking findings (no change required for READ01)
- **N1: render layout can be spoofed.** Condition descriptions, check reasons, event text and error messages are printed without indentation (:218, :222-223, the Event line).
  - A model-proposed DraftCondition containing newlines could print a forged 'Current usability: current' line.
  - The structured inspection is unaffected.
  - Escape or line-prefix every owner and model string before any PRI/UI exposure.
- **N2: hash format only.** HostReader checks the hash format (:38) but does not recompute SHA-256(content). Owners compute it correctly; recomputing would harden the shared boundary cheaply.
- **N3: duplicated NOTICE literal.** The text appears in the consumer (:14) and in TaskStore.invalidate_by_refs. Drift fails safe to 'not current'. Prefer a shared constant or a structured notice code before adding more notices.
- **N4: hardcoded mock label.** render always prints 'Model: mock' instead of deriving it from provenance. This must change before any real-model path.
- **N5: snapshot test relies on journal mode.** test_read_snapshot_orders_a_stop_attempt… expects the other writer to fail.
  - That holds in rollback-journal mode with a short busy timeout, which fits the 0.152s run; the fixture was not supplied.
  - It would not hold under WAL.
  - The guarantee itself (one read TX) holds either way.
- **N6: misleading error reason.** HostReader reports 'missing key' for extra keys (:82-83). Cosmetic.

## Current value, ownership, gaps
**Value.**
- A local consumer can now follow C14 → C02 → C11 through real MEM/ART/VER.
- It shows the saved draft, the fixed structural checks and present usability as separate facts.
- After a source stop, history stays byte-identical while usability flips.
- ASK01 and any future UI need this read path. It never grants completion or dispatch authority.

**Ownership and contracts.** VER owns its read, HostReader is stateless, and the consumer uses only public calls. There is no schema change and no mutation of old rows. This matches READ01-SCOPE and C11.

**Whole-product gaps.** Still missing:
- PRI/UI;
- a real model;
- GitHub/EXE (source/receipt refs are unreadable);
- semantic verification;
- restart recovery;
- question/change features;
- evidence of usefulness to the user.

**Mock and structural limits.**
- Checks are structural only: artifact_saved means the ordered artifact set is nonempty.
- The expert is a hardcoded mock, and the consumer tests use doubles.
- There is no cross-owner atomic snapshot: the consumer scans, then reads. A stop in between degrades the result to 'not current'.

## Milestone: REFINE
The code and the connection tests support the behavior claims. Evidence provenance needs these corrections:
1. **Log header mismatch.** Line 1 of demo-green.log reads 'Local temporary SQLite, mock model, structural verification.' The header printed by the __main__ block of scripts/demo_readback_v5.py reads '…demo; mock model and structural verification only.' The rendered sections match render() exactly, so the log probably came from a wrapper or an earlier script version.
2. **Demo assertions not in the supplied script.** The milestone says the actual demo 'additionally asserts complete/history/hash/source-stop/visible-MEM' and cites demo.json. The supplied script checks only the completed status and writes no JSON. Either name and commit the harness that asserts and writes demo.json, or move those assertions into the script and regenerate the log from the documented command.
3. **verification.json.** Set independent_final_review to this verdict and keep full747 labelled receipt-only.

None of this implies a code change, a new gate, or any service/provider/cost/auth change.

## NEXT ASK01: REFINE (nonblocking for READ01)
The proposed next value is right: keep one mock question and its saved answer through waiting and resume, ending in completed plus readback. Before code, freeze the following.

**C04 save API.**
- Add C04 to TaskStore: key, work_ref, step_id, question, missing_fact and source_refs in; question_id out.
- Save in one TX: the finished ask step, waiting_input, the question event and the replay.
- Today TaskStore.begin_step allows only report/lookup/compose, and control has no answer command.

**Lease release.**
- TaskStore.release keeps terminal states and maps a paused flag to paused. Every other state becomes queued (yield) or failed. It cannot produce waiting_input, and it abandons started steps.
- Decide whether C04 deactivates the lease atomically or release gains an explicit outcome.
- Release must never queue waiting work.

**Pause, drain and cancel races.** Decide:
- whether C04 is rejected under pause_requested or drain (the contract implies no new save);
- what cancel does to an open question;
- that resuming a paused work with an open question returns waiting_input (current resume always queues).

**Source stop.**
- TaskStore.invalidate_by_refs rejects waiting_input with unavailable, which would make the whole MEM stop_reference fail.
- C05 instead requires checking the question's sources, closing the old question and queuing.
- Resolve this in the same scope.

**Answer authority.**
- Check goal and revision; ignore epoch.
- Check question_id freshness.
- Register the answer record as a work source before admit_call, so a later stop and the readback can correlate it.
- Carry the answer in claim pending_inputs.
- Replay after a later terminal state returns the saved answer result without implying current state.
- Recover a lost reply by key.

**Question identity.** RefKind has no question kind, yet the C13 checkpoint names open_question_refs. Freeze that field as question ids from C02 rather than inventing a Ref kind.

**Readback.** Decide whether inspect_session selects question events (it currently selects only result events and notices) or the demo reads them through C02 open_questions.

**Acceptance.**
- CT-06, CT-07, CT-10 and CT-22.
- Budget is not reset by answer or resume.
- Pause during ask.
- Source stop while waiting.
- Answer replay and conflict.
- Real temporary-SQLite end-to-end run, with prior evidence unchanged.
- Carry C076's verify-authority note into the RUN edit.
- Restart recovery stays out of scope.
