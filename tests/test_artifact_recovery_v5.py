"""RECOVERY02 ART protocol acceptance, actual fresh ART with trusted callback fixtures."""
import copy
import hashlib
from pathlib import Path
import sqlite3
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore, artifact_save_key
from pal.contracts_v5 import Ref, Result, dumps, parse_model_action


class FaultConnection(sqlite3.Connection):
    fault = None
    def execute(self, sql, parameters=()):
        if self.fault and sql.lstrip().upper().startswith('SELECT'):
            raise self.fault('PRIVATE_DIAGNOSTIC')
        return super().execute(sql, parameters)


_DEFAULT = object()


class ArtifactRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None, factory=FaultConnection)
        self.addCleanup(self.conn.close)
        self.refs = [{'kind': 'record', 'id': 'r1'}, {'kind': 'record', 'id': 'r2'}]
        self.work = {'goal_id': 'goal:日本語', 'revision': 1, 'epoch': 4}
        self.action = {'kind': 'compose', 'content': '本文😀\n\r\n',
                       'media_type': 'text/markdown', 'source_refs': self.refs[:1] * 2}
        self.calls = []
        self.mode = 'available'
        self.store = ArtifactStore(self.conn, authorize_save=self.authorize, source_gate=self.gate,
                                   id_factory=self.identifier, clock=self.clock)
        self.request = {'key': artifact_save_key(self.work, 'step'), 'work_ref': self.work,
                        'step_id': 'step', 'action': self.action}

    def authorize(self, conn, request):
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        self.assertEqual(request, {'work_ref': self.work, 'step_id': 'step', 'action': self.action})
        self.calls.append('authorize')
        return Result.success({'source_refs': self.refs})

    def identifier(self, prefix):
        self.calls.append('id')
        return 'artifact'

    def clock(self):
        self.calls.append('clock')
        return '2026-10-10T00:00:00+00:00'

    def gate(self, conn, refs):
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        self.assertIs(type(refs), tuple)
        self.assertEqual(refs, tuple(Ref.from_json(r) for r in self.refs))
        self.calls.append('gate')
        if self.mode == 'write':
            conn.execute('INSERT INTO caller VALUES (99)')
            return 'available'
        if self.mode == 'commit':
            conn.commit()
            return 'available'
        if isinstance(self.mode, type) and issubclass(self.mode, BaseException):
            raise self.mode('PRIVATE_DIAGNOSTIC')
        return self.mode

    def save(self):
        action = parse_model_action(dumps(self.action),
                                    allowed_refs=[Ref.from_json(r) for r in self.refs]).to_json()
        request = {k: v for k, v in self.request.items() if k != 'action'}
        request.update({k: v for k, v in action.items() if k != 'kind'})
        result = self.store.save(request)
        self.assertTrue(result.ok, result)
        return result.value.to_json()

    def lookup(self, request=_DEFAULT):
        return self.store.lookup_saved(self.conn, self.request if request is _DEFAULT else request)

    def begin(self):
        self.conn.execute('CREATE TABLE caller (value)')
        self.conn.execute('BEGIN IMMEDIATE')
        self.conn.execute('INSERT INTO caller VALUES (7)')
        self.conn.execute('SAVEPOINT caller_owned')

    def failure(self, result, code):
        self.assertIs(type(result), Result)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code.value, code)
        self.assertNotIn('PRIVATE_DIAGNOSTIC', dumps(result))
        self.assertNotIn(self.action['content'], dumps(result))

    def readonly(self, request=_DEFAULT):
        before = '\n'.join(self.conn.iterdump())
        changes = self.conn.total_changes
        calls = len(self.calls)
        result = self.lookup(request)
        self.assertEqual('\n'.join(self.conn.iterdump()), before)
        self.assertEqual(self.conn.total_changes, changes)
        self.assertTrue(self.conn.in_transaction)
        self.assertTrue(all(c == 'gate' for c in self.calls[calls:]))
        return result

    def test_save_key_exact_frozen_identity_and_validation(self):
        self.assertEqual(artifact_save_key({'epoch': 4, 'revision': 1, 'goal_id': 'goal:日本語'}, 'step'),
                         '["C08.save",{"epoch":4,"goal_id":"goal:日本語","revision":1},"step"]')
        self.assertEqual(self.request['key'], dumps(['C08.save', self.work, 'step']))
        for work, step in (({**self.work, 'epoch': True}, 'step'), (self.work, ''),
                           (self.work, '\ud800')):
            with self.assertRaises(ValueError): artifact_save_key(work, step)

    def test_exact_full_producer_projection_no_body_or_authorize(self):
        receipt = self.save()
        self.begin()
        result = self.readonly()
        self.assertTrue(result.ok)
        self.assertEqual(result.value.to_json(), {**receipt, 'work_ref': self.work,
                                                 'step_id': 'step', 'source_refs': self.refs})
        self.assertNotIn('content', result.value.to_json())
        self.assertEqual(receipt['hash'], hashlib.sha256(self.action['content'].encode()).hexdigest())

    def test_definitive_absence_requires_no_body_for_step(self):
        self.begin()
        self.failure(self.readonly(), 'not_found')

    def test_body_without_expected_key_is_unavailable(self):
        self.save()
        self.conn.execute('DELETE FROM v5_art_replay')
        self.begin()
        self.failure(self.readonly(), 'unavailable')

    def test_dangling_receipt_is_unavailable(self):
        self.save()
        self.conn.execute('DELETE FROM v5_art_body')
        self.begin()
        self.failure(self.readonly(), 'unavailable')

    def test_foreign_body_step_work_binding_is_unavailable(self):
        self.save()
        self.begin()
        for column, value in (('step_id', 'foreign'), ('work_json', dumps({**self.work, 'epoch': 3}))):
            self.conn.execute('SAVEPOINT corrupt')
            self.conn.execute('UPDATE v5_art_body SET ' + column + '=?', (value,))
            self.failure(self.readonly(), 'unavailable')
            self.conn.execute('ROLLBACK TO corrupt')
            self.conn.execute('RELEASE corrupt')

    def test_changed_content_media_order_duplicates_conflict(self):
        self.save()
        self.begin()
        for delta in ({'content': 'changed'}, {'media_type': 'text/plain'},
                      {'source_refs': self.refs[:1]}, {'source_refs': self.refs},
                      {'source_refs': list(reversed(self.refs))},
                      {'source_refs': self.refs[:1] * 3}, {'source_refs': []}):
            request = copy.deepcopy(self.request)
            request['action'].update(delta)
            self.failure(self.readonly(request), 'conflict')
        self.assertTrue(self.readonly().ok)

    def test_strict_closed_lookup_inputs(self):
        self.save()
        self.begin()
        bad = [None, [], {}, {**self.request, 'extra': 1}, {**self.request, 'key': ''},
               {**self.request, 'step_id': '\ud800'},
               {**self.request, 'work_ref': {**self.work, 'epoch': True}}]
        for action in ({**self.action, 'extra': True}, {**self.action, 'content': '\ud800'},
                       {**self.action, 'source_refs': True}, {'kind': 'report', 'text': 'x'}):
            bad.append({**self.request, 'action': action})
        for request in bad:
            with self.subTest(request=repr(request)):
                self.failure(self.readonly(request), 'invalid_input')

    def test_wrong_idle_and_non_autocommit_connection_refuse(self):
        with self.assertRaises(ValueError): self.lookup()
        other = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(other.close)
        other.execute('BEGIN')
        with self.assertRaises(ValueError): self.store.lookup_saved(other, self.request)
        self.conn.execute('BEGIN')
        self.conn.isolation_level = ''
        with self.assertRaises(ValueError): self.lookup()

    def test_immutable_bytes_hash_length_utf8_metadata_and_receipt_corruption(self):
        self.save()
        self.begin()
        mutations = [('v5_art_body', 'body', b'changed'), ('v5_art_body', 'body', b'\xff'),
                     ('v5_art_body', 'hash', '0' * 64), ('v5_art_body', 'byte_count', 999),
                     ('v5_art_body', 'media_type', 'text/html'),
                     ('v5_art_body', 'binding_json', '{}'),
                     ('v5_art_body', 'sources_json', '[]'),
                     ('v5_art_replay', 'result_json', '{}'),
                     ('v5_art_replay', 'artifact_id', 'foreign')]
        for table, column, value in mutations:
            with self.subTest(column=column, value=repr(value)):
                self.conn.execute('SAVEPOINT corrupt')
                self.conn.execute('UPDATE ' + table + ' SET ' + column + '=?', (value,))
                self.failure(self.readonly(), 'unavailable')
                self.conn.execute('ROLLBACK TO corrupt')
                self.conn.execute('RELEASE corrupt')

    def test_noncanonical_stored_input_is_conflict(self):
        self.save()
        self.conn.execute("UPDATE v5_art_replay SET input_json='{}'")
        self.begin()
        self.failure(self.readonly(), 'conflict')

    def test_gate_denied_missing_unavailable_and_malformed(self):
        self.save()
        self.begin()
        for state, expected in (('denied', 'denied'), ('not_found', 'unavailable'),
                                ('unavailable', 'unavailable'), (None, 'unavailable'),
                                (RuntimeError, 'unavailable')):
            self.mode = state
            self.failure(self.readonly(), expected)

    def test_mutating_gate_rolls_back_only_owned_savepoint(self):
        self.save()
        self.begin()
        self.mode = 'write'
        before = '\n'.join(self.conn.iterdump())
        self.failure(self.lookup(), 'unavailable')
        self.assertEqual('\n'.join(self.conn.iterdump()), before)
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(self.conn.execute('SELECT * FROM caller').fetchall(), [(7,)])
        self.conn.execute('RELEASE caller_owned')
        with self.assertRaises(sqlite3.OperationalError): self.conn.execute('RELEASE v5_art_callback')

    def test_committing_gate_reports_unavailable_without_false_rollback(self):
        self.save()
        self.begin()
        self.mode = 'commit'
        self.failure(self.lookup(), 'unavailable')
        self.assertFalse(self.conn.in_transaction)
        self.assertEqual(self.conn.execute('SELECT * FROM caller').fetchall(), [(7,)])

    def test_baseexception_cleans_owned_savepoint_preserving_caller(self):
        self.save()
        self.begin()
        for failure in (KeyboardInterrupt, SystemExit):
            self.mode = failure
            with self.assertRaises(failure): self.lookup()
            self.assertTrue(self.conn.in_transaction)
            self.assertEqual(self.conn.execute('SELECT * FROM caller').fetchall(), [(7,)])
            with self.assertRaises(sqlite3.OperationalError): self.conn.execute('RELEASE v5_art_callback')
        self.conn.execute('RELEASE caller_owned')

    def test_sqlite_read_failure_is_bounded_and_preserves_transaction(self):
        self.save()
        self.begin()
        self.conn.fault = sqlite3.OperationalError
        self.failure(self.lookup(), 'unavailable')
        self.conn.fault = None
        self.assertTrue(self.conn.in_transaction)
        self.conn.execute('RELEASE caller_owned')
