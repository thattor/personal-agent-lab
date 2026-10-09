"""TSK completion owner acceptance using explicit readonly VER/ART doubles."""
import copy
import sqlite3
import unittest
from unittest.mock import patch

from pal.contracts_v5 import Ref, Result, dumps, loads
import test_tasks_v5 as base
import test_task_artifact_binding_v5 as binding


class CompletionTests(unittest.TestCase):
    for _name in ('connect', 'make_store', 'value', 'error', 'claim', 'start', 'key',
                  'reserve', 'admit_request', 'returned', 'begin', 'release', 'control', 'snapshot'):
        locals()[_name] = getattr(base.TaskTests, _name)
    gate = binding.ArtifactBindingTests.gate
    inspect = binding.ArtifactBindingTests.inspect
    compose = binding.ArtifactBindingTests.compose
    current = binding.ArtifactBindingTests.current

    def setUp(self):
        base.TaskTests.setUp(self)
        self.artifacts, self.inspections = {}, []
        self.ver = None
        self.store = self.make_store(artifact_inspect=self.inspect, verification_inspect=self.inspect_ver)

    def create(self, **kwargs):
        request = base.intake(**kwargs)
        request['brief']['conditions'][0]['check'] = 'artifact_saved'
        return self.value(self.store.create(request, request_scope=self.grant))['work_ref']

    def inspect_ver(self, conn, request):
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        self.assertEqual(request, {'verification_ref': {'kind': 'verification', 'id': 'v'}})
        return Result.success(copy.deepcopy(self.ver))

    def ready(self):
        claim, step, ref, finish = self.compose()
        self.value(self.store.finish_step(finish))
        self.conn.execute('BEGIN')
        context = self.value(self.store.verification_context(self.conn, {'work_ref': claim['work_ref']}, purpose='status'))
        self.conn.rollback()
        self.ver = {k: context[k] for k in ('work_ref', 'artifact_refs', 'source_refs')}
        self.ver.update(status='valid', checks=[{'condition_id': c['id'], 'status': 'met',
            'reason': 'saved', 'evidence_refs': [ref]} for c in context['conditions']])
        return claim, {'key': 'complete', 'work_ref': claim['work_ref'],
            'command': {'kind': 'complete', 'verification_ref': {'kind': 'verification', 'id': 'v'}}}

    def test_complete_closes_lease_once_replay_reopen_and_next_work(self):
        claim, request = self.ready()
        budget = self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall()
        result = self.value(self.store.control(request))
        self.assertEqual(result, dict(work_ref=claim['work_ref'], state='completed', control_status='none'))
        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease').fetchone(), (0,))
        self.assertEqual(self.conn.execute('SELECT pause,drain FROM v5_tsk_control').fetchone(), (0, 0))
        events = self.conn.execute("SELECT refs_json FROM v5_intake_event WHERE kind='result'").fetchall()
        self.assertEqual(len(events), 1)
        self.assertEqual(loads(events[0][0]), self.ver['artifact_refs'] + [request['command']['verification_ref']])
        self.assertEqual(budget, self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall())
        self.store = self.make_store(artifact_inspect=self.inspect)
        self.assertEqual(self.value(self.store.control(request)), result)
        self.error(self.store.control({**request, 'key': 'new'}), 'denied')
        self.error(self.store.control({**request, 'command': 'pause'}), 'conflict')
        self.error(self.release(claim), 'denied')
        self.create(key='next')
        self.assertNotEqual(self.claim('next')['work_ref']['goal_id'], claim['work_ref']['goal_id'])

    def test_input_and_authority_precedence(self):
        claim, request = self.ready()
        for command in ({'kind': 'complete'}, {'kind': 'complete', 'verification_ref': {'kind': 'record', 'id': 'v'}},
                        {**request['command'], 'extra': True}, []):
            self.error(self.store.control({**request, 'command': command}), 'invalid_input')
        self.store._verification_inspect = None
        self.error(self.store.control(request), 'unavailable')
        self.value(self.control(claim, 'pause'))
        self.error(self.store.control(request), 'conflict')
        self.value(self.control(claim, 'cancel'))
        self.error(self.store.control(request), 'stale')

    def test_typed_callback_validation_and_comparison_precedence(self):
        _, request = self.ready()
        original = copy.deepcopy(self.ver)
        variants = [({'extra': True}, 'unavailable'), ({'checks': []}, 'unavailable'),
            ({'status': 'invalidated'}, 'unavailable'), ({'status': 'bad'}, 'unavailable'),
            ({'artifact_refs': [], 'checks': [{**original['checks'][0], 'evidence_refs': []}]}, 'stale'),
            ({'work_ref': {**original['work_ref'], 'goal_id': 'other'}}, 'conflict'),
            ({'work_ref': {**original['work_ref'], 'epoch': 0}}, 'stale'),
            ({'source_refs': []}, 'unavailable'),
            ({'source_refs': [{'kind': 'record', 'id': 'unregistered'}]}, 'unavailable')]
        for delta, expected in variants:
            with self.subTest(delta=delta):
                self.ver = {**copy.deepcopy(original), **delta}
                self.error(self.store.control(request), expected)
        for delta, expected in [({'status': 'unknown'}, 'conflict'), ({'status': 'unmet'}, 'conflict'),
                ({'condition_id': 'fake'}, 'unavailable'), ({'reason': 'x'*1025}, 'unavailable'),
                ({'evidence_refs': [{'kind': 'record', 'id': 'unknown'}]}, 'unavailable')]:
            self.ver = copy.deepcopy(original)
            self.ver['checks'][0].update(delta)
            self.error(self.store.control(request), expected)
        self.store._verification_inspect = lambda c, r: Result.failure('not_found', 'SECRET')
        self.error(self.store.control(request), 'not_found')
        self.store._verification_inspect = lambda c, r: {'ok': True}
        self.error(self.store.control(request), 'unavailable')

    def test_stopped_source_precedes_invalidated_disagreement(self):
        _, request = self.ready()
        self.ver['status'] = 'invalidated'
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
        self.error(self.store.control(request), 'denied')

    def test_unfinished_and_corrupt_call_step_states(self):
        claim, request = self.ready()
        call = self.conn.execute('SELECT id FROM v5_tsk_call').fetchone()[0]
        for state, expected in [('admitted', 'conflict'), ('broken', 'unavailable')]:
            self.conn.execute('UPDATE v5_tsk_call SET status=? WHERE id=?', (state, call))
            self.error(self.store.control(request), expected)
        self.conn.execute("UPDATE v5_tsk_call SET status='returned',step=NULL WHERE id=?", (call,))
        self.error(self.store.control(request), 'conflict')
        step_id, wire = self.conn.execute('SELECT id,wire FROM v5_tsk_step').fetchone()
        self.conn.execute('UPDATE v5_tsk_call SET step=? WHERE id=?', (step_id, call))
        # Add a report step so artifact-set validation stays intact.
        report = {'step_id': 'pending', 'work_ref': claim['work_ref'], 'index': 1,
                  'action': {'kind': 'report', 'summary': 'x'}, 'status': 'started', 'result_refs': []}
        self.conn.execute('INSERT INTO v5_tsk_step VALUES (?,?,?,?,?,?,?,?)',
            ('pending', claim['work_ref']['goal_id'], 1, 1, None, dumps(report), 0, '[]'))
        self.error(self.store.control(request), 'conflict')
        report['status'] = 'broken'
        self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(report), 'pending'))
        self.error(self.store.control(request), 'unavailable')

    def test_owned_writes_and_interruptions_roll_back_with_retry(self):
        _, request = self.ready()
        before = self.snapshot()
        original = self.store._event
        for exception in (RuntimeError('SECRET'), KeyboardInterrupt(), SystemExit()):
            def fail(*args):
                original(*args)
                raise exception
            with patch.object(self.store, '_event', side_effect=fail):
                if isinstance(exception, Exception):
                    self.error(self.store.control(request), 'unavailable')
                else:
                    with self.assertRaises(type(exception)):
                        self.store.control(request)
            self.assertFalse(self.conn.in_transaction)
            self.assertEqual(self.snapshot(), before)
        self.value(self.store.control(request))

    def test_readonly_guard_cleans_writes_exceptions_and_savepoint(self):
        _, request = self.ready()
        before = self.snapshot()
        for exception in (None, RuntimeError('SECRET'), KeyboardInterrupt()):
            def bad(conn, req):
                conn.execute("UPDATE v5_intake_work SET state='failed'")
                if exception is not None:
                    raise exception
                return Result.success(self.ver)
            self.store._verification_inspect = bad
            if isinstance(exception, KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.store.control(request)
            else:
                self.error(self.store.control(request), 'unavailable')
            self.assertEqual(self.snapshot(), before)
            self.assertFalse(self.conn.in_transaction)
        self.store._verification_inspect = self.inspect_ver
        self.value(self.store.control(request))

    def test_completed_stop_notice_is_scoped_replayed_and_preserves_max_epoch(self):
        claim, request = self.ready()
        receipt = self.value(self.store.control(request))
        self.conn.execute('UPDATE v5_intake_work SET epoch=?', (2**63-1,))
        for _ in range(2):
            self.conn.execute('BEGIN IMMEDIATE')
            result = self.store.invalidate_by_refs(self.conn, key='stop', session_id='different',
                refs=(Ref('record', 'origin'), Ref('record', 'extra')))
            self.assertEqual(self.value(result), {'work_refs': []})
            self.conn.commit()
        row = self.conn.execute('SELECT state,epoch FROM v5_intake_work').fetchone()
        self.assertEqual(row, ('completed', 2**63-1))
        notices = self.conn.execute("SELECT session_id,text,refs_json FROM v5_intake_event WHERE kind='progress' AND text LIKE 'a source%'").fetchall()
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0][0], 'session')
        self.assertEqual(loads(notices[0][2]), [{'kind': 'record', 'id': 'origin'}])
        self.assertEqual(self.value(self.store.control(request)), receipt)

    def test_terminal_release_defensively_preserves_completed_and_failed(self):
        claim = self.start()
        for terminal in ('completed', 'failed'):
            self.conn.execute('UPDATE v5_intake_work SET state=?', (terminal,))
            self.conn.execute('UPDATE v5_tsk_lease SET active=1')
            self.conn.execute("DELETE FROM v5_intake_replay WHERE command='release'")
            self.assertEqual(self.value(self.release(claim))['state'], terminal)

    def test_completed_and_running_stop_share_one_transaction(self):
        first, request = self.ready()
        self.value(self.store.control(request))
        self.create(key='second')
        second = self.claim()
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.value(self.store.invalidate_by_refs(self.conn, key='both', session_id='x', refs=(Ref('record', 'origin'),)))
        self.conn.commit()
        self.assertEqual(result['work_refs'], [{**second['work_ref'], 'epoch': second['work_ref']['epoch']+1}])
        self.assertEqual(self.current(first)['state'], 'completed')

    def test_stored_empty_duplicate_conditions_are_unavailable(self):
        _, request = self.ready()
        original = self.conn.execute('SELECT brief_json FROM v5_intake_work').fetchone()[0]
        brief = loads(original)
        for conditions in ([], brief['conditions'] * 2):
            self.conn.execute('UPDATE v5_intake_work SET brief_json=?', (dumps({**brief, 'conditions': conditions}),))
            self.error(self.store.control(request), 'unavailable')
        self.conn.execute('UPDATE v5_intake_work SET brief_json=?', (original,))
        self.value(self.store.control(request))

    def test_added_artifact_rejects_old_whole_set(self):
        claim, request = self.ready()
        _, _, _, finish = self.compose(claim)
        self.value(self.store.finish_step(finish))
        self.error(self.store.control(request), 'stale')

    def test_pause_complete_order_and_source_stop_fence(self):
        claim, request = self.ready()
        other = self.make_store(conn=self.connect(), artifact_inspect=self.inspect)
        self.value(other.control({'key': 'pause', 'work_ref': claim['work_ref'], 'command': 'pause'}))
        self.error(self.store.control(request), 'conflict')
        self.conn.execute('UPDATE v5_tsk_control SET pause=0')
        self.value(self.store.control(request))
        self.error(other.control({'key': 'late-pause', 'work_ref': claim['work_ref'], 'command': 'pause'}), 'conflict')
        self.error(other.control({'key': 'late-cancel', 'work_ref': claim['work_ref'], 'command': 'cancel'}), 'conflict')

    def test_callback_owned_savepoint_cleanup_preserves_outer_transaction(self):
        self.ready()
        self.conn.execute('BEGIN')
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='extra'")
        def interrupted(conn, request):
            conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
            raise KeyboardInterrupt()
        self.store._verification_inspect = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.store._inspect_verification(Ref('verification', 'v'))
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(self.conn.execute("SELECT status FROM test_sources WHERE id='origin'").fetchone()[0], 'available')
        self.assertEqual(self.conn.execute("SELECT status FROM test_sources WHERE id='extra'").fetchone()[0], 'denied')
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute('RELEASE v5_tsk_verification_inspect')
        self.conn.rollback()

    def test_completed_notice_rolls_back_with_running_invalidation_failure(self):
        _, request = self.ready()
        self.value(self.store.control(request))
        self.create(key='second')
        self.claim()
        before = self.snapshot()
        original = self.store._event
        def fail(row, kind, *args):
            original(row, kind, *args)
            if kind == 'state':
                raise RuntimeError('SECRET')
        self.conn.execute('BEGIN IMMEDIATE')
        with patch.object(self.store, '_event', side_effect=fail):
            self.error(self.store.invalidate_by_refs(self.conn, key='atomic', session_id='x', refs=(Ref('record', 'origin'),)), 'unavailable')
        self.conn.rollback()
        self.assertEqual(self.snapshot(), before)

    def test_committed_lost_response_replays_without_writes(self):
        _, request = self.ready()
        receipt = self.value(self.store.control(request))
        before = self.snapshot()
        # The transport loses this committed receipt; the caller resends its key.
        replay = self.value(self.store.control(copy.deepcopy(request)))
        self.assertEqual(replay, receipt)
        self.assertEqual(self.snapshot(), before)

    def test_returned_call_cannot_borrow_another_finished_step(self):
        _, request = self.ready()
        self.conn.execute("UPDATE v5_tsk_step SET call='unrelated'")
        self.error(self.store.control(request), 'unavailable')


if __name__ == '__main__':
    unittest.main()
