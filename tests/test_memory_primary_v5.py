"""Frozen PRI01-MEM metadata acceptance; actual MEM/Intake on fresh memory DBs."""
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.contracts_v5 import Grant, Limits, Result, dumps
from pal.intake_v5 import IntakeStore
from pal.memory_v5 import MemoryStore
from pal.sanitize import sanitize


class InterruptConnection(sqlite3.Connection):
    interrupt = False

    def execute(self, sql, parameters=()):
        if self.interrupt and sql.lstrip().upper().startswith('SELECT'):
            raise KeyboardInterrupt()
        return super().execute(sql, parameters)


class MemoryPrimaryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None, factory=InterruptConnection)
        self.addCleanup(self.conn.close)
        self.number = 0
        self.calls = []
        self.bind()

    def identifier(self, kind):
        self.number += 1
        return f'{kind}-{self.number}'

    def bind(self):
        def gate(conn, refs):
            self.calls.append('gate')
            return self.mem.source_gate(conn, refs)
        self.intake = IntakeStore(self.conn, host_grant=Grant(('read',), (), Limits(5, 5, 5)),
                                  expert_id='mock', source_gate=gate, id_factory=self.identifier)
        def event(conn, request):
            self.calls.append('event')
            return self.intake.append_event(conn, request)
        def invalidate(conn, **request):
            self.calls.append('invalidate')
            return self.intake.invalidate_by_refs(conn, **request)
        def clean(text):
            self.calls.append('sanitize')
            return sanitize(text)
        self.mem = MemoryStore(self.conn, sanitize_text=clean, append_event=event,
                               invalidate_by_refs=invalidate, id_factory=self.identifier,
                               clock=lambda: '2026-10-10T00:00:00+00:00')

    def append(self, key, session='日本語', role='user'):
        result = self.mem.append({'client_key': key, 'session_id': session, 'role': role,
                                  'text': 'BODY_SENTINEL_' + key})
        self.assertTrue(result.ok, result)
        return result.value.to_json()['record_ref']

    def stop(self, ref, key='停止'):
        result = self.mem.stop_reference({'key': key, 'source_ref': ref}, session_id='initiator')
        self.assertTrue(result.ok, result)
        return result

    def snapshot(self):
        return '\n'.join(self.conn.iterdump())

    def read_only(self, operation):
        before, changes, calls = self.snapshot(), self.conn.total_changes, list(self.calls)
        trace = []
        self.conn.set_trace_callback(trace.append)
        try:
            result = operation()
        finally:
            self.conn.set_trace_callback(None)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.conn.total_changes, changes)
        self.assertEqual(self.calls, calls)
        self.assertFalse(any(s.lstrip().upper().startswith(('BEGIN', 'COMMIT', 'ROLLBACK',
                                                           'SAVEPOINT', 'INSERT', 'UPDATE', 'DELETE'))
                             for s in trace), trace)
        return result

    def failure(self, result, code):
        self.assertIs(type(result), Result)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code.value, code)
        self.assertNotIn('BODY_SENTINEL', dumps(result))
        self.assertLessEqual(len(result.error.message), 200)

    def recent(self, limit=2):
        return self.mem.list_recent({'session_id': '日本語', 'limit': limit})

    def lookup(self, key='停止'):
        return self.mem.get_stop_reference_by_key({'key': key})

    def test_recent_empty_closed_projection(self):
        result = self.read_only(self.recent)
        self.assertTrue(result.ok)
        self.assertEqual(result.value.to_json(), {'record_refs': [], 'truncated': False})

    def test_recent_order_roles_session_and_stopped_filter_before_limit(self):
        old = self.append('old')
        middle = self.append('middle', role='assistant')
        self.append('other', session='other')
        stopped = self.append('stopped')
        self.stop(stopped)
        new = self.append('new')
        result = self.read_only(self.recent)
        self.assertEqual(result.value.to_json(), {'record_refs': [new, middle], 'truncated': True})
        self.assertEqual(self.recent(3).value.to_json(),
                         {'record_refs': [new, middle, old], 'truncated': False})
        self.assertNotIn('BODY_SENTINEL', dumps(result))

    def test_recent_strict_inputs_and_utf8(self):
        self.append('record')
        for request in (None, [], {}, {'session_id': '日本語'},
                        {'session_id': '', 'limit': 1}, {'session_id': '\ud800', 'limit': 1},
                        {'session_id': 1, 'limit': 1}, {'session_id': '日本語', 'limit': True},
                        {'session_id': '日本語', 'limit': 0}, {'session_id': '日本語', 'limit': 51},
                        {'session_id': '日本語', 'limit': 1.0},
                        {'session_id': '日本語', 'limit': 1, 'query': 'BODY_SENTINEL'}):
            with self.subTest(request=repr(request)):
                self.failure(self.read_only(lambda: self.mem.list_recent(request)), 'invalid_input')

    def test_recent_bound_fifty_and_exact_truncation(self):
        refs = [self.append(str(i)) for i in range(51)]
        self.assertEqual(self.read_only(lambda: self.recent(50)).value.to_json(),
                         {'record_refs': list(reversed(refs[1:])), 'truncated': True})
        self.stop(refs[0])
        self.assertFalse(self.recent(50).value.to_json()['truncated'])

    def test_reads_preserve_caller_transaction_and_uncommitted_rows(self):
        ref = self.append('record')
        original = self.stop(ref)
        self.conn.execute('BEGIN IMMEDIATE')
        self.conn.execute('UPDATE v5_mem_record SET usable=1 WHERE id=?', (ref['id'],))
        self.assertEqual(self.read_only(self.recent).value.to_json()['record_refs'], [ref])
        self.assertEqual(self.read_only(self.lookup), original)
        self.assertTrue(self.conn.in_transaction)
        self.conn.execute('ROLLBACK')
        self.assertEqual(self.recent().value.to_json()['record_refs'], [])

    def test_lookup_original_receipt_after_later_stop_and_reopen(self):
        first = self.append('first')
        receipt = self.stop(first)
        self.stop(self.append('later'), key='later-stop')
        new = sqlite3.connect(':memory:', isolation_level=None, factory=InterruptConnection)
        self.conn.backup(new)
        self.conn.close()
        self.conn = new
        self.addCleanup(new.close)
        self.bind()
        self.assertEqual(self.read_only(self.lookup), receipt)
        self.assertEqual(self.read_only(self.lookup), receipt)
        self.failure(self.mem.read({'ref': first}, purpose='model_context'), 'denied')

    def test_lookup_missing_and_strict_inputs(self):
        self.failure(self.read_only(self.lookup), 'not_found')
        for request in (None, [], {}, {'key': ''}, {'key': '\ud800'}, {'key': 1},
                        {'key': '停止', 'session_id': 'invented'}):
            with self.subTest(request=repr(request)):
                self.failure(self.read_only(lambda: self.mem.get_stop_reference_by_key(request)),
                             'invalid_input')

    def corrupt_lookup(self, sql, parameters=()):
        ref = self.append('source')
        self.stop(ref)
        self.conn.execute(sql, parameters or (ref['id'],))
        self.failure(self.read_only(self.lookup), 'unavailable')

    def test_lookup_corrupt_input_and_initiating_session(self):
        ref = self.append('source')
        self.stop(ref)
        original = self.conn.execute("SELECT input_json FROM v5_mem_replay WHERE command='C05.stop_reference'").fetchone()[0]
        for value in ('{', dumps({'key': '停止', 'source_ref': ref}),
                      dumps({'key': '停止', 'source_ref': ref, 'session_id': ''}),
                      dumps({'key': 'wrong', 'source_ref': ref, 'session_id': 'initiator'})):
            self.conn.execute("UPDATE v5_mem_replay SET input_json=? WHERE command='C05.stop_reference'", (value,))
            self.failure(self.read_only(self.lookup), 'unavailable')
        self.conn.execute("UPDATE v5_mem_replay SET input_json=? WHERE command='C05.stop_reference'", (original,))
        self.assertTrue(self.lookup().ok)

    def test_lookup_corrupt_result_shape_ref_and_binding(self):
        ref = self.append('source')
        other = self.append('other')
        self.stop(ref)
        for value in ('{', dumps({'affected_refs': []}), dumps({'affected_refs': [other]}),
                      dumps({'affected_refs': [{'kind': 'artifact', 'id': ref['id']}]}),
                      dumps({'affected_refs': [ref], 'extra': True})):
            self.conn.execute("UPDATE v5_mem_replay SET result_json=? WHERE command='C05.stop_reference'", (value,))
            self.failure(self.read_only(self.lookup), 'unavailable')

    def test_lookup_missing_source_body(self):
        self.corrupt_lookup('DELETE FROM v5_mem_record WHERE id=?')

    def test_lookup_wrong_command_cannot_return_append_receipt(self):
        ref = self.append('停止')
        self.failure(self.read_only(self.lookup), 'not_found')
        self.stop(ref)
        self.assertEqual(self.lookup().value.to_json(), {'affected_refs': [ref]})

    def test_sqlite_error_and_baseexception_preserve_transaction(self):
        self.append('record')
        self.conn.execute('BEGIN')
        self.conn.interrupt = True
        for operation in (self.recent, self.lookup):
            with self.assertRaises(KeyboardInterrupt): operation()
            self.assertTrue(self.conn.in_transaction)
        self.conn.interrupt = False
        self.conn.execute('ROLLBACK')
        self.failure(self.read_only(lambda: self.mem.list_recent({'session_id': '', 'limit': 1})),
                     'invalid_input')
        self.conn.execute('DROP TABLE v5_mem_record')
        self.failure(self.read_only(self.recent), 'unavailable')

    def test_lookup_sqlite_failure_is_unavailable_and_readonly(self):
        self.stop(self.append('source'))
        self.conn.execute('DROP TABLE v5_mem_replay')
        self.conn.execute('BEGIN')
        self.failure(self.read_only(self.lookup), 'unavailable')
        self.assertTrue(self.conn.in_transaction)
        self.conn.execute('ROLLBACK')
