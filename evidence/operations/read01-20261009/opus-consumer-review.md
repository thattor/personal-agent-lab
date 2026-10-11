REQUEST_CHANGES

# READ01 independent consumer review

Scope reviewed: pal/read_consumer_v5.py and pal/host_read_v5.py at base 367c1de. Checked against frozen READ01-SCOPE, READ01-TEST-PLAN, PAL-contracts-v5 C02/C11/C14, and the supplied owner bodies (memory_v5, artifacts_v5, events_v5, contracts_v5). I am not the author, and I made no edits to source or tests.

## Evidence basis

- **Inspected:** the code text in the supplied snapshot only. Line numbers below refer to that snapshot.
- **Supplied receipts:** sonnet-contract-red.log shows 3 FAILs in test_read_regressions_v5. The coordinator states that Root's fixed 11 consumer tests passed; I was not given a log for that.
- **Not done:** I ran no tests, no demo and no verifier.
- **Not inspectable:** tasks_v5, verification_v5, mock_runner_v5 and the completion fixtures were not readable. Statements that depend on them are marked unverified.
- **Limits:** this review is not product, UI or semantic-quality approval, and it grants no completion authority.

## Contract defects reproduced in the red log

### D1: Completed-history notice is never an item, and is dropped when it has no work_ref

- **Where:** pal/read_consumer_v5.py:108-114 (`_scan`).
  - Only `kind == 'result'` events go into `selected`.
  - The exact NOTICE progress event only feeds the correlation list, and only when `'work_ref' in event`.
- **Contract (SCOPE):**
  - 'Select result events and progress events with the exact COMPLETE01 notice text'.
  - 'Missing event WorkRef produces visible unavailable work, without a guessed ID'.
- **Failure (red log):** `[] != [notice1, notice2]`.
  - The user never sees why a completed result stopped being usable.
  - A notice without a WorkRef disappears entirely.
- **Minimal fix:**
  - In the same loop, append the exact-notice progress event to `selected`, keeping page order with result events.
  - Keep adding to `notices` only when `work_ref` is present.
  - `_work(None)` (lines 119-120) already returns a visible unavailable work result.
  - Change render line 236 from `Result event` to a kind-aware label (for example `Completed-history notice`), so notices are not presented as results.

### D2: One malformed or unknown Ref fails the whole page

- **Where:** read_consumer_v5.py:53, `Ref.from_json(item)` inside `_parse_event`.
  - A ContractError makes `_parse_event` return None.
  - `_page` then returns None (lines 70-71).
  - `_scan` then returns `unavailable: malformed event page` (lines 99-100).
- **Contract:**
  - SCOPE: 'Include all refs by kind/order; retain per-ref errors rather than dropping or substituting them'.
  - HostReader: an unknown kind or malformed input is invalid_input.
- **Failure (red log):** the whole inspection fails with `malformed event page`. Expected: 4 reads, two of them invalid_input.
- **Reachability:** the real EventReader already validates stored refs (pal/events_v5.py:73) and maps a failure to page unavailable (:124-126). So with the real owner this path is reachable only from other C14 providers or doubles. It is still a breach of the consumer contract.
- **Minimal fix:**
  1. In `_parse_event`, keep the event structure strict (refs must be a list), but copy each ref item raw as a JSON value, without parsing it as a Ref.
  2. In `_read` (lines 132-149), handle non-dict items before calling the reader.
     - Return invalid_input directly for a non-dict item.
     - Otherwise pass the item to `reader.read`. HostReader already returns invalid_input for an alien kind or a missing id.
     - Do not call `dict(ref)` on a non-dict. That raises, the generic except turns it into unavailable, and the code is wrong.
  3. Guard correlation at line 114 by building the name set only from items that parse as Ref. Once refs are raw, a malformed ref in a notice would raise KeyError outside any handler.
  4. Guard `_name` (lines 179-180) with a safe fallback, such as the dumps of the item, when kind or id is missing or not a string. Today render would raise KeyError.

### D3: MEM and ART stored times are labelled as read time

- **Where:** read_consumer_v5.py:213. The label is applied to every successful read before the kind branch at line 215.
- **Owner facts:**
  - MEM `_append_locked` stores `self._clock()` at append time, and `read` returns that stored `observed_at`.
  - ART `save` stores `observed`, and `read` returns it.
  - Only VER.read returns the read snapshot time as `observed_at` (SCOPE: 'MEM/ART retain their existing stored observation times; document the per-kind meaning').
- **Failure (red log):** the record and artifact sections say `time of this read, not creation time`. That is false, and a user could misjudge when the draft was saved.
- **Minimal fix:** move the time line into per-kind branches. No schema change is needed.
  - Verification: `Read at: ... (time of this read, not creation time)`.
  - Record and artifact: `Stored at: ... (owner's saved observation time)`.

## Further actionable bug (found by inspection, not run)

### F1: HostReader rejects real MEM record bodies

- **Where:** pal/host_read_v5.py:15-16 (`_BODY_KEYS`) and :27 (`set(value) != _BODY_KEYS`).
- **Evidence:**
  - MEM.read (memory_v5 `read`) returns a body without `work_ref`.
  - C11 defines `work_ref:WorkRef?` and `version:str?` as optional fields.
  - ART and VER do include work_ref.
  - The test doubles' `c11()` includes work_ref for every kind, so the fixed tests cannot detect this.
- **Failure:** every real `record` read through HostReader becomes `unavailable: owner unavailable`.
  - The record subtest of `test_three_real_owners_return_matching_utf8_hashes_without_writes` in tests/test_read_connection_v5.py should fail. No receipt for that file was supplied.
  - After the D1 fix, every notice item's record ref would render as unavailable instead of showing the stopped record.
- **Minimal fix:**
  - Require ref, content, media_type, hash, observed_at, source_refs and usable.
  - Allow optional `work_ref` (absent, null, or a valid WorkRef) and optional `version` (a str).
  - Reject any other key.
  - Owners stay unchanged.

## Non-blocking observations

- **Correlation window:** notice correlation sees only the scanned window, starting after `after_event_id` and ending at max_pages. If a result's notice lies before the cursor or after truncation, the result shows `not current`. This matches the conservative rule (say source stopped only with evidence). It should be documented, not changed.
- **Demo session (unverified):** scripts/demo_readback_v5.py stops the source with `session_id='demo-control'`. tasks_v5 was not readable, so I cannot confirm that TSK writes the NOTICE into the work's own session. The real demo output must show `source stopped`; that should not be assumed.
- **Correct as inspected:**
  - Calls use only purpose user_view.
  - max_pages bounds are checked before any event access.
  - Cursor and stall checks, and empty-page termination, are in place.
  - Per-work errors stay visible.
  - TSK state is kept separate from current usability.
  - Mock and structural labels are present.
  - There are no writes and no cache.

## Minimum repair (one small author change)

1. D1: select notices as items, and fix the render label.
2. D2: keep refs raw, return per-ref invalid_input, and add guards in `_read`, in notice correlation and in `_name`.
3. D3: per-kind time labels.
4. F1: accept the optional C11 keys in HostReader.

No changes are needed to the MEM, ART, VER, TSK or C14 owners, to the schema, or to the frozen tests. Nothing here widens the output schema or semantic authority.

## Missing tests (for a separate test author)

- **Doubles:**
  - HostReader accepts a body without `work_ref`, and a body with a str `version`.
  - HostReader rejects a non-str version and any extra key.
- **Real owners:** after stop_reference, the notice item is visible and its record read through actual MEM succeeds with usable=false.
- **Malformed refs:**
  - A notice containing a malformed or non-dict ref causes no exception, gets a per-ref invalid_input, and is ignored for correlation.
  - A non-dict ref item (a string or number) gives invalid_input, and render does not raise.
- **Render:** notices are labelled distinctly from results.
- **Times with real owners:** record and artifact show stored times that stay unchanged across reads, while an injected VER clock changes only the verification read time.
- **Window:** a notice before the resume cursor yields `not current`, which pins the conservative window.
- **Receipts:** logs for test_read_connection_v5, and captured demo output before and after the stop.

## Responsibility separation

- **Code author:** repairs to the consumer and HostReader only.
- **Regression test author:** the tests above; not the code author.
- **Root:** real demo and connection evidence, canonical records, and the acceptance decision.
- **This reviewer:** inspection only. No edits, no runs, no product approval.
- **Owners (MEM, ART, VER, TSK, EventReader):** unchanged. Their current contracts already provide what these fixes need.

## User value

After the repair, a person following a session's results can see:

- the saved draft;
- the fixed conditions and the historical checks;
- when each item was stored versus when it was read;
- why a completed result is no longer current, because the stop notice is visible.

Without the repair, they miss the stop notice, misread save times, and lose real record readback.

## Provisional next dependency

First, real readback evidence is needed:

- passing connection tests;
- captured demo output before and after the stop, showing `source stopped`, stored versus read times, and the visible notice.

After that evidence exists, the provisional next dependency is the next RUN change. That change carries C076's retained verify-authority note. After it, this inspection can be reused for the PRI-04/C14 display path. INT-02 (EXE GitHub read) remains independent. This ordering is provisional, and no owner approval gate is added here.
