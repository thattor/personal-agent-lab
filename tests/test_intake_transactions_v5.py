"""TSK-owned notifications and source invalidation in a caller-owned transaction."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.contracts_v5 import Grant, Limits, Ref, dumps
from pal.intake_v5 import IntakeStore


class IntakeTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'scope.sqlite'
        self.conn = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(self.conn.close)
        self.grant = Grant(('read',), ('sample/repo',), Limits(2, 3, 4))
        self.store = IntakeStore(self.conn, host_grant=self.grant, expert_id='expert',
                                 source_gate=lambda conn, refs: 'available')

    def create(self, key='create', origin='origin', context='context'):
        request = {'key': key, 'session_id': 'session',
                   'origin_record_ref': {'kind': 'record', 'id': origin},
                   'brief': {'purpose': 'prepare', 'target': {'repository': 'sample/repo',
                           'issue_numbers': [], 'files': []}, 'constraints': [],
                           'conditions': [{'description': 'save', 'check': 'artifact_saved'}],
                           'context_refs': [{'kind': 'record', 'id': context}]}}
        result = self.store.create(request, request_scope=self.grant)
        self.assertTrue(result.ok)
        return request, result.value.to_json()['work_ref']

    def event(self, key='event'):
        return {'key': key, 'session_id': 'session', 'kind': 'state', 'text': '', 'refs': []}

    def snapshot(self):
        return '\n'.join(self.conn.iterdump())

    def test_public_event_replay_is_transaction_bound_and_rollback_owned_by_caller(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.store.append_event(self.conn, self.event())
        self.conn.execute('BEGIN IMMEDIATE')
        first = self.store.append_event(self.conn, self.event())
        self.assertTrue(first.ok)
        self.assertEqual(first, self.store.append_event(self.conn, self.event()))
        changed = self.event()
        changed['text'] = 'different'
        self.assertEqual(self.store.append_event(self.conn, changed).error.code.value, 'conflict')
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_intake_event').fetchone()[0], 1)
        self.conn.execute('ROLLBACK')
        self.assertEqual(self.snapshot(), before)

    def test_event_strict_wire_and_current_work_binding(self):
        _, work = self.create()
        self.conn.execute('BEGIN IMMEDIATE')
        for field, value in [('extra', True), ('kind', 'invented'), ('text', False),
                             ('refs', {}), ('work_ref', None)]:
            with self.subTest(field=field):
                bad = self.event()
                bad[field] = value
                self.assertEqual(self.store.append_event(self.conn, bad).error.code.value,
                                 'invalid_input')
        event = self.event()
        event['work_ref'] = dict(work, epoch=1)
        self.assertEqual(self.store.append_event(self.conn, event).error.code.value, 'stale')
        event['work_ref'] = work
        self.assertTrue(self.store.append_event(self.conn, event).ok)
        self.conn.execute('COMMIT')

    def test_create_registers_all_sources_and_invalidation_preserves_receipt(self):
        request, old = self.create(context='origin')
        refs = self.conn.execute('SELECT kind,id FROM v5_intake_source').fetchall()
        self.assertEqual(refs, [('record', 'origin')])
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.store.invalidate_by_refs(self.conn, key='stop', session_id='control',
                                               refs=(Ref('record', 'origin'),))
        self.assertTrue(result.ok)
        new = dict(old, epoch=1)
        self.assertEqual(result.value.to_json(), {'work_refs': [new]})
        self.assertEqual(result, self.store.invalidate_by_refs(
            self.conn, key='stop', session_id='control', refs=(Ref('record', 'origin'),)))
        self.conn.execute('COMMIT')
        current = self.store.get_work({'goal_id': old['goal_id']}).value.to_json()
        self.assertEqual(current['work_ref'], new)
        self.assertEqual(current['state'], 'queued')
        replay = self.store.create(request, request_scope=self.grant)
        self.assertEqual(replay.value.to_json()['work_ref'], old)
        row = self.conn.execute("SELECT session_id,work_ref_json FROM v5_intake_event WHERE kind='state'").fetchone()
        self.assertEqual(row, ('control', dumps(new)))

    def test_invalidation_prechecks_all_states_and_caller_can_rollback(self):
        _, one = self.create('one')
        _, two = self.create('two')
        self.conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=?', ('running', two['goal_id']))
        before = self.snapshot()
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.store.invalidate_by_refs(self.conn, key='stop', session_id='session',
                                               refs=(Ref('record', 'context'),))
        self.assertEqual(result.error.code.value, 'unavailable')
        self.conn.execute('ROLLBACK')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.store.get_work({'goal_id': one['goal_id']}).value.to_json()['work_ref'], one)

    def test_missing_source_coverage_is_unavailable_instead_of_silent_miss(self):
        self.create()
        self.conn.execute('DELETE FROM v5_intake_source')
        before = self.snapshot()
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.store.invalidate_by_refs(self.conn, key='stop', session_id='s',
                                               refs=(Ref('record', 'origin'),))
        self.assertEqual(result.error.code.value, 'unavailable')
        self.conn.execute('ROLLBACK')
        self.assertEqual(self.snapshot(), before)

    def test_invalidating_one_source_does_not_touch_unrelated_work(self):
        _, affected = self.create('one')
        _, other = self.create('two', origin='other-origin', context='other-context')
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.store.invalidate_by_refs(self.conn, key='opaque:key', session_id='s',
                                               refs=(Ref('record', 'context'), Ref('record', 'context')))
        self.assertEqual(result.value.to_json()['work_refs'], [dict(affected, epoch=1)])
        conflict = self.store.invalidate_by_refs(self.conn, key='opaque:key', session_id='s',
                                                 refs=(Ref('record', 'other-context'),))
        self.assertEqual(conflict.error.code.value, 'conflict')
        self.conn.execute('COMMIT')
        self.assertEqual(self.store.get_work({'goal_id': other['goal_id']}).value.to_json()['work_ref'], other)

    def test_epoch_overflow_and_foreign_transaction_rejected(self):
        _, work = self.create()
        self.conn.execute('UPDATE v5_intake_work SET epoch=?', (2**63-1,))
        other = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(other.close)
        other.execute('BEGIN')
        with self.assertRaises(ValueError):
            self.store.append_event(other, self.event())
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.store.invalidate_by_refs(self.conn, key='stop', session_id='s', refs=(Ref('record', 'origin'),))
        self.assertEqual(result.error.code.value, 'unavailable')
        self.conn.execute('ROLLBACK')


if __name__ == '__main__':
    unittest.main()
