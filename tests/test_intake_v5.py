"""Synthetic TSK01/1 acceptance, using only caller-owned temporary databases."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.contracts_v5 import Brief, Grant, Limits, Ref, Result, dumps, loads
from pal.intake_v5 import IntakeStore


def grant(capabilities=('read', 'other'), repositories=('synthetic/repo',), limits=(5, 6, 7)):
    return Grant(capabilities, repositories, Limits(*limits))


def request(key='key'):
    return {'key': key, 'session_id': 'session',
            'origin_record_ref': {'kind': 'record', 'id': 'origin'},
            'brief': {'purpose': '日本語の要約',
                      'target': {'repository': 'synthetic/repo', 'issue_numbers': [0, 7],
                                 'files': [{'path': '', 'ref': 'branch'}]},
                      'constraints': ['', 'do not send'],
                      'conditions': [{'description': '', 'check': 'semantic'},
                                     {'description': 'save', 'check': 'artifact_saved'}],
                      'context_refs': [{'kind': 'source', 'id': 'source'}]}}


_DEFAULT_REQUEST = object()


class IntakeV5Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'intake.sqlite'
        self.conn = self.connect()
        self.conn.execute('CREATE TABLE synthetic_source(kind TEXT, id TEXT, stopped INTEGER)')
        self.conn.executemany('INSERT INTO synthetic_source VALUES (?, ?, 0)',
                              [('record', 'origin'), ('source', 'source')])
        self.calls = []
        self.scope = grant()
        self.store = self.make_store()

    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(connection.close)
        return connection

    def gate(self, connection, refs):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.assertIs(type(refs), tuple)
        self.assertTrue(all(type(ref) is Ref for ref in refs))
        self.calls.append(refs)
        for ref in refs:
            row = connection.execute('SELECT stopped FROM synthetic_source WHERE kind=? AND id=?',
                                     (ref.kind.value, ref.id)).fetchone()
            if row is None:
                return 'not_found'
            if row[0]:
                return 'denied'
        return 'available'

    def make_store(self, **options):
        values = dict(host_grant=grant(), expert_id='expert', source_gate=self.gate)
        values.update(options)
        return IntakeStore(self.conn, **values)

    def create(self, data=_DEFAULT_REQUEST, **options):
        return self.store.create(request() if data is _DEFAULT_REQUEST else data,
                                 request_scope=options.get('scope', self.scope))

    def snapshot(self):
        return {name: self.conn.execute('SELECT * FROM ' + name + ' ORDER BY rowid').fetchall()
                for name in ('v5_intake_work', 'v5_intake_event', 'v5_intake_replay')}

    def assertFailure(self, result, code):
        self.assertIs(type(result), Result)
        data = result.to_json()
        self.assertEqual(set(data), {'ok', 'error'})
        self.assertIs(data['ok'], False)
        self.assertEqual(data['error']['code'], code)
        self.assertEqual(set(data['error']), {'code', 'message', 'refs'})
        self.assertLessEqual(len(data['error']['message']), 200)
        self.assertNotIn('SENTINEL', dumps(result))
        self.assertEqual(data['error']['refs'], [])
        self.assertFalse(self.conn.in_transaction)

    def test_durable_formal_brief_bindings_event_and_exact_schemas(self):
        original = request()
        result = self.create(original)
        self.assertTrue(result.ok)
        created = result.value.to_json()
        self.assertEqual(set(created), {'work_ref', 'expert_id', 'state', 'grant'})
        self.assertEqual(created['expert_id'], 'expert')
        self.assertEqual(created['state'], 'queued')
        self.assertEqual(created['work_ref']['revision'], 1)
        self.assertEqual(created['work_ref']['epoch'], 0)
        self.conn.close()
        self.conn = self.connect()
        self.store = self.make_store()
        view = self.store.get_work({'goal_id': created['work_ref']['goal_id']}).value.to_json()
        self.assertEqual(set(view), {'work_ref', 'brief', 'grant', 'state',
                                    'current_artifact_refs', 'open_questions'})
        self.assertEqual(view['work_ref'], created['work_ref'])
        self.assertEqual(view['grant'], created['grant'])
        self.assertEqual(view['current_artifact_refs'], [])
        self.assertEqual(view['open_questions'], [])
        formal = Brief.from_json(view['brief'])
        self.assertEqual(len({x.id for x in formal.conditions}), 2)
        wire = formal.to_json()
        for condition in wire['conditions']:
            self.assertTrue(condition.pop('id'))
        self.assertEqual(wire, original['brief'])
        row = self.conn.execute('SELECT session_id, origin_ref_json, expert_id FROM v5_intake_work').fetchone()
        self.assertEqual(row, ('session', dumps(original['origin_record_ref']), 'expert'))
        event = self.conn.execute('SELECT session_id, work_ref_json, kind FROM v5_intake_event').fetchall()
        self.assertEqual(event, [('session', dumps(created['work_ref']), 'accepted')])
        self.assertEqual(len(self.snapshot()['v5_intake_replay']), 1)

    def test_grant_intersection_request_order_duplicates_zero_and_constraints(self):
        self.store = self.make_store(host_grant=grant(('b', 'a'), ('synthetic/repo', 'r2'), (0, 4, 8)))
        scope = grant(('a', 'c', 'b', 'a'), ('r2', 'synthetic/repo', 'r2', 'outside'), (3, 0, 2))
        result = self.create(scope=scope)
        expected = grant(('a', 'b'), ('r2', 'synthetic/repo'), (0, 0, 2)).to_json()
        self.assertEqual(result.value.to_json()['grant'], expected)
        view = self.store.get_work({'goal_id': result.value.to_json()['work_ref']['goal_id']}).value.to_json()
        self.assertEqual(view['grant'], expected)
        self.assertEqual(view['brief']['constraints'], request()['brief']['constraints'])
        zero = self.create(request('zero'), scope=grant((), limits=(0, 0, 0)))
        self.assertTrue(zero.ok)
        self.assertEqual(zero.value.to_json()['grant'], grant((), limits=(0, 0, 0)).to_json())

    def test_target_denial_has_no_effect_and_failed_key_can_retry(self):
        before = self.snapshot()
        self.assertFailure(self.create(scope=grant(repositories=())), 'denied')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.create().ok)

    def test_gate_inside_reserved_transaction_before_intake_write_with_all_refs(self):
        trace = []
        self.conn.set_trace_callback(trace.append)
        def observed_gate(conn, refs):
            self.assertTrue(any(sql == 'BEGIN IMMEDIATE' for sql in trace))
            self.assertFalse(any(sql.startswith('INSERT INTO v5_intake_') for sql in trace))
            other = self.connect()
            with self.assertRaises(sqlite3.OperationalError):
                other.execute('BEGIN IMMEDIATE')
            return self.gate(conn, refs)
        self.store = self.make_store(source_gate=observed_gate)
        trace.clear()
        self.assertTrue(self.create().ok)
        self.assertEqual(self.calls, [(Ref('record', 'origin'), Ref('source', 'source'))])
        self.assertEqual(sum(sql == 'COMMIT' for sql in trace), 1)
        self.assertFalse(self.conn.in_transaction)

    def test_missing_and_stopped_sources_reject_then_repair_allows_same_key(self):
        for state, expected in [('missing', 'not_found'), ('stopped', 'denied')]:
            with self.subTest(state=state):
                self.conn.execute('DELETE FROM synthetic_source WHERE id="source"')
                if state == 'stopped':
                    self.conn.execute('INSERT INTO synthetic_source VALUES ("source", "source", 1)')
                before = self.snapshot()
                data = request(state)
                self.assertFailure(self.create(data), expected)
                self.assertEqual(self.snapshot(), before)
                self.conn.execute('DELETE FROM synthetic_source WHERE id="source"')
                self.conn.execute('INSERT INTO synthetic_source VALUES ("source", "source", 0)')
                self.assertTrue(self.create(data).ok)

    def test_gate_failures_and_transaction_control_leave_no_intake_effects(self):
        class StringSubclass(str):
            pass
        def raising(conn, refs):
            raise RuntimeError('SENTINEL' * 1000)
        def commit(conn, refs):
            conn.commit()
            return 'available'
        def rollback(conn, refs):
            conn.rollback()
            return 'available'
        def restart(conn, refs):
            conn.commit()
            conn.execute('BEGIN IMMEDIATE')
            return 'available'
        gates = [raising, commit, rollback, restart,
                 lambda conn, refs: None, lambda conn, refs: [],
                 lambda conn, refs: 'SENTINEL' * 1000,
                 lambda conn, refs: StringSubclass('available'),
                 lambda conn, refs: 'unavailable']
        for i, gate in enumerate(gates):
            with self.subTest(gate=i):
                self.store = self.make_store(source_gate=gate)
                before = self.snapshot()
                self.assertFailure(self.create(), 'unavailable')
                self.assertEqual(self.snapshot(), before)
        self.store = self.make_store()
        self.assertTrue(self.create().ok)

    def test_replay_after_reopen_stop_and_changed_host_returns_original_without_callbacks(self):
        first = self.create()
        before = self.snapshot()
        self.conn.close()
        self.conn = self.connect()
        self.conn.execute('UPDATE synthetic_source SET stopped=1')
        def forbidden(*args):
            self.fail('replay must not call gate or id factory')
        self.store = self.make_store(host_grant=grant((), (), (0, 0, 0)),
                                    expert_id='changed', source_gate=forbidden, id_factory=forbidden)
        reordered = dict(reversed(list(request().items())))
        reordered['brief'] = dict(reversed(list(reordered['brief'].items())))
        self.assertEqual(self.create(reordered), first)
        self.assertEqual(self.snapshot(), before)

    def test_replay_compares_original_scope_and_every_request_field(self):
        self.assertTrue(self.create().ok)
        before = self.snapshot()
        changed = []
        for key, value in [('session_id', 'other'), ('origin_record_ref', {'kind': 'record', 'id': 'other'})]:
            data = request(); data[key] = value; changed.append(data)
        for field, value in [('purpose', 'changed'), ('conditions', list(reversed(request()['brief']['conditions']))),
                             ('constraints', list(reversed(request()['brief']['constraints']))),
                             ('context_refs', [])]:
            data = request(); data['brief'][field] = value; changed.append(data)
        for data in changed:
            self.assertFailure(self.create(data), 'conflict')
        # Same intersection, different original scope: duplicates/excess rights are still input.
        for scope in [grant(('read', 'other', 'read')), grant(('read', 'other', 'outside')),
                      grant(limits=(99, 6, 7))]:
            self.assertFailure(self.create(scope=scope), 'conflict')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.calls), 1)

    def test_mid_event_abort_preserves_existing_data_and_retry_is_fresh(self):
        self.assertTrue(self.create(request('previous')).ok)
        before = self.snapshot()
        seen_work = []
        counter = 0
        def fail_event(prefix):
            nonlocal counter
            counter += 1
            if prefix == 'event':
                seen_work.append(self.conn.execute('SELECT count(*) FROM v5_intake_work').fetchone()[0])
                raise RuntimeError('SENTINEL abort after insert')
            return f'new-{prefix}-{counter}'
        self.store = self.make_store(id_factory=fail_event)
        self.assertFailure(self.create(), 'unavailable')
        self.assertEqual(seen_work, [2])
        self.assertEqual(self.snapshot(), before)
        self.store = self.make_store()
        self.assertTrue(self.create().ok)
        self.assertEqual({name: len(rows) for name, rows in self.snapshot().items()},
                         {name: 2 for name in before})

    def test_host_id_collisions_and_invalid_ids_roll_back(self):
        first = self.create(request('previous')).value.to_json()
        event_id = self.conn.execute('SELECT event_id FROM v5_intake_event').fetchone()[0]
        counter = 0
        def factory_for(collision):
            def factory(prefix):
                nonlocal counter
                counter += 1
                if collision == 'condition' and prefix == 'condition':
                    return 'same-condition'
                if collision == 'goal' and prefix == 'goal':
                    return first['work_ref']['goal_id']
                if collision == 'event' and prefix == 'event':
                    return event_id
                if collision == 'invalid' and prefix == 'event':
                    return '\ud800'
                return f'{prefix}-{counter}'
            return factory
        before = self.snapshot()
        for kind in ('condition', 'goal', 'event', 'invalid'):
            with self.subTest(kind=kind):
                self.store = self.make_store(id_factory=factory_for(kind))
                self.assertFailure(self.create(), 'unavailable')
                self.assertEqual(self.snapshot(), before)
        self.store = self.make_store()
        self.assertTrue(self.create().ok)

    def test_busy_writer_returns_unavailable_without_effects(self):
        other = self.connect()
        before = self.snapshot()
        other.execute('BEGIN IMMEDIATE')
        self.assertFailure(self.create(), 'unavailable')
        other.rollback()
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.create().ok)

    def test_strict_create_input_rejection_precedes_any_gate_or_write(self):
        cases = [None, [], '{}']
        for key in request():
            data = request(); del data[key]; cases.append(data)
        for key, value in [('extra', 'SENTINEL'), ('key', ''), ('key', True),
                           ('session_id', '\ud800'), ('origin_record_ref', {'kind': 'source', 'id': 'source'})]:
            data = request(); data[key] = value; cases.append(data)
        for field, value in [('conditions', []), ('conditions', [{'id': 'model', 'description': '', 'check': 'semantic'}]),
                             ('purpose', float('nan')), ('constraints', ('tuple',))]:
            data = request(); data['brief'][field] = value; cases.append(data)
        data = request(); data['brief']['target']['issue_numbers'] = [True]; cases.append(data)
        for data in cases:
            with self.subTest(case=repr(data)[:70]):
                before = self.snapshot()
                self.assertFailure(self.create(data), 'invalid_input')
                self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.calls, [])

    def test_get_work_revision_selection_exact_shape_and_no_writes(self):
        created = self.create().value.to_json()
        goal = created['work_ref']['goal_id']
        before = self.snapshot()
        changes = self.conn.total_changes
        omitted = self.store.get_work({'goal_id': goal})
        self.assertEqual(self.store.get_work({'goal_id': goal, 'revision': 1}), omitted)
        for data in [{'goal_id': 'unknown'}, {'goal_id': goal, 'revision': 2},
                     {'goal_id': goal, 'revision': 2 ** 80}]:
            self.assertFailure(self.store.get_work(data), 'not_found')
        for value in [0, -1, True, 1.0, '1', None]:
            self.assertFailure(self.store.get_work({'goal_id': goal, 'revision': value}), 'invalid_input')
        for data in [{}, {'goal_id': ''}, {'goal_id': '\ud800'}, {'goal_id': goal, 'extra': 'SENTINEL'}]:
            self.assertFailure(self.store.get_work(data), 'invalid_input')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.conn.total_changes, changes)

    def test_constructor_rejects_configuration_before_schema_writes(self):
        for options in [dict(host_grant={}), dict(expert_id=''), dict(expert_id=True),
                        dict(source_gate=None), dict(id_factory=1)]:
            with self.subTest(options=list(options)):
                with self.assertRaises((TypeError, ValueError)):
                    self.make_store(**options)
        self.conn.execute('BEGIN')
        with self.assertRaises(ValueError):
            self.make_store()
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        with self.assertRaises(TypeError):
            self.create(scope={})
        other = sqlite3.connect(':memory:')
        self.addCleanup(other.close)
        with self.assertRaises(ValueError):
            IntakeStore(other, host_grant=grant(), expert_id='e', source_gate=self.gate)
        self.assertEqual(other.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])


if __name__ == '__main__':
    unittest.main()
