"""TSK binding consumer tests; ART inspect is an explicit contract double."""
import copy
import unittest
from unittest.mock import patch

from pal.contracts_v5 import Ref, Result, dumps, loads
import test_tasks_v5 as fixture


class ArtifactBindingTests(unittest.TestCase):
    connect = fixture.TaskTests.connect
    make_store = fixture.TaskTests.make_store
    value = fixture.TaskTests.value
    error = fixture.TaskTests.error
    create = fixture.TaskTests.create
    claim = fixture.TaskTests.claim
    start = fixture.TaskTests.start
    key = fixture.TaskTests.key
    reserve = fixture.TaskTests.reserve
    admit_request = fixture.TaskTests.admit_request
    returned = fixture.TaskTests.returned
    begin = fixture.TaskTests.begin
    release = fixture.TaskTests.release
    control = fixture.TaskTests.control
    snapshot = fixture.TaskTests.snapshot

    def setUp(self):
        fixture.TaskTests.setUp(self)
        self.artifacts = {}
        self.inspections = []
        self.store = self.make_store(artifact_inspect=self.inspect)

    def gate(self, conn, refs):
        if any(ref.kind.value != 'record' for ref in refs):
            return 'unavailable'
        return fixture.TaskTests.gate(self, conn, refs)

    def inspect(self, conn, request):
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        self.assertEqual(set(request), {'ref'})
        self.inspections.append(copy.deepcopy(request))
        metadata = self.artifacts.get(request['ref']['id'])
        return Result.success(copy.deepcopy(metadata)) if metadata else Result.failure('not_found', 'SECRET')

    def compose(self, claim=None):
        claim = claim or self.start()
        call = self.returned(claim)
        step = self.value(self.begin(claim, {'kind': 'compose', 'content': 'draft\n',
                                            'media_type': 'text/plain', 'source_refs': []}))
        ref = {'kind': 'artifact', 'id': 'artifact-' + step['step_id']}
        self.artifacts[ref['id']] = {'artifact_ref': ref, 'work_ref': claim['work_ref'],
            'step_id': step['step_id'], 'hash': 'a' * 64, 'bytes': 6, 'source_refs': call['source_refs']}
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': [ref]}
        return claim, step, ref, request

    def current(self, claim):
        return self.value(self.store.get_work({'goal_id': claim['work_ref']['goal_id']}))

    def test_append_projection_reopen_and_later_report_without_artifact_input(self):
        claim, step, ref, request = self.compose()
        finished = self.value(self.store.finish_step(request))
        self.assertEqual(finished['status'], 'finished')
        self.assertEqual(self.current(claim)['current_artifact_refs'], [ref])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM v5_intake_source WHERE kind='artifact'").fetchone()[0], 0)
        self.assertEqual(loads(self.conn.execute("SELECT refs_json FROM v5_intake_event WHERE kind='progress'").fetchone()[0]), [ref])
        self.value(self.release(claim))
        self.conn = self.connect()
        self.store = self.make_store(artifact_inspect=self.inspect)
        next_claim = self.claim('next')
        context = self.value(self.store.get_execution_context({'work_ref': next_claim['work_ref'], 'lease_id': next_claim['lease_id']}))
        self.assertEqual(context['optional_refs'], [])
        sources = context['step_sources'][0]['refs']
        self.assertIn(ref, sources)
        available = context['required_refs'] + context['optional_refs']
        self.assertFalse(set(map(dumps, sources)) <= set(map(dumps, available)))
        self.returned(next_claim)
        report = self.value(self.begin(next_claim))
        self.value(self.store.finish_step({'work_ref': next_claim['work_ref'], 'step_id': report['step_id'], 'result_refs': []}))
        self.assertEqual(self.current(next_claim)['current_artifact_refs'], [ref])
        _, step2, ref2, request2 = self.compose(next_claim)
        self.value(self.store.finish_step(request2))
        self.assertEqual(self.current(next_claim)['current_artifact_refs'], [ref, ref2])
        self.assertNotEqual(step['step_id'], step2['step_id'])

    def test_old_work_empty_projection_and_missing_inspector_prevents_compose_start(self):
        claim = self.start()
        self.assertEqual(self.current(claim)['current_artifact_refs'], [])
        self.returned(claim)
        self.store = self.make_store()
        before = self.snapshot()
        self.error(self.begin(claim, {'kind': 'compose', 'content': '', 'media_type': 'text/plain', 'source_refs': []}), 'unavailable')
        self.assertEqual(before, self.snapshot())

    def test_finish_replay_after_pause_release_and_changed_input(self):
        claim, step, ref, request = self.compose()
        finished = self.value(self.store.finish_step(request))
        self.value(self.control(claim, 'pause'))
        self.value(self.release(claim))
        before = self.snapshot()
        self.assertEqual(self.value(self.store.finish_step(request)), finished)
        self.assertEqual(before, self.snapshot())
        self.error(self.store.finish_step(dict(request, error='changed')), 'conflict')
        self.assertEqual(len(self.inspections), 1)

    def test_compose_result_shape_is_closed_and_not_filtered(self):
        claim, step, ref, request = self.compose()
        for refs in ([], [ref, ref], [ref, {'kind': 'artifact', 'id': 'other'}], [{'kind': 'record', 'id': 'origin'}]):
            before = self.snapshot()
            self.error(self.store.finish_step(dict(request, result_refs=refs)), 'invalid_input')
            self.assertEqual(before, self.snapshot())
        for kwargs in ({'truncated': True}, {'excluded_refs': (Ref('record', 'origin'),)}):
            self.error(self.store.finish_step(request, **kwargs), 'invalid_input')
        self.error(self.store.finish_step(dict(request, error='')), 'invalid_input')
        self.assertEqual(self.inspections, [])

    def test_inspect_metadata_exact_types_and_binding_errors(self):
        claim, step, ref, request = self.compose()
        original = copy.deepcopy(self.artifacts[ref['id']])
        variants = [({'extra': 1}, 'unavailable'), ({'artifact_ref': {'kind': 'artifact', 'id': 'other'}}, 'unavailable'),
                    ({'hash': 'A' * 64}, 'unavailable'), ({'hash': None}, 'unavailable'),
                    ({'bytes': True}, 'unavailable'), ({'bytes': -1}, 'unavailable'), ({'bytes': 1048577}, 'unavailable'),
                    ({'source_refs': []}, 'unavailable'), ({'source_refs': [{'kind': 'artifact', 'id': 'a'}]}, 'unavailable'),
                    ({'source_refs': [{'kind': 'record', 'id': 'extra'}]}, 'unavailable'),
                    ({'step_id': 'wrong-step'}, 'conflict'),
                    ({'work_ref': dict(claim['work_ref'], epoch=0)}, 'stale')]
        for changes, code in variants:
            with self.subTest(changes=changes):
                self.artifacts[ref['id']] = dict(original, **changes)
                before = self.snapshot()
                self.error(self.store.finish_step(request), code)
                self.assertEqual(before, self.snapshot())
        self.artifacts.clear()
        self.error(self.store.finish_step(request), 'not_found')

    def test_callback_bad_returns_exceptions_and_mutation_roll_back(self):
        claim, step, ref, request = self.compose()
        for callback in (lambda *a: None, lambda *a: {'ok': True},
                         lambda *a: Result.success({'hash': 'bad'}),
                         lambda *a: (_ for _ in ()).throw(RuntimeError('SECRET')),
                         lambda *a: Result.failure('denied', 'SECRET', (Ref('record', 'SECRET'),))):
            before = self.snapshot()
            with patch.object(self.store, '_artifact_inspect', callback):
                result = self.store.finish_step(request)
            self.assertFalse(result.ok)
            self.assertNotIn('SECRET', dumps(result))
            self.assertEqual(before, self.snapshot())
        def writer(conn, data):
            conn.execute("UPDATE test_sources SET status='denied'")
            return self.inspect(conn, data)
        with patch.object(self.store, '_artifact_inspect', writer):
            self.error(self.store.finish_step(request), 'unavailable')
        self.assertEqual(self.conn.execute("SELECT status FROM test_sources WHERE id='origin'").fetchone()[0], 'available')
        self.assertEqual(self.current(claim)['current_artifact_refs'], [])

    def test_inspector_ended_transaction_is_detected_without_false_rollback_claim(self):
        claim, step, ref, request = self.compose()
        def commits(conn, data):
            result = self.inspect(conn, data)
            conn.execute('COMMIT')
            return result
        with patch.object(self.store, '_artifact_inspect', commits):
            self.error(self.store.finish_step(request), 'unavailable')
        self.assertFalse(self.conn.in_transaction)
        self.assertEqual(self.current(claim)['current_artifact_refs'], [])
        # No attachment write precedes inspect; this asserts detection, not undo of
        # arbitrary host writes committed inside a trusted callback.

    def test_call_binding_status_lease_and_missing_call_are_checked(self):
        claim, step, ref, request = self.compose()
        call_id = self.conn.execute('SELECT id FROM v5_tsk_call').fetchone()[0]
        for column, value, code in [('step', 'wrong', 'unavailable'), ('status', 'admitted', 'conflict'),
                                    ('lease', 'wrong', 'denied'), ('work', dumps(dict(claim['work_ref'], epoch=0)), 'stale')]:
            original = self.conn.execute('SELECT ' + column + ' FROM v5_tsk_call WHERE id=?', (call_id,)).fetchone()[0]
            self.conn.execute('UPDATE v5_tsk_call SET ' + column + '=? WHERE id=?', (value, call_id))
            before = self.snapshot()
            self.error(self.store.finish_step(request), code)
            self.assertEqual(before, self.snapshot())
            self.conn.execute('UPDATE v5_tsk_call SET ' + column + '=? WHERE id=?', (original, call_id))
        self.conn.execute('DELETE FROM v5_tsk_call WHERE id=?', (call_id,))
        self.error(self.store.finish_step(request), 'unavailable')

    def test_stop_pause_and_abandonment_prevent_new_attachment(self):
        claim, step, ref, request = self.compose()
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
        self.error(self.store.finish_step(request), 'denied')
        self.conn.execute("UPDATE test_sources SET status='available' WHERE id='origin'")
        self.value(self.control(claim, 'pause'))
        self.error(self.store.finish_step(request), 'conflict')
        self.value(self.release(claim))
        self.error(self.store.finish_step(request), 'denied')
        self.assertEqual(self.current(claim)['current_artifact_refs'], [])

    def test_faults_after_step_set_dependency_event_and_replay_are_atomic(self):
        claim, step, ref, request = self.compose()
        for name in ('_register', '_event', '_save_replay'):
            for interruption in (RuntimeError, KeyboardInterrupt, SystemExit):
                before = self.snapshot()
                original = getattr(self.store, name)
                def fail_after(*args, **kwargs):
                    original(*args, **kwargs)
                    raise interruption('SECRET')
                with patch.object(self.store, name, fail_after):
                    if interruption is RuntimeError:
                        self.error(self.store.finish_step(request), 'unavailable')
                    else:
                        with self.assertRaises(interruption):
                            self.store.finish_step(request)
                self.assertFalse(self.conn.in_transaction)
                self.assertEqual(before, self.snapshot())
        self.conn.execute("CREATE TRIGGER binding_fault BEFORE INSERT ON v5_tsk_artifact_set BEGIN SELECT RAISE(ABORT,'SECRET'); END")
        before = self.snapshot()
        self.error(self.store.finish_step(request), 'unavailable')
        self.assertEqual(before, self.snapshot())
        self.conn.execute('DROP TRIGGER binding_fault')
        self.value(self.store.finish_step(request))

    def test_current_set_corruption_and_arbitrary_artifact_provenance_fail_closed(self):
        claim, step, ref, request = self.compose()
        self.value(self.store.finish_step(request))
        self.conn.execute("UPDATE v5_tsk_artifact_set SET artifact_id='wrong'")
        self.error(self.store.get_work({'goal_id': claim['work_ref']['goal_id']}), 'unavailable')
        context = {'work_ref': claim['work_ref'], 'lease_id': claim['lease_id']}
        self.error(self.store.get_execution_context(context), 'unavailable')
        self.conn.execute('DELETE FROM v5_tsk_artifact_set')
        self.error(self.store.get_execution_context(context), 'unavailable')
        self.conn.execute('INSERT INTO v5_tsk_artifact_set(goal,revision,artifact_id,step_id) VALUES (?,?,?,?)',
                          (claim['work_ref']['goal_id'], 1, ref['id'], step['step_id']))
        self.conn.execute("DELETE FROM v5_intake_source WHERE id='origin'")
        self.error(self.store.get_execution_context(context), 'unavailable')

    def test_only_bound_finished_compose_can_carry_unregistered_artifact(self):
        claim = self.start()
        self.returned(claim)
        report = self.value(self.begin(claim))
        self.value(self.store.finish_step({'work_ref': claim['work_ref'], 'step_id': report['step_id'], 'result_refs': []}))
        report.update(status='finished', result_refs=[{'kind': 'artifact', 'id': 'unbound'}])
        self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(report), report['step_id']))
        context = {'work_ref': claim['work_ref'], 'lease_id': claim['lease_id']}
        self.error(self.store.get_execution_context(context), 'unavailable')
        self.conn.execute('INSERT INTO v5_intake_source VALUES (?,?,?,?)',
                          (claim['work_ref']['goal_id'], 1, 'artifact', 'unbound'))
        self.error(self.store.get_execution_context(context), 'unavailable')

    def test_inspect_sources_match_the_entire_call_and_gate_is_rechecked(self):
        claim = self.start()
        refs = [{'kind': 'record', 'id': name} for name in ('origin', 'extra')]
        self.value(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': refs}))
        call = self.returned(claim, refs)
        step = self.value(self.begin(claim, {'kind': 'compose', 'content': 'draft', 'media_type': 'text/plain', 'source_refs': [refs[0]]}))
        ref = {'kind': 'artifact', 'id': 'union'}
        metadata = {'artifact_ref': ref, 'work_ref': claim['work_ref'], 'step_id': step['step_id'],
                    'hash': 'a' * 64, 'bytes': 5, 'source_refs': [refs[0]]}
        self.artifacts['union'] = metadata
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': [ref]}
        self.error(self.store.finish_step(request), 'unavailable')
        metadata['source_refs'] = list(reversed(refs))
        original_gate = self.store._source_gate
        checks = []
        def changes_availability(conn, supplied):
            checks.append(supplied)
            if len(checks) == 2:
                return 'denied'
            return original_gate(conn, supplied)
        with patch.object(self.store, '_source_gate', changes_availability):
            self.error(self.store.finish_step(request), 'denied')
        self.assertEqual(self.current(claim)['current_artifact_refs'], [])
        self.value(self.store.finish_step(request))
        self.assertEqual(self.current(claim)['current_artifact_refs'], [ref])

    def test_artifact_reinput_stays_closed(self):
        claim, step, ref, request = self.compose()
        self.value(self.store.finish_step(request))
        self.error(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': [ref]}), 'unavailable')
        self.returned(claim)
        self.error(self.begin(claim, {'kind': 'lookup', 'query': '', 'source_refs': [ref]}), 'invalid_input')
        data = fixture.intake(key='other')
        data['brief']['context_refs'] = [ref]
        self.error(self.store.create(data, request_scope=self.grant), 'unavailable')


if __name__ == '__main__':
    unittest.main()
