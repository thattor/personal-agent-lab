# TSK03/1 — durable C14 event pagination

SOL owns the contract/integration. SWE-2 High authors an isolated read-only provider;
an independent Opus context reviews the code. PAL v5 C14. Prerequisite MEM01 source
013bf52c5a8ec079614071f251109a9413b08a60. Worker base is the commit with this scope.
This is the next authorized unfinished connection, not another owner approval gate.

Implement exactly pal/events_v5.py, tests/test_events_v5.py and
docs/design/contracts-v5/TSK03-IMPLEMENTATION.md. Read current intake_v5.py,
contracts_v5.py, this scope and v5 C14. No changes to those input files, schema,
canonical records, existing DBs, runtime/providers, auth, fees or network. Python
standard library only; temporary SQLite test DBs. No full product/UI PASS claim.

Expose EventReader(connection, *, page_size=100) and get_events(request) -> Result.
Constructor accepts sqlite3.Connection; page_size is a host-only strict int1..1000.
No file open, schema create, PRAGMA, BEGIN/COMMIT/ROLLBACK or writes. Do not open a
replacement connection. TSK alone writes the existing v5_intake_event ledger.

Input exactly {session_id,after_event_id?}. IDs are nonempty UTF-8 strings; reject
extras, wrong types, explicit null and bad Unicode as bounded invalid_input.
No cursor means start from the first event in the requested session. A cursor must
identify an existing event in that same session; missing or another-session cursor
is not_found. The cursor is opaque event_id, never parsed as a numeric sequence.

Read rows after that cursor's seq, filter the exact session, order seq ascending,
return at most page_size. Output exactly {events:[{event_id,work_ref?,kind,text,refs}],
next_cursor}. next_cursor is the last returned event_id; with an empty page preserve
the supplied cursor, or null if no cursor was supplied. The latter is the explicit
initial-empty cursor convention. A consumer omits a null cursor on the next request.
Omit work_ref if its stored value is SQL NULL; otherwise strict WorkRef JSON. Kind
is accepted|progress|question|state|result|error. refs are strict Ref JSON. Preserve
stored event order/text/immutable WorkRefs, including historical epochs. Reading an
event is never current execution/reference authority, completion or source-body read.

Validate saved row structure before returning it. Malformed JSON/IDs/kind/text or
missing schema/SQLite read error is bounded unavailable with no raw row/error leak.
Do not silently drop a corrupted row, return partial success or repair the database.
Read operations must preserve preexisting data and any caller-owned transaction.

Required tests: real IntakeStore.create plus public append_event populate the ledger;
page_size2 across mixed sessions, exact cursor continuation with no duplicates or
gaps, no rows before/after cursor, initial empty, wrong-session/unknown cursor,
Unicode/empty text and historical WorkRef preservation, reopen persistence, strict
input/config failures, missing schema/corrupt stored data, and zero writes/transaction
control with an existing caller transaction. Use actual provider public calls as
well as controlled corrupt-row failure fixtures. No sleep-based timing or new test
framework. Run python3 -E -s -B -m unittest discover -s tests -p test_events_v5.py -v.

Return the three-file diff, actual test result and limitations. Root verifies the
exact diff and adds a MEM→intake→stop→C14 reconnect consumer case; full regression
and independent review are separate evidence. After acceptance, continue TSK/RUN
execution/control work, not a checkpoint stop. Full UI/model/event replay in a
running product remains unverified.
