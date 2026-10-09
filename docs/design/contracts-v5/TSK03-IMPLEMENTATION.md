# TSK03/1 — durable C14 event pagination implementation note

2026-10-09. Worker: SWE-2 High. Scope: `docs/design/contracts-v5/TSK03-SCOPE.md`
over base `5c427f0857cf54d0b9e2c8e91ab706e87c1df85b`. Prerequisite MEM01 source
`013bf52c5a8ec079614071f251109a9413b08a60` supplies the `v5_intake_event` ledger
that this reader consumes. No input files, schema, canonical records, existing
DBs, providers, auth, fees or network paths were changed.

## What was added

- `pal/events_v5.py` — `EventReader(connection, *, page_size=100)` with
  `get_events(request) -> Result`. Read-only over the existing
  `v5_intake_event` table: SELECT only. No file open, schema create, PRAGMA,
  BEGIN/COMMIT/ROLLBACK, writes, or replacement connection. TSK (`intake_v5`)
  remains the sole ledger writer.
- `tests/test_events_v5.py` — unittest coverage over real `IntakeStore.create`
  plus public `append_event` rows on fresh temporary databases, plus controlled
  corrupt-row fixtures inserted directly. No sleep, no new test framework.
- This note.

## Contract mapping (v5 C14)

- Input is exactly `{session_id, after_event_id?}`; nonempty UTF-8 strings
  only. Extras, missing `session_id`, explicit null, non-str keys and wrong
  types are bounded `invalid_input`. `after_event_id` is an opaque event_id
  resolved by identity and session, never parsed as a numeric sequence;
  unknown or foreign-session cursors are `not_found`.
- Output is exactly `{events, next_cursor}`. Rows are `seq > cursor.seq`,
  exact session, `seq` ascending, capped at `page_size` (host-only strict
  int 1..1000; non-`sqlite3.Connection` and bad `page_size` raise
  TypeError/ValueError). `next_cursor` is the last returned event_id; an
  empty page preserves the supplied cursor, or null when none was supplied
  (the explicit initial-empty convention).
- Stored rows are validated before they surface: nonempty `event_id`,
  `kind` in accepted|progress|question|state|result|error, UTF-8 `text`,
  strict `WorkRef` JSON when `work_ref_json` is not SQL NULL (key omitted
  otherwise), strict `Ref` JSON list in `refs`. Stored order, text and
  immutable WorkRefs — including historical epochs — are preserved verbatim.
- Any malformed row, missing ledger or SQLite read error is bounded
  `unavailable` with a fixed message: no raw row/error leak, no partial
  page, no silent drop, no repair.
- Reads preserve preexisting data and caller-owned transactions: a test
  asserts `in_transaction` and `total_changes` across a read inside an open
  caller transaction, then rolls it back.
- Reading an event is display data only — never current execution or
  reference authority, completion, or a source-body read.

## Verification

Verifier (sandboxed, cwd=workspace):

    /opt/homebrew/bin/python3.13 -E -s -B -m unittest discover -s tests -p test_events_v5.py -v

Actual coordinator verifier output on the previous diff:

    Ran 10 tests in 0.004s
    FAILED (errors=15)

Every error was `sqlite3.OperationalError: unable to open database file` raised
inside test setup: `tempfile.TemporaryDirectory()` placed the test databases
under the process-default TMPDIR, which is outside the verifier sandbox's
writable workspace, so `sqlite3.connect` could not create the file. No test
reached an assertion; the reader itself was not exercised.

Fix in this diff only: `TemporaryDirectory(dir=<absolute verifier cwd>)` so all
fresh temporary DBs live inside the sandbox-writable workspace. No other
behavioral change; `pal/events_v5.py` is unchanged from the reviewed logic.

This worker runs with all tools disabled in the controlled pipeline, so it
could not execute the verifier itself; the coordinator applies this diff and
runs the command above, and its captured output is the actual result.
Worker-side expectation: 10 tests, `OK`. If the coordinator's run differs,
the coordinator output wins and this expectation is wrong.

## Honest limits

- Not a product/UI PASS claim. Full UI/model event replay in a running
  product is unverified, and the root-added MEM→intake→stop→C14 reconnect
  consumer case plus full regression remain separate root evidence.
- Corruption is detected only within rows a page actually fetches; a
  malformed row beyond the current page surfaces on the page that reaches it.
- Cursor anchoring reads only `(seq, session_id)`; a cursor row whose payload
  is corrupt still anchors, and the corrupt row itself is never returned
  because later pages are strictly `seq >` the anchor.
- Reads observe the caller transaction's own uncommitted ledger rows, which
  is required for same-transaction C14 notification reads by owners.
- Concurrency beyond the v5 single-process single-SQLite model is out of
  scope; no push, polling loop or reconnect transport is implemented.

## SOL host verification correction

The attempted cwd workaround above also failed: the CO verifier denies mkdir in
its workspace. Its task is failed/verified:false, with no independent review step.
The original note and exact receipt are retained under evidence/operations/tsk03-20261009.
Root copied only the three allowed outputs, preserved events_v5.py bytes, and changed
test setup back to standard TemporaryDirectory in the already-authorized PAL host
environment. This neither modifies nor bypasses the CO sandbox. The separate host
test result and separate code review will determine adoption; no CO PASS is inferred.
