# TSK03 independent code review: EventReader and root MEM to C14 reconnect

Base: 0cf8563378223fa080e8abaf979e42b2bdf73e51. This is a review only. It makes no source, test, schema, runtime, auth, cost, network or canonical changes. The reviewer ran no commands.

Inputs read: pal/events_v5.py, pal/intake_v5.py, pal/memory_v5.py, pal/contracts_v5.py, tests/test_events_v5.py, tests/test_memory_intake_pipeline_v5.py, TSK03-SCOPE.md and PAL-contracts-v5 C14.

The attached logs (host-targeted.log: 10/10 OK; connected.log: 7/7 OK) are host evidence only. This reviewer did not produce or rerun them, and nothing below is model self-report used as test evidence.

## Checks against TSK03-SCOPE and C14

- **Opaque same-session cursor.** `get_events` resolves `after_event_id` only by exact `event_id` equality and uses the anchor row's own `seq`. The cursor string is never parsed. A missing cursor and a cursor from another session both return the same `not_found` / 'cursor not found', so there is no cross-session existence oracle. Tests cover an unknown cursor, a numeric-looking '1' and a foreign-session cursor.
- **Pagination.** Rows are selected with `seq > anchor.seq` and an exact `session_id` match, ordered by `seq ASC`, with `LIMIT page_size`. `next_cursor` is the last returned `event_id`. An empty page returns the supplied cursor, or null when no cursor was given (the initial-empty convention). The page_size=2 test interleaves two sessions and asserts exact ledger order, no duplicates or gaps, and that the terminal empty page preserves the cursor. A separate test asserts the initial-empty page returns null.
- **Strict input and config.** The request must be an exact dict with str keys, `session_id` required and `after_event_id` optional. Both IDs must be strict nonempty str that encode as UTF-8; surrogates give invalid_input. Explicit null, extra keys and wrong types are rejected with a bounded reason. The constructor requires a `sqlite3.Connection`, a strict int page_size (bool and float are rejected) and the range 1..1000. All of this is tested.
- **Corrupt or missing rows.** Every row in the page is validated before `Result.success` is built:
  - event_id is checked as an identifier;
  - kind is checked against the enum, and text is checked as a str;
  - refs must be a JSON list of strict Ref;
  - work_ref must be strict WorkRef JSON.
  Any ContractError or `sqlite3.Error` gives the fixed 'event store unavailable' with no refs. This includes a missing table, a closed connection and an undecodable TEXT value. There is no partial page, no dropped row and no raw data in the error. Six corrupt fixtures, each sharing a page with a valid row, and a missing ledger on both cursor paths are tested.
- **Read-only and caller transaction.** The reader issues only three SELECTs. It runs no BEGIN, COMMIT, ROLLBACK, PRAGMA or DDL, does not call commit() or rollback(), and opens no connection. The caller-transaction test checks four things:
  - a pending row is visible inside the caller's transaction;
  - `in_transaction` stays true;
  - `total_changes` is unchanged;
  - after rollback, only committed rows are visible.
  On reopen, `total_changes == 0`.
- **Historical WorkRef.** The stored `work_ref_json` is decoded as-is and never compared with `v5_intake_work`. The test raises the work's epoch to 9, and the event keeps its original WorkRef. A SQL NULL work_ref is omitted from the event.
- **Root MEM stop and reconnect.** The test reads two pages at page_size=1 and holds the cursor. It then stops the record twice; the second stop is a replay. It closes the connection and reconnects with new stores (the schema step is IF NOT EXISTS only), then resumes:
  - exactly one state event appears, with epoch+1 and refs [record];
  - the next page is empty and preserves the cursor, so there is no duplicate.
- **Crossed actor and work sessions.** The 'control' session holds only the ack event, without a work_ref. The work's session receives the invalidation event. A cursor taken from 'control' gives not_found on the work session.
- **Temp-dir change.** Both test files use the default `tempfile.TemporaryDirectory()` with cleanup and no repo-relative or hard-coded path, so the location follows the host TMPDIR. The pre-change version is not in this snapshot, so the diff itself cannot be checked. The docstring note in tests/test_events_v5.py is a process narrative and a comment only; it is not evidence.

## Non-blocking observations

1. Outside a caller transaction, the anchor lookup and the page query are two statements, not one snapshot. This is safe for an append-only ledger with serialized writers, where seq order equals commit order. It should be revisited if ledger rows are ever deleted, because INTEGER PRIMARY KEY without AUTOINCREMENT can reuse the max seq.
2. The reader is fail-closed: one corrupt row blocks all later reads for its session until the owner repairs it. This matches the scope (no silent drop), but the repair path is outside this module.
3. Corruption is detected only within the requested page. Rows in other sessions or on later pages do not affect the current response. This matches the scope's 'validate before returning'.

## Untested limits

- SHARED-EXAMPLES.json and pal.sanitize were not readable here. The connected-test inputs (session ids, text) and the sanitizer's behavior are inferred from usage only.
- docs/design/contracts-v5/TSK03-IMPLEMENTATION.md is not in the readable set and was not reviewed.
- The corrupt fixtures do not cover:
  - BLOB or non-text columns;
  - invalid UTF-8 bytes;
  - invalid JSON in work_ref_json;
  - duplicate JSON keys;
  - a corrupt row on a later page after a valid earlier page;
  - a corrupt row in another session.
  Code inspection shows these paths are handled, but no test exercises them.
- No test asserts that the error message excludes row content. This is inferred from the fixed strings.
- Only `isolation_level=None` connections are tested. Not tested: legacy deferred mode, `autocommit=False`, savepoint-only caller transactions, and a second connection reading while a writer holds the lock (expected result: busy, then unavailable).
- No concurrent writer runs during pagination, and there is no large-ledger or page_size=1000 test.
- There is no live UI, model, runner or running-product event replay. Real UI dedupe by event_id is not exercised.
- No full regression log is attached; only the targeted logs are.

## Blockers

None found, so no file:line blocker citations are given.

## Disposition

This is a code-review disposition only. It is not a product, UI or integration PASS. The original failed CO task remains failed, and this review is not a retry of it.

Verdict: APPROVE
