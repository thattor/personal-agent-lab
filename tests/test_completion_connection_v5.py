"""C10 with actual temporary SQLite MEM/TSK/ART/VER and public C14 reads."""
import copy
import sqlite3
import unittest

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, dumps
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore
import test_verification_connection_v5 as fixture


NOTICE = 'a source registered for this completed work was stopped; completion is historical'


class CompletionFaultConnection(fixture.FaultConnection):
    completion_fault = None

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if self.completion_fault:
            phase, exception = self.completion_fault
            matches = {
                'state': sql.startswith('UPDATE v5_intake_work SET state='),
                'lease': sql.startswith('UPDATE v5_tsk_lease SET active=0'),
                'flags': sql.startswith('INSERT INTO v5_tsk_control'),
                'event': sql.startswith('INSERT INTO v5_intake_event') and
                         'work completed from saved verification' in parameters,
                'replay': sql.startswith('INSERT INTO v5_intake_replay') and
                          parameters[0] == 'control',
                'notice': sql.startswith('INSERT INTO v5_intake_event') and NOTICE in parameters,
            }
            if matches[phase]:
                self.completion_fault = None
                raise exception('injected after actual ' + phase + ' write')
        return result


class CompletionConnectionTests(unittest.TestCase):
    for _name in ('stage', 'compose', 'verify', 'request', 'status', 'current',
                  'stop', 'usage', 'value', 'error'):
        locals()[_name] = getattr(fixture.VerificationConnectionTests, _name)

    def setUp(self):
        self.inspect_hook = None
        fixture.VerificationConnectionTests.setUp(self)

    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=0,
                                     factory=CompletionFaultConnection)
        self.addCleanup(connection.close)
        memory = artifacts = verifications = None

        def inspect(conn, request):
            if self.inspect_hook and conn is self.conn:
                self.inspect_hook(conn, request)
            return verifications.inspect(conn, request)

        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        tasks = TaskStore(connection, host_limits=Limits(0, 50, 50), host_grant=grant,
            expert_id='expert', source_gate=lambda c, refs: memory.source_gate(c, refs),
            artifact_inspect=lambda c, request: artifacts.inspect(c, request),
            verification_inspect=inspect)
        memory = MemoryStore(connection, sanitize_text=lambda text: text,
            append_event=tasks.append_event, invalidate_by_refs=tasks.invalidate_by_refs)
        artifacts = ArtifactStore(connection, authorize_save=tasks.authorize_artifact_save,
                                  source_gate=memory.source_gate)
        verifications = VerificationStore(connection, context=tasks.verification_context,
            artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
        return connection, tasks, memory, artifacts, verifications

    def complete_request(self, receipt, key=None):
        ref = receipt['verification_ref']
        return {'key': key or dumps(['C10.complete', self.work, ref]),
                'work_ref': copy.deepcopy(self.work),
                'command': {'kind': 'complete', 'verification_ref': ref}}

    def ready(self, *, all_kinds=False):
        self.stage(all_kinds=all_kinds)
        self.compose()
        receipt = self.verify()
        return receipt, self.complete_request(receipt)

    def events(self, session='draft-session'):
        return self.value(EventReader(self.conn).get_events({'session_id': session}))['events']

    def snapshot(self):
        return tuple(self.conn.iterdump())

    def create_next(self, session='next-session'):
        brief = copy.deepcopy(self.current()['brief'])
        for condition in brief['conditions']:
            del condition['id']
        return self.value(self.tasks.create({'key': 'next-create', 'session_id': session,
            'origin_record_ref': self.refs[0], 'brief': brief},
            request_scope=Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))))['work_ref']

    def test_complete_once_closes_lease_preserves_budgets_reopens_and_claims_next(self):
        verification, request = self.ready()
        before = self.usage()
        completed = self.value(self.tasks.control(request))
        self.assertEqual(completed, {'work_ref': self.work, 'state': 'completed', 'control_status': 'none'})
        self.assertEqual(self.current()['work_ref'], self.work)
        self.assertEqual(self.current()['current_artifact_refs'], self.saved_refs)
        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease').fetchall(), [(0,)])
        self.assertEqual(self.conn.execute('SELECT pause,drain FROM v5_tsk_control').fetchall(), [(0, 0)])
        results = [event for event in self.events() if event['kind'] == 'result']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['refs'], self.saved_refs + [verification['verification_ref']])
        self.assertEqual(results[0]['work_ref'], self.work)
        self.assertEqual((self.usage(), self.calls), (before, 1))
        self.conn.close()
        self.conn, self.tasks, self.memory, self.artifacts, self.verifications = self.connect()
        snapshot = self.snapshot()
        self.assertEqual(self.value(self.tasks.control(request)), completed)
        self.assertEqual(snapshot, self.snapshot())
        self.error(self.tasks.control({**request, 'key': 'new-complete'}), 'denied')
        self.error(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.work,
                                      'outcome': 'failed', 'reason': 'late release'}), 'denied')
        next_work = self.create_next()
        self.assertEqual(self.value(self.tasks.claim({'runner_id': 'next-host'}))['work_ref']['goal_id'],
                         next_work['goal_id'])
        self.assertEqual(self.current()['state'], 'completed')

    def test_semantic_or_source_fetch_unknown_cannot_complete(self):
        verification, request = self.ready(all_kinds=True)
        self.assertEqual([check['status'] for check in verification['checks']], ['met', 'unknown', 'unknown'])
        before = self.snapshot()
        self.error(self.tasks.control(request), 'conflict')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.current()['state'], 'running')
        self.assertFalse(any(event['kind'] == 'result' for event in self.events()))

    def test_selected_and_unselected_source_stop_keeps_completed_history(self):
        for selected in (True, False):
            with self.subTest(selected=selected):
                if not selected:
                    self.setUp()
                verification, request = self.ready()
                completed = self.value(self.tasks.control(request))
                _, _, other_memory, _, _ = self.connect()
                stopped = self.refs[0 if selected else 1]
                first = self.value(self.stop(other_memory, stopped))
                self.assertEqual(self.value(self.stop(other_memory, stopped)), first)
                self.assertEqual((self.current()['state'], self.current()['work_ref']), ('completed', self.work))
                self.assertEqual(self.value(self.status(verification))['status'], 'invalidated')
                self.assertEqual(self.value(self.tasks.control(request)), completed)
                self.assertEqual(self.verify(), verification)
                self.error(self.artifacts.read({'ref': self.saved_refs[0]}, purpose='verification'), 'denied')
                self.assertFalse(self.value(self.artifacts.read({'ref': self.saved_refs[0]}, purpose='user_view'))['usable'])
                notices = [event for event in self.events() if event['text'] == NOTICE]
                self.assertEqual(len(notices), 1)
                self.assertEqual((notices[0]['work_ref'], notices[0]['refs']), (self.work, [stopped]))
                self.assertFalse(any(event['text'] == NOTICE for event in self.events('control-session')))
                self.conn.close()
                self.conn, self.tasks, self.memory, self.artifacts, self.verifications = self.connect()
                self.assertEqual(self.value(self.tasks.control(request)), completed)
                self.assertEqual(self.value(self.status(verification))['status'], 'invalidated')

    def test_shared_source_stop_is_atomic_for_completed_and_running_work(self):
        verification, request = self.ready()
        self.value(self.tasks.control(request))
        next_work = self.create_next()
        next_lease = self.value(self.tasks.claim({'runner_id': 'next-host'}))
        before = self.snapshot()
        self.conn.completion_fault = ('notice', RuntimeError)
        self.error(self.stop(self.memory, self.refs[0]), 'unavailable')
        self.assertIsNone(self.conn.completion_fault)
        self.assertFalse(self.conn.in_transaction)
        self.assertEqual(before, self.snapshot())
        self.value(self.stop(self.memory, self.refs[0]))
        current_next = self.value(self.tasks.get_work({'goal_id': next_work['goal_id']}))
        self.assertEqual(current_next['state'], 'running')
        self.assertEqual(current_next['work_ref']['epoch'], next_lease['work_ref']['epoch'] + 1)
        self.assertEqual((self.current()['state'], self.current()['work_ref']), ('completed', self.work))
        self.assertEqual(self.value(self.status(verification))['status'], 'invalidated')
        self.assertEqual(len([event for event in self.events() if event['text'] == NOTICE]), 1)
        self.assertEqual(len([event for event in self.events('next-session')
                              if event['text'] == 'work sources invalidated']), 1)

    def test_control_or_source_stop_before_complete_wins_on_other_connection(self):
        for command, code in (('pause', 'conflict'), ('cancel', 'stale'), ('stop', 'stale')):
            with self.subTest(command=command):
                if command != 'pause':
                    self.setUp()
                _, request = self.ready()
                _, tasks, memory, _, _ = self.connect()
                if command == 'stop':
                    self.value(self.stop(memory, self.refs[1]))
                else:
                    self.value(tasks.control({'key': command, 'work_ref': self.work, 'command': command}))
                before = self.snapshot()
                self.error(self.tasks.control(request), code)
                self.assertEqual(before, self.snapshot())
                self.assertFalse(any(event['kind'] == 'result' for event in self.events()))

    def test_complete_write_lock_orders_other_connection_controls(self):
        _, request = self.ready()
        _, tasks, memory, _, _ = self.connect()
        attempts = []
        def race(connection, inspected):
            self.assertTrue(connection.in_transaction)
            attempts.append(tasks.control({'key': 'pause', 'work_ref': self.work, 'command': 'pause'}))
            attempts.append(self.stop(memory, self.refs[1]))
        self.inspect_hook = race
        self.value(self.tasks.control(request))
        self.assertEqual(len(attempts), 2)
        for result in attempts:
            self.error(result, 'unavailable')
        self.inspect_hook = None
        for command in ('pause', 'cancel', 'resume'):
            self.error(tasks.control({'key': command, 'work_ref': self.work, 'command': command}), 'conflict')
        self.value(self.stop(memory, self.refs[1]))
        self.assertEqual(self.current()['state'], 'completed')

    def test_new_attachment_and_new_epoch_require_current_whole_set_verification(self):
        _, old_request = self.ready()
        self.compose()
        self.error(self.tasks.control(old_request), 'stale')
        before_yield = self.verify('second-artifact')
        self.value(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.work,
                                      'outcome': 'yield', 'reason': 'bounded slice'}))
        self.lease = self.value(self.tasks.claim({'runner_id': 'next-epoch'}))
        self.work = self.lease['work_ref']
        self.error(self.tasks.control(self.complete_request(before_yield)), 'stale')
        current = self.verify('new-epoch')
        self.assertEqual(self.value(self.tasks.control(self.complete_request(current)))['state'], 'completed')
        self.assertEqual(self.usage(), {'model': 2, 'step': 2})

    def test_corrupt_verification_record_cannot_create_completion(self):
        _, request = self.ready()
        self.conn.execute("UPDATE v5_ver_body SET record_json='{}'")
        before = self.snapshot()
        self.error(self.tasks.control(request), 'unavailable')
        self.assertEqual(before, self.snapshot())

    def test_each_actual_completion_write_rolls_back_errors_and_interruptions(self):
        _, request = self.ready()
        before = self.snapshot()
        for phase in ('state', 'lease', 'flags', 'event', 'replay'):
            for exception in (RuntimeError, KeyboardInterrupt, SystemExit):
                with self.subTest(phase=phase, exception=exception.__name__):
                    self.conn.completion_fault = (phase, exception)
                    if issubclass(exception, Exception):
                        self.error(self.tasks.control(request), 'unavailable')
                    else:
                        with self.assertRaises(exception):
                            self.tasks.control(request)
                    self.assertIsNone(self.conn.completion_fault)
                    self.assertFalse(self.conn.in_transaction)
                    self.assertEqual(before, self.snapshot())
        self.assertEqual(self.value(self.tasks.control(request))['state'], 'completed')
        self.assertEqual(len([event for event in self.events() if event['kind'] == 'result']), 1)


if __name__ == '__main__':
    unittest.main()
