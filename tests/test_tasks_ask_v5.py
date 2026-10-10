"""ASK01 fixed owner acceptance: actual temporary SQLite TSK/MEM, no provider."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import sqlite3
import tempfile
import unittest
from pal.contracts_v5 import Grant, Limits, dumps, loads
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.tasks_v5 import TaskStore


class FaultConnection(sqlite3.Connection):
    fault = None
    writes_until_fault = 1

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if self.fault and sql.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
            self.writes_until_fault -= 1
            if self.writes_until_fault == 0:
                failure, self.fault = self.fault, None
                raise failure('private injected post-write failure')
        return result


class TaskAskTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'ask.sqlite'
        self.grant = Grant(('read',), ('repo',), Limits(0, 20, 20))
        self.conn, self.tasks, self.memory = self.connect()
        self.serial = 0
        self.origin = self.record('origin')
        self.extra = self.record('unselected input')
        self.history = self.record('historical optional')
        created = self.value(self.tasks.create({'key': 'create', 'session_id': 'session',
            'origin_record_ref': self.origin, 'brief': {'purpose': 'ask then draft',
                'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                'constraints': [], 'conditions': [{'description': 'draft saved', 'check': 'artifact_saved'}],
                'context_refs': []}}, request_scope=self.grant))
        self.goal = created['work_ref']['goal_id']
        self.lease = self.value(self.tasks.claim({'runner_id': 'runner'}))

    def connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=0, factory=FaultConnection)
        self.addCleanup(conn.close)
        memory = None
        tasks = TaskStore(conn, host_grant=self.grant, host_limits=Limits(0, 100, 100),
            expert_id='expert', source_gate=lambda connection, refs: memory.source_gate(connection, refs))
        memory = MemoryStore(conn, sanitize_text=lambda text: text,
                            append_event=tasks.append_event, invalidate_by_refs=tasks.invalidate_by_refs)
        return conn, tasks, memory

    def key(self):
        self.serial += 1
        return str(self.serial)

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        self.assertNotIn('private', result.error.message)
        self.assertLess(len(result.error.message), 160)

    def record(self, text):
        return self.value(self.memory.append({'client_key': self.key(), 'session_id': 'session',
            'role': 'user', 'text': text}))['record_ref']

    def work(self):
        return self.value(self.tasks.get_work({'goal_id': self.goal, 'revision': 1}))

    def call(self, refs):
        work = self.lease['work_ref']
        self.value(self.tasks.register_sources({'work_ref': work, 'refs': refs}))
        index = self.value(self.tasks.get_execution_context({'lease_id': self.lease['lease_id'], 'work_ref': work}))['next_step_index']
        reservation = self.value(self.tasks.reserve_budget({'key': self.key(), 'work_ref': work,
            'kind': 'model', 'role': 'expert'}))['reservation_id']
        call_id = dumps(['C15.call', self.lease['lease_id'], index])
        self.value(self.tasks.admit_call({'call_id': call_id, 'lease_id': self.lease['lease_id'],
            'work_ref': work, 'reservation_id': reservation, 'source_refs': refs}))
        self.value(self.tasks.end_call({'call_id': call_id, 'outcome': 'returned'}))
        return call_id

    def stage(self, *, selected=None):
        self.call_id = self.call([self.origin, self.extra])
        action = {'kind': 'ask', 'question': '回答をお願いします。', 'missing_fact': '確認した日程',
                  'source_refs': selected if selected is not None else [self.origin]}
        step = self.value(self.tasks.begin_step({'key': self.key(), 'work_ref': self.lease['work_ref'], 'action': action}))
        self.request = {'key': dumps(['C04.ask', self.lease['work_ref'], step['step_id']]),
            'work_ref': self.lease['work_ref'], 'step_id': step['step_id'],
            **{k: v for k, v in action.items() if k != 'kind'}}
        return step

    def ask(self):
        self.stage()
        return self.value(self.tasks.ask(self.request))

    def answer_request(self, receipt, record=None):
        record = record or self.record('月曜日です。')
        work = self.work()['work_ref']
        return {'key': dumps(['C10.answer', work['goal_id'], work['revision'], receipt['question_id'], record]),
            'work_ref': work, 'command': {'kind': 'answer', 'question_id': receipt['question_id'], 'answer_record_ref': record}}

    def control(self, command):
        return self.value(self.tasks.control({'key': self.key(), 'work_ref': self.work()['work_ref'], 'command': command}))

    def stop(self, ref, memory=None):
        return self.value((memory or self.memory).stop_reference({'key': self.key(), 'source_ref': ref}, session_id='stop-session'))

    def dump(self):
        return '\n'.join(self.conn.iterdump())

    def test_atomic_wait_history_readback_lease_closed_no_extra_budget(self):
        step = self.stage()
        budgets = self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY goal,kind').fetchall()
        receipt = self.value(self.tasks.ask(self.request))
        self.assertEqual(set(receipt), {'question_id', 'state', 'work_ref'})
        self.assertEqual(receipt['state'], 'waiting_input')
        self.assertEqual(receipt['work_ref'], self.lease['work_ref'])
        self.assertEqual(self.work()['open_questions'], [{'id': receipt['question_id'], 'text': self.request['question'], 'revision': 1}])
        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease WHERE id=?', (self.lease['lease_id'],)).fetchone()[0], 0)
        saved = loads(self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (step['step_id'],)).fetchone()[0])
        self.assertEqual((saved['status'], saved['result_refs']), ('finished', []))
        self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY goal,kind').fetchall(), budgets)
        events = self.value(EventReader(self.conn).get_events({'session_id': 'session'}))['events']
        questions = [e for e in events if e['kind'] == 'question']
        self.assertEqual(len(questions), 1)
        self.assertEqual((questions[0]['text'], questions[0]['refs']), (self.request['question'], [self.origin]))
        self.error(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.lease['work_ref'], 'outcome': 'yield', 'reason': 'after ask'}), 'denied')
        self.assertEqual(self.value(self.tasks.claim({'runner_id': 'other'})), {'status': 'empty'})

    def test_answer_optional_link_and_claim_replay_not_consumed(self):
        receipt = self.ask()
        request = self.answer_request(receipt)
        answer_ref = request['command']['answer_record_ref']
        before = self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY goal,kind').fetchall()
        result = self.value(self.tasks.control(request))
        self.assertEqual((result['state'], result['control_status']), ('queued', 'none'))
        self.assertEqual(self.work()['open_questions'], [])
        self.lease = self.value(self.tasks.claim({'runner_id': 'next'}))
        expected = [{'question_id': receipt['question_id'], 'step_id': self.request['step_id'], 'answer_record_ref': answer_ref}]
        self.assertEqual(self.lease['pending_inputs'], expected)
        self.assertEqual(self.value(self.tasks.claim({'runner_id': 'next'}))['pending_inputs'], expected)
        self.assertEqual(self.lease['checkpoint']['open_question_refs'], [])
        context = self.value(self.tasks.get_execution_context({'lease_id': self.lease['lease_id'], 'work_ref': self.lease['work_ref']}))
        self.assertNotIn(answer_ref, context['required_refs'])
        self.assertIn(answer_ref, context['optional_refs'])
        self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY goal,kind').fetchall(), before)

    def test_historical_ask_and_answer_replay_and_changed_input_conflict(self):
        receipt = self.ask()
        request = self.answer_request(receipt)
        answered = self.value(self.tasks.control(request))
        self.assertEqual(self.value(self.tasks.ask(self.request)), receipt)
        self.assertEqual(self.value(self.tasks.get_question_by_key({'key': self.request['key']})), receipt)
        self.assertEqual(self.value(self.tasks.control(request)), answered)
        self.error(self.tasks.ask({**self.request, 'question': 'different'}), 'conflict')
        self.error(self.tasks.control({**request, 'key': 'new answer key'}), 'conflict')
        changed = copy.deepcopy(request); changed['work_ref']['epoch'] += 1
        self.error(self.tasks.control(changed), 'conflict')
        self.stop(request['command']['answer_record_ref'])
        self.assertEqual(self.value(self.tasks.control(request)), answered)

    def test_pause_answer_resume_and_cancel_do_not_revive_question(self):
        receipt = self.ask()
        self.assertEqual(self.control('pause')['state'], 'paused')
        self.assertEqual(self.control('resume')['state'], 'waiting_input')
        self.control('pause')
        self.assertEqual(self.value(self.tasks.control(self.answer_request(receipt)))['state'], 'paused')
        self.assertEqual(self.control('resume')['state'], 'queued')
        self.lease = self.value(self.tasks.claim({'runner_id': 'next'}))
        second = self.ask()
        request = self.answer_request(second)
        self.assertEqual(self.control('cancel')['state'], 'cancelled')
        self.assertEqual(self.work()['open_questions'], [])
        self.error(self.tasks.control(request), 'conflict')
        self.assertEqual(self.value(self.tasks.ask(self.request)), second)
        self.assertEqual(self.work()['state'], 'cancelled')

    def test_selected_and_unselected_call_source_stop_close_waiting_question(self):
        for select_extra in (False, True):
            self.setUp()
            receipt = self.ask()
            before = receipt['work_ref']['epoch']
            self.stop(self.extra if select_extra else self.origin)
            current = self.work()
            self.assertEqual(current['state'], 'queued')
            self.assertEqual(current['work_ref']['epoch'], before + 1)
            self.assertEqual(current['open_questions'], [])
            self.assertEqual(self.value(self.tasks.get_question_by_key({'key': self.request['key']})), receipt)

    def test_historical_optional_stop_retains_question_and_waiting_or_paused(self):
        self.call([self.origin, self.history])
        previous = self.value(self.tasks.begin_step({'key': self.key(), 'work_ref': self.lease['work_ref'], 'action': {'kind': 'report', 'summary': 'history'}}))
        self.value(self.tasks.finish_step({'work_ref': self.lease['work_ref'], 'step_id': previous['step_id'], 'result_refs': []}))
        self.value(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.lease['work_ref'], 'outcome': 'yield', 'reason': 'next epoch'}))
        self.lease = self.value(self.tasks.claim({'runner_id': 'runner'}))
        receipt = self.ask()
        self.control('pause')
        self.stop(self.history)
        self.assertEqual(self.work()['state'], 'paused')
        self.assertEqual(self.work()['open_questions'][0]['id'], receipt['question_id'])
        self.assertEqual(self.control('resume')['state'], 'waiting_input')
        self.value(self.tasks.control(self.answer_request(receipt)))
        self.assertEqual(self.work()['state'], 'queued')

    def test_answer_stop_invalidates_without_reopening_and_multiple_links_ordered(self):
        first = self.ask(); answer1 = self.answer_request(first)
        self.value(self.tasks.control(answer1))
        self.lease = self.value(self.tasks.claim({'runner_id': 'next'}))
        second = self.ask(); answer2 = self.answer_request(second)
        self.value(self.tasks.control(answer2))
        self.stop(answer1['command']['answer_record_ref'])
        self.assertEqual(self.work()['open_questions'], [])
        self.lease = self.value(self.tasks.claim({'runner_id': 'final'}))
        self.assertEqual([link['question_id'] for link in self.lease['pending_inputs']], [first['question_id'], second['question_id']])
        self.assertEqual(self.lease['pending_inputs'][0]['answer_record_ref'], answer1['command']['answer_record_ref'])

    def test_duplicate_selected_refs_preserved_and_ordinary_finish_refused(self):
        step = self.stage(selected=[self.origin, self.origin])
        self.error(self.tasks.finish_step({'work_ref': self.lease['work_ref'], 'step_id': step['step_id'], 'result_refs': []}), 'conflict')
        receipt = self.value(self.tasks.ask(self.request))
        self.assertEqual(self.value(self.tasks.ask(self.request)), receipt)
        self.error(self.tasks.ask({**self.request, 'source_refs': [self.origin]}), 'conflict')

    def test_closed_invalid_inputs_and_wrong_action_or_step_do_not_burn_key(self):
        step = self.stage()
        for request in ({**self.request, 'extra': 1}, {**self.request, 'key': ''},
                        {**self.request, 'question': '\ud800'}, {**self.request, 'source_refs': [{'kind': 'artifact', 'id': 'a'}]}):
            self.error(self.tasks.ask(request), 'invalid_input')
        self.error(self.tasks.ask({**self.request, 'step_id': 'absent'}), 'not_found')
        self.error(self.tasks.ask({**self.request, 'question': 'valid but different'}), 'conflict')
        self.error(self.tasks.get_question_by_key({'key': self.request['key']}), 'not_found')
        self.value(self.tasks.ask(self.request))

    def test_answer_missing_foreign_question_old_revision_and_nonrecord(self):
        receipt = self.ask(); request = self.answer_request(receipt)
        missing = copy.deepcopy(request); missing['command']['question_id'] = 'absent'
        self.error(self.tasks.control(missing), 'not_found')
        old = copy.deepcopy(request); old['work_ref']['revision'] += 1
        self.error(self.tasks.control(old), 'stale')
        wrong = copy.deepcopy(request); wrong['command']['answer_record_ref'] = {'kind': 'artifact', 'id': 'a'}
        self.error(self.tasks.control(wrong), 'invalid_input')
        self.stop(request['command']['answer_record_ref'])
        self.error(self.tasks.control(request), 'denied')
        self.assertEqual(self.work()['state'], 'waiting_input')

    def test_foreign_question_cannot_answer_a_different_waiting_work(self):
        original = self.ask()
        self.value(self.tasks.create({'key': 'other-work', 'session_id': 'session',
            'origin_record_ref': self.origin, 'brief': {'purpose': 'another question',
                'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                'constraints': [], 'conditions': [{'description': 'saved', 'check': 'artifact_saved'}],
                'context_refs': []}}, request_scope=self.grant))
        self.lease = self.value(self.tasks.claim({'runner_id': 'other-runner'}))
        foreign = self.ask()
        self.error(self.tasks.control(self.answer_request(foreign)), 'not_found')
        self.assertEqual(self.work()['open_questions'][0]['id'], original['question_id'])

    def test_ask_post_write_faults_and_baseexception_leave_no_partial_key(self):
        self.stage(); before = self.dump()
        for failure, position in ((RuntimeError, 1), (RuntimeError, 3), (KeyboardInterrupt, 2), (SystemExit, 4)):
            self.conn.fault, self.conn.writes_until_fault = failure, position
            if issubclass(failure, Exception):
                self.error(self.tasks.ask(self.request), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.tasks.ask(self.request)
            self.assertIsNone(self.conn.fault, 'must reach an actual write')
            self.assertFalse(self.conn.in_transaction)
            self.assertEqual(self.dump(), before)
            self.error(self.tasks.get_question_by_key({'key': self.request['key']}), 'not_found')
        self.value(self.tasks.ask(self.request))

    def test_answer_post_write_failure_preserves_open_question_and_memory(self):
        receipt = self.ask(); request = self.answer_request(receipt); before = self.dump()
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            self.conn.fault, self.conn.writes_until_fault = failure, 2
            if issubclass(failure, Exception):
                self.error(self.tasks.control(request), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.tasks.control(request)
            self.assertIsNone(self.conn.fault)
            self.assertEqual(self.dump(), before)
            self.assertFalse(self.conn.in_transaction)
        self.value(self.tasks.control(request))

    def test_sql_index_and_call_binding_corruption_fail_closed(self):
        step = self.stage(); before = self.dump()
        original = self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (step['step_id'],)).fetchone()[0]
        for change in ({'index': True}, {'index': step['index'] + 1}, {'status': 'mystery'}):
            wire = loads(original); wire.update(change)
            self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(wire), step['step_id']))
            self.error(self.tasks.ask(self.request), 'unavailable')
            self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (original, step['step_id']))
        self.conn.execute("UPDATE v5_tsk_call SET status='mystery' WHERE id=?", (self.call_id,))
        self.error(self.tasks.ask(self.request), 'unavailable')
        self.conn.execute("UPDATE v5_tsk_call SET status='returned' WHERE id=?", (self.call_id,))
        self.conn.execute('UPDATE v5_tsk_step SET idx=idx+1 WHERE id=?', (step['step_id'],))
        self.error(self.tasks.ask(self.request), 'unavailable')
        self.conn.execute('UPDATE v5_tsk_step SET idx=idx-1 WHERE id=?', (step['step_id'],))
        self.assertEqual(self.dump(), before)

    def test_admitted_or_unadopted_returned_activity_cannot_close_lease(self):
        self.stage()
        for status in ('admitted', 'returned'):
            self.conn.execute('INSERT INTO v5_tsk_call (id,lease,work,idx,reservation,sources,status,step) '
                'SELECT ?,lease,work,idx+1,reservation,sources,?,NULL FROM v5_tsk_call WHERE id=?',
                ('extra-call', status, self.call_id))
            self.error(self.tasks.ask(self.request), 'conflict')
            self.conn.execute('DELETE FROM v5_tsk_call WHERE id=?', ('extra-call',))
            self.error(self.tasks.get_question_by_key({'key': self.request['key']}), 'not_found')
        self.value(self.tasks.ask(self.request))

    def test_every_current_lease_call_workref_and_status_must_be_valid(self):
        self.stage()
        original = self.conn.execute('SELECT work FROM v5_tsk_call WHERE id=?', (self.call_id,)).fetchone()[0]
        for work in ({}, {**self.lease['work_ref'], 'epoch': True}):
            self.conn.execute('UPDATE v5_tsk_call SET work=? WHERE id=?', (dumps(work), self.call_id))
            self.error(self.tasks.ask(self.request), 'unavailable')
        self.conn.execute('UPDATE v5_tsk_call SET work=? WHERE id=?', (original, self.call_id))
        for status in ('returned', 'raised', 'not_entered'):
            old_work = {**self.lease['work_ref'], 'epoch': self.lease['work_ref']['epoch'] - 1}
            self.conn.execute('INSERT INTO v5_tsk_call (id,lease,work,idx,reservation,sources,status,step) '
                'SELECT ?,lease,?,idx+1,reservation,sources,?,NULL FROM v5_tsk_call WHERE id=?',
                ('old-work-call', dumps(old_work), status, self.call_id))
            result = self.tasks.ask(self.request)
            self.assertFalse(result.ok, result.to_json())
            self.assertIn(result.error.code.value, ('stale', 'unavailable'))
            self.conn.execute('DELETE FROM v5_tsk_call WHERE id=?', ('old-work-call',))
        self.error(self.tasks.get_question_by_key({'key': self.request['key']}), 'not_found')

    def test_two_connection_pause_cancel_and_stop_order_before_ask(self):
        for action, code in (('pause', 'conflict'), ('cancel', 'stale'), ('stop', 'stale')):
            self.setUp(); self.stage()
            other, tasks, memory = self.connect()
            if action == 'stop':
                self.stop(self.extra, memory)
            else:
                self.value(tasks.control({'key': 'other-' + action, 'work_ref': self.lease['work_ref'], 'command': action}))
            self.error(self.tasks.ask(self.request), code)
            self.error(self.tasks.get_question_by_key({'key': self.request['key']}), 'not_found')
            self.assertFalse(other.in_transaction)


if __name__ == '__main__':
    unittest.main()
