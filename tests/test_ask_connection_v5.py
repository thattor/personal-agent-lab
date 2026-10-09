"""ASK01 through actual temporary MEM/TSK/ART/VER public owner boundaries."""
import copy
import unittest

from pal.contracts_v5 import Result, dumps
from pal.host_read_v5 import HostReader
from pal.events_v5 import EventReader
from pal.mock_runner_v5 import MockRunner
from pal.read_consumer_v5 import inspect_session
import test_completion_connection_v5 as fixture


class AskBoundary:
    def __init__(self, owner, mode):
        self.owner, self.mode = owner, mode
        self.requests, self.releases, self.lookups = [], [], []

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def ask(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.mode == 'before':
            return Result.failure('unavailable', 'injected before owner write')
        result = self.owner.ask(request)
        if self.mode == 'after' and result.ok:
            return Result.failure('unavailable', 'injected lost owner reply')
        return result

    def get_question_by_key(self, request):
        self.lookups.append(copy.deepcopy(request))
        return self.owner.get_question_by_key(request)

    def release(self, request):
        self.releases.append(copy.deepcopy(request))
        return self.owner.release(request)


class AskConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CompletionConnectionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.stage()
        self.f.value(self.f.tasks.release({'lease_id': self.f.lease['lease_id'],
            'work_ref': self.f.work, 'outcome': 'yield', 'reason': 'test runner handoff'}))
        self.inputs = []
        self.runner = MockRunner(self.f.tasks, self.f.memory,
            artifacts=self.f.artifacts, verifications=self.f.verifications)

    def ask(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        return {'kind': 'ask', 'question': '必要な日時は？', 'missing_fact': '日時',
                'source_refs': [self.f.refs[0]]}

    def waiting(self, runner=None):
        output = self.f.value((runner or self.runner).run_once(self.ask))
        self.assertEqual((output['status'], output['state']), ('waiting', 'waiting_input'))
        return output

    def answer(self, waiting, text='10月12日午後2時'):
        ref = self.f.value(self.f.memory.append({'client_key': 'answer-' + waiting['question_id'],
            'session_id': 'draft-session', 'role': 'user', 'text': text}))['record_ref']
        request = {'key': 'answer-' + waiting['question_id'], 'work_ref': waiting['work_ref'],
            'command': {'kind': 'answer', 'question_id': waiting['question_id'],
                        'answer_record_ref': ref}}
        result = self.f.value(self.f.tasks.control(request))
        return ref, request, result

    def link(self, waiting, ref):
        return {'question_id': waiting['question_id'], 'step_id': waiting['step_id'],
                'answer_record_ref': ref}

    def compose(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        return {'kind': 'compose', 'content': '回答を用いた保存下書き', 'media_type': 'text/plain',
                'source_refs': [item['ref'] for item in context['context']]}

    def test_two_questions_keep_distinct_answer_links_and_finish_same_goal(self):
        first = self.waiting()
        one, _, _ = self.answer(first)
        second = self.waiting()
        self.assertEqual(self.inputs[1]['pending_inputs'], [self.link(first, one)])
        two, request, receipt = self.answer(second, '会議室B')
        done = self.f.value(self.runner.run_once(self.compose))
        self.assertEqual(done['status'], 'completed')
        self.assertEqual(done['work_ref']['goal_id'], first['work_ref']['goal_id'])
        self.assertGreater(done['work_ref']['epoch'], second['work_ref']['epoch'])
        self.assertEqual(self.inputs[-1]['pending_inputs'], [self.link(first, one), self.link(second, two)])
        self.assertEqual(self.f.usage(), {'model': 3, 'step': 3})
        self.assertEqual(self.f.value(self.f.tasks.control(request)), receipt)
        reader = HostReader(self.f.memory, self.f.artifacts, self.f.verifications)
        inspection = self.f.value(inspect_session({'session_id': 'draft-session'},
            events=EventReader(self.f.conn), tasks=self.f.tasks, reader=reader))
        self.assertTrue(inspection['items'])
        self.assertEqual(inspection['items'][0]['work']['value']['state'], 'completed')

    def test_waiting_frees_capacity_for_another_goal(self):
        waiting = self.waiting()
        next_work = self.f.create_next()
        claim = self.f.value(self.f.tasks.claim({'runner_id': 'other-runner'}))
        self.assertEqual(claim['work_ref']['goal_id'], next_work['goal_id'])
        self.assertEqual(self.f.current()['state'], 'waiting_input')
        self.assertEqual(self.f.current()['open_questions'][0]['id'], waiting['question_id'])

    def test_reconnected_owner_recovers_question_and_answer_replay_is_history(self):
        waiting = self.waiting()
        _, tasks, _, _, _ = self.f.connect()
        opened = self.f.value(tasks.get_work({'goal_id': self.f.work['goal_id']}))
        self.assertEqual(opened['open_questions'][0]['id'], waiting['question_id'])
        _, request, receipt = self.answer(waiting)
        snapshot = self.f.snapshot()
        self.assertEqual(self.f.value(tasks.control(request)), receipt)
        self.assertEqual(snapshot, self.f.snapshot())

    def test_lost_committed_ask_response_recovers_by_key_without_reinference(self):
        boundary = AskBoundary(self.f.tasks, 'after')
        runner = MockRunner(boundary, self.f.memory)
        waiting = self.waiting(runner)
        self.assertEqual(len(boundary.requests), 3)
        self.assertTrue(all(x == boundary.requests[0] for x in boundary.requests))
        self.assertEqual(boundary.lookups, [{'key': boundary.requests[0]['key']}])
        self.assertEqual(boundary.releases, [])
        self.assertEqual((len(self.inputs), self.f.usage()), (1, {'model': 1, 'step': 1}))
        self.assertEqual(len([e for e in self.f.events() if e['kind'] == 'question']), 1)
        self.assertEqual(self.f.current()['open_questions'][0]['id'], waiting['question_id'])

    def test_uncommitted_tail_is_retried_locally_without_another_model_call(self):
        boundary = AskBoundary(self.f.tasks, 'before')
        runner = MockRunner(boundary, self.f.memory)
        self.f.error(runner.run_once(self.ask), 'unavailable')
        self.assertEqual(self.f.current()['state'], 'running')
        boundary.mode = None
        waiting = self.waiting(runner)
        self.assertEqual(boundary.requests[0], boundary.requests[-1])
        self.assertEqual((len(self.inputs), self.f.usage()), (1, {'model': 1, 'step': 1}))
        self.assertEqual(self.f.current()['open_questions'][0]['id'], waiting['question_id'])

    def test_stopping_one_answer_excludes_derived_question_link_without_losing_other_record(self):
        first = self.waiting()
        one, _, _ = self.answer(first)
        second = self.waiting()
        two, _, _ = self.answer(second, '会議室B')
        self.f.value(self.f.stop(self.f.memory, one))
        done = self.f.value(self.runner.run_once(self.compose))
        self.assertEqual(done['status'], 'completed')
        supplied = self.inputs[-1]
        refs = [item['ref'] for item in supplied['context']]
        self.assertNotIn(one, refs)
        self.assertIn(two, refs)
        self.assertNotIn('pending_inputs', supplied)
        self.assertIn(one, done['excluded_refs'])
        self.assertIn(second['step_id'], done['excluded_step_ids'])
        self.assertEqual(done['pending_inputs'], [self.link(first, one), self.link(second, two)])


if __name__ == '__main__':
    unittest.main()
