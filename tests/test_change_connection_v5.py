"""CHANGE01 through actual temporary owners and explicit SQLite commit order."""
import copy
import unittest

from pal.contracts_v5 import dumps, loads
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.mock_runner_v5 import MockRunner
from pal.read_consumer_v5 import inspect_session
import test_completion_connection_v5 as fixture


class ChangeConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CompletionConnectionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.stage()
        self.runner = MockRunner(self.f.tasks, self.f.memory,
            artifacts=self.f.artifacts, verifications=self.f.verifications)
        self.inputs = []
        self.origin = self.f.value(self.f.memory.append({
            'client_key': 'correction', 'session_id': 'draft-session', 'role': 'user',
            'text': '訂正：議事メモの下書きを新しい内容で保存する。送信しない。'}))['record_ref']

    def request(self, *, refs=(), work=None, key='change'):
        # This fixture is the trusted host: it declares every reused record.
        return {'key': key, 'work_ref': copy.deepcopy(work or self.f.current()['work_ref']),
            'command': {'kind': 'change', 'origin_record_ref': self.origin, 'brief': {
                'purpose': '訂正版の議事メモを保存する',
                'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                'constraints': ['送信しない'], 'context_refs': list(refs),
                'conditions': [{'description': '訂正版の下書きが保存されている',
                                'check': 'artifact_saved'}]}}}

    def changed(self, **kwargs):
        request = self.request(**kwargs)
        return request, self.f.value(self.f.tasks.control(request))

    def old_release(self, *, outcome='yield'):
        return {'lease_id': self.f.lease['lease_id'], 'work_ref': self.f.work,
                'outcome': outcome, 'reason': 'old call has ceased'}

    def admit(self):
        reservation = self.f.value(self.f.tasks.reserve_budget({'key': 'model',
            'work_ref': self.f.work, 'kind': 'model', 'role': 'expert'}))
        request = {'call_id': dumps(['C15.call', self.f.lease['lease_id'], 0]),
            'lease_id': self.f.lease['lease_id'], 'work_ref': self.f.work,
            'reservation_id': reservation['reservation_id'], 'source_refs': self.f.refs}
        return request

    def started(self, kind='report'):
        admitted = self.admit()
        self.f.value(self.f.tasks.admit_call(admitted))
        self.f.value(self.f.tasks.end_call({'call_id': admitted['call_id'], 'outcome': 'returned'}))
        action = ({'kind': 'report', 'summary': 'Old result'} if kind == 'report' else
                  {'kind': 'compose', 'content': '旧revisionの保存候補',
                   'media_type': 'text/plain', 'source_refs': [self.f.refs[0]]})
        return self.f.value(self.f.tasks.begin_step({'key': 'begin',
            'work_ref': self.f.work, 'action': action}))

    def artifact_request(self, step):
        return {'key': 'old-artifact', 'work_ref': self.f.work,
                'step_id': step['step_id'],
                **{k: v for k, v in step['action'].items() if k != 'kind'}}

    def waiting(self):
        self.f.value(self.f.tasks.release(self.old_release()))
        def ask(context, **diagnostics):
            self.inputs.append(copy.deepcopy(context))
            return {'kind': 'ask', 'question': '日時は？', 'missing_fact': '日時',
                    'source_refs': [self.f.refs[0]]}
        output = self.f.value(self.runner.run_once(ask))
        self.assertEqual(output['status'], 'waiting')
        return output

    def compose(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        self.assertNotIn('pending_inputs', context)
        self.assertEqual(context['work_ref']['revision'], 2)
        self.assertEqual([body['ref'] for body in context['context']], [self.origin])
        return {'kind': 'compose', 'content': '訂正版の議事メモ（下書き）',
                'media_type': 'text/plain', 'source_refs': [self.origin]}

    def test_actual_callable_change_fences_output_keeps_occupancy_then_finishes_replacement(self):
        self.f.value(self.f.tasks.release(self.old_release()))
        _, tasks, _, _, _ = self.f.connect()
        before_calls = []
        def old_expert(context, **diagnostics):
            before_calls.append(copy.deepcopy(context))
            changed = self.f.value(tasks.control(self.request(work=context['work_ref'])))
            self.assertEqual(changed['state'], 'running')
            self.assertEqual(changed['control_status'], 'draining')
            self.assertEqual(self.f.conn.execute('SELECT active FROM v5_tsk_lease WHERE active=1').fetchall(), [(1,)])
            lease = self.f.conn.execute('SELECT id FROM v5_tsk_lease WHERE active=1').fetchone()[0]
            self.f.error(tasks.release({'lease_id': lease, 'work_ref': context['work_ref'],
                'outcome': 'yield', 'reason': 'too early'}), 'conflict')
            return {'kind': 'compose', 'content': 'must never be saved',
                    'media_type': 'text/plain', 'source_refs': [self.f.refs[0]]}
        settled = self.f.value(self.runner.run_once(old_expert))
        self.assertEqual((settled['status'], settled['state']), ('released', 'queued'))
        self.assertEqual(settled['work_ref']['revision'], 2)
        self.assertEqual(len(before_calls), 1)
        self.assertEqual(self.f.usage(), {'model': 1})
        self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0], 0)
        self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_tsk_step').fetchone()[0], 0)
        completed = self.f.value(self.runner.run_once(self.compose))
        self.assertEqual((completed['status'], completed['work_ref']['revision']), ('completed', 2))
        self.assertEqual(completed['work_ref']['goal_id'], self.f.work['goal_id'])
        self.assertEqual(self.f.usage(), {'model': 2, 'step': 1})
        history = self.f.value(self.f.tasks.get_work({'goal_id': self.f.work['goal_id'], 'revision': 1}))
        self.assertEqual(history['state'], 'superseded')
        inspection = self.f.value(inspect_session({'session_id': 'draft-session'},
            events=EventReader(self.f.conn), tasks=self.f.tasks,
            reader=HostReader(self.f.memory, self.f.artifacts, self.f.verifications)))
        self.assertTrue(any(item['work']['value']['state'] == 'completed'
                            for item in inspection['items'] if item.get('work', {}).get('ok')))

    def test_waiting_question_and_receipt_remain_history_without_old_answer_adoption(self):
        waiting = self.waiting()
        question_key = dumps(['C04.ask', waiting['work_ref'], waiting['step_id']])
        receipt = self.f.value(self.f.tasks.get_question_by_key({'key': question_key}))
        self.changed()
        historical = self.f.value(self.f.tasks.get_work({'goal_id': self.f.work['goal_id'], 'revision': 1}))
        self.assertEqual((historical['state'], historical['open_questions']), ('superseded', []))
        self.assertEqual(self.f.conn.execute('SELECT status FROM v5_tsk_question').fetchall(), [('superseded',)])
        self.assertEqual(self.f.value(self.f.tasks.get_question_by_key({'key': question_key})), receipt)
        answer = self.f.value(self.f.memory.append({'client_key': 'late-answer',
            'session_id': 'draft-session', 'role': 'user', 'text': '月曜日'}))['record_ref']
        before = self.f.snapshot()
        self.f.error(self.f.tasks.control({'key': 'late-answer', 'work_ref': waiting['work_ref'],
            'command': {'kind': 'answer', 'question_id': waiting['question_id'],
                        'answer_record_ref': answer}}), 'stale')
        self.assertEqual(before, self.f.snapshot())
        self.assertEqual(self.f.value(self.runner.run_once(self.compose))['status'], 'completed')

    def test_artifact_and_verification_history_never_enter_new_current_set(self):
        self.f.compose()
        verification = self.f.verify()
        old_complete = self.f.complete_request(verification)
        old_artifact = self.f.value(self.f.artifacts.read({'ref': self.f.saved_refs[0]}, purpose='user_view'))
        saved_ver = self.f.conn.execute('SELECT record_json FROM v5_ver_body').fetchall()
        _, tasks, _, artifacts, verifications = self.f.connect()
        self.f.value(tasks.control(self.request()))
        before = self.f.snapshot()
        self.f.error(tasks.control(old_complete), 'stale')
        self.assertEqual(before, self.f.snapshot())
        self.assertEqual(self.f.value(artifacts.read({'ref': self.f.saved_refs[0]}, purpose='user_view')), old_artifact)
        self.assertEqual(self.f.value(verifications.get_by_key({'key': 'verify'})), verification)
        self.assertEqual(self.f.conn.execute('SELECT record_json FROM v5_ver_body').fetchall(), saved_ver)
        old = self.f.value(tasks.get_work({'goal_id': self.f.work['goal_id'], 'revision': 1}))
        self.assertEqual(old['current_artifact_refs'], self.f.saved_refs)
        self.assertEqual(self.f.current()['current_artifact_refs'], [])
        self.assertEqual(self.f.value(tasks.release(self.old_release()))['state'], 'queued')
        new_claim = self.f.value(tasks.claim({'runner_id': 'new-runner'}))
        self.assertEqual((new_claim['steps'], new_claim['pending_inputs']), ([], []))
        checked = self.f.value(verifications.verify({'key': 'new-empty',
            'work_ref': new_claim['work_ref'], 'artifact_refs': []}))
        self.assertEqual([row['status'] for row in checked['checks']], ['unmet'])
        self.assertNotEqual(checked['checks'][0]['condition_id'], verification['checks'][0]['condition_id'])

    def test_admission_commit_order_fences_old_reservation_without_refund(self):
        for admit_first in (True, False):
            with self.subTest(admit_first=admit_first):
                if not admit_first:
                    self.setUp()
                request = self.admit()
                _, tasks, _, _, _ = self.f.connect()
                if admit_first:
                    self.f.value(self.f.tasks.admit_call(request))
                self.f.value(tasks.control(self.request()))
                if admit_first:
                    self.f.error(tasks.release(self.old_release()), 'conflict')
                    self.assertFalse(self.f.value(tasks.get_call({'call_id': request['call_id']}))['may_enter'])
                    self.f.value(tasks.end_call({'call_id': request['call_id'], 'outcome': 'not_entered'}))
                else:
                    before = self.f.snapshot()
                    self.f.error(self.f.tasks.admit_call(request), 'stale')
                    self.assertEqual(before, self.f.snapshot())
                self.assertEqual(self.f.usage(), {'model': 1})
                self.assertEqual(self.f.value(tasks.release(self.old_release()))['state'], 'queued')

    def test_finish_commit_order_retains_or_abandons_only_old_step(self):
        for finish_first in (True, False):
            with self.subTest(finish_first=finish_first):
                if not finish_first:
                    self.setUp()
                step = self.started()
                request = {'work_ref': self.f.work, 'step_id': step['step_id'], 'result_refs': []}
                _, tasks, _, _, _ = self.f.connect()
                if finish_first:
                    self.f.value(self.f.tasks.finish_step(request))
                self.f.value(tasks.control(self.request()))
                if not finish_first:
                    before = self.f.snapshot()
                    self.f.error(self.f.tasks.finish_step(request), 'stale')
                    self.assertEqual(before, self.f.snapshot())
                self.f.value(tasks.release(self.old_release()))
                retained = loads(self.f.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',
                                                     (step['step_id'],)).fetchone()[0])
                self.assertEqual(retained['status'], 'finished' if finish_first else 'abandoned')

    def test_artifact_save_commit_order_preserves_receipt_or_rejects_fresh_stale_write(self):
        for save_first in (True, False):
            with self.subTest(save_first=save_first):
                if not save_first:
                    self.setUp()
                step = self.started('compose')
                request = self.artifact_request(step)
                _, tasks, _, artifacts, _ = self.f.connect()
                if save_first:
                    receipt = self.f.value(self.f.artifacts.save(request))
                self.f.value(tasks.control(self.request()))
                before = self.f.snapshot()
                if save_first:
                    self.assertEqual(self.f.value(artifacts.save(request)), receipt)
                    self.assertEqual(self.f.value(artifacts.get_by_key({'key': request['key']})), receipt)
                else:
                    self.f.error(artifacts.save(request), 'stale')
                self.assertEqual(before, self.f.snapshot())
                self.assertEqual(self.f.current()['current_artifact_refs'], [])

    def test_verification_save_commit_order_keeps_original_record_or_denies_new_stale_check(self):
        for verify_first in (True, False):
            with self.subTest(verify_first=verify_first):
                if not verify_first:
                    self.setUp()
                self.f.compose()
                request = self.f.request()
                _, tasks, _, _, verifications = self.f.connect()
                if verify_first:
                    receipt = self.f.verify()
                self.f.value(tasks.control(self.request()))
                before = self.f.snapshot()
                if verify_first:
                    self.assertEqual(self.f.value(verifications.verify(request)), receipt)
                else:
                    self.f.error(verifications.verify(request), 'stale')
                self.assertEqual(before, self.f.snapshot())

    def test_complete_commit_order_prevents_terminal_change_or_stale_completion(self):
        for complete_first in (True, False):
            with self.subTest(complete_first=complete_first):
                if not complete_first:
                    self.setUp()
                self.f.compose()
                receipt = self.f.verify()
                request = self.f.complete_request(receipt)
                change = self.request()
                _, tasks, _, _, _ = self.f.connect()
                if complete_first:
                    self.f.value(self.f.tasks.control(request))
                    before = self.f.snapshot()
                    self.f.error(tasks.control(change), 'conflict')
                    self.assertEqual(self.f.current()['state'], 'completed')
                else:
                    self.f.value(tasks.control(change))
                    before = self.f.snapshot()
                    self.f.error(self.f.tasks.control(request), 'stale')
                    self.assertEqual(self.f.current()['state'], 'running')
                self.assertEqual(before, self.f.snapshot())

    def test_answer_commit_order_preserves_answered_history_or_rejects_superseded_question(self):
        for answer_first in (True, False):
            with self.subTest(answer_first=answer_first):
                if not answer_first:
                    self.setUp()
                waiting = self.waiting()
                answer = self.f.value(self.f.memory.append({'client_key': 'answer',
                    'session_id': 'draft-session', 'role': 'user', 'text': '月曜日'}))['record_ref']
                request = {'key': 'answer', 'work_ref': waiting['work_ref'], 'command': {
                    'kind': 'answer', 'question_id': waiting['question_id'], 'answer_record_ref': answer}}
                _, tasks, _, _, _ = self.f.connect()
                if answer_first:
                    receipt = self.f.value(self.f.tasks.control(request))
                self.f.value(tasks.control(self.request()))
                before = self.f.snapshot()
                if answer_first:
                    self.assertEqual(self.f.value(tasks.control(request)), receipt)
                else:
                    self.f.error(self.f.tasks.control(request), 'stale')
                self.assertEqual(before, self.f.snapshot())
                self.assertEqual(self.f.conn.execute('SELECT status FROM v5_tsk_question').fetchall(),
                                 [('answered' if answer_first else 'superseded',)])

    def test_old_only_or_declared_shared_source_stop_has_exact_commit_order_effect(self):
        for reuse in (False, True):
            for stop_first in (True, False):
                with self.subTest(reuse=reuse, stop_first=stop_first):
                    if reuse or not stop_first:
                        self.setUp()
                    _, tasks, memory, _, _ = self.f.connect()
                    if stop_first:
                        self.f.value(self.f.stop(memory, self.f.refs[0]))
                    request = self.request(refs=[self.f.refs[0]] if reuse else [])
                    if reuse and stop_first:
                        before = self.f.snapshot()
                        self.f.error(tasks.control(request), 'denied')
                        self.assertEqual(before, self.f.snapshot())
                    else:
                        changed = self.f.value(tasks.control(request))
                        if not stop_first:
                            self.f.value(self.f.stop(memory, self.f.refs[0]))
                        current = self.f.current()['work_ref']
                        self.assertEqual(current['epoch'], changed['work_ref']['epoch'] + (reuse and not stop_first))

    def test_change_write_lock_blocks_other_connection_effects_before_its_commit(self):
        self.f.compose()
        receipt = self.f.verify()
        _, tasks, memory, _, _ = self.f.connect()
        attempts = []
        gate = self.f.tasks._source_gate
        def source_gate(connection, refs):
            self.assertTrue(connection.in_transaction)
            attempts.append(tasks.control(self.f.complete_request(receipt)))
            attempts.append(self.f.stop(memory, self.f.refs[0]))
            return gate(connection, refs)
        self.f.tasks._source_gate = source_gate
        self.changed()
        self.f.tasks._source_gate = gate
        self.assertEqual(len(attempts), 2)
        for result in attempts:
            self.f.error(result, 'unavailable')
        self.f.error(tasks.control(self.f.complete_request(receipt)), 'stale')
        before = self.f.current()['work_ref']
        self.f.value(self.f.stop(memory, self.f.refs[0]))
        self.assertEqual(self.f.current()['work_ref'], before)


if __name__ == '__main__':
    unittest.main()
