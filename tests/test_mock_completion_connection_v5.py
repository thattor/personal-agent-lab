"""Actual local completion flow with response loss at public owner boundaries."""
import copy
import unittest

from pal.contracts_v5 import Result, dumps
from pal.mock_runner_v5 import MockRunner
import test_completion_connection_v5 as fixture


class ResponseBoundary:
    def __init__(self, owner, method, *, mode=None, after=None):
        self.owner, self.method, self.mode, self.after = owner, method, mode, after
        self.requests, self.releases = [], []

    def __getattr__(self, name):
        return getattr(self.owner, name)

    def release(self, request):
        self.releases.append(copy.deepcopy(request))
        return self.owner.release(request)

    def invoke(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.mode == 'uncommitted':
            return Result.failure('unavailable', 'synthetic unavailable before owner write')
        if self.mode == 'malformed':
            return Result.success({'work_ref': request['work_ref'], 'state': 'running', 'control_status': 'none'})
        result = getattr(self.owner, self.method)(request)
        if self.after:
            callback, self.after = self.after, None
            callback()
        if self.mode in ('lost_once', 'lost_always') and result.ok:
            if self.mode == 'lost_once':
                self.mode = None
            return Result.failure('unavailable', 'synthetic response loss after real owner commit')
        return result

    def control(self, request):
        return self.invoke(request) if self.method == 'control' else self.owner.control(request)

    def verify(self, request):
        return self.invoke(request) if self.method == 'verify' else self.owner.verify(request)


class MockCompletionConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CompletionConnectionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.inputs = []

    def runner(self, *, all_kinds=False, control_mode=None, verify_mode=None, after_verify=None):
        self.f.stage(all_kinds=all_kinds)
        self.f.value(self.f.tasks.release({'lease_id': self.f.lease['lease_id'], 'work_ref': self.f.work,
            'outcome': 'yield', 'reason': 'hand queued work to local runner'}))
        self.tasks = ResponseBoundary(self.f.tasks, 'control', mode=control_mode)
        self.verifications = ResponseBoundary(self.f.verifications, 'verify', mode=verify_mode, after=after_verify)
        return MockRunner(self.tasks, self.f.memory, artifacts=self.f.artifacts, verifications=self.verifications)

    def expert(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        if len(self.inputs) > 1:
            return {'kind': 'report', 'summary': 'bounded continuation'}
        return {'kind': 'compose', 'content': '保存する下書き', 'media_type': 'text/plain',
                'source_refs': [self.f.refs[0]]}

    def assert_completed(self, output):
        self.assertEqual((output['status'], output['state']), ('completed', 'completed'))
        self.assertEqual(self.f.current()['state'], 'completed')
        events = [event for event in self.f.events() if event['kind'] == 'result']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['refs'], self.f.current()['current_artifact_refs'] +
                         [output['verification']['verification_ref']])
        self.assertEqual(self.f.value(self.f.status(output['verification']))['status'], 'valid')

    def test_actual_compose_verify_complete_uses_one_inference_and_no_release(self):
        runner = self.runner()
        out = self.f.value(runner.run_once(self.expert))
        self.assert_completed(out)
        self.assertEqual((len(self.inputs), self.f.usage()), (1, {'model': 1, 'step': 1}))
        self.assertEqual(self.tasks.releases, [])
        self.assertEqual(len(out['steps']), 1)
        self.assertEqual(len(out['call_ids']), 1)
        self.assertEqual(self.tasks.requests[0]['key'],
                         dumps(['C10.complete', out['work_ref'], out['verification']['verification_ref']]))
        self.assertEqual(self.verifications.requests[0]['key'],
                         dumps(['C09.verify', out['work_ref'], self.f.current()['current_artifact_refs']]))
        self.assertEqual(self.f.value(runner.run_once(self.expert))['status'], 'empty')
        self.assertEqual(len(self.inputs), 1)

    def test_unknown_checks_continue_bounded_loop_and_never_enter_model_or_steps(self):
        runner = self.runner(all_kinds=True)
        out = self.f.value(runner.run_once(self.expert, max_steps=2))
        self.assertEqual((out['status'], out['state']), ('released', 'queued'))
        self.assertEqual([check['status'] for check in out['verification']['checks']], ['met', 'unknown', 'unknown'])
        self.assertEqual((len(self.inputs), self.f.usage()), (2, {'model': 2, 'step': 2}))
        self.assertEqual(self.tasks.requests, [])
        ref = out['verification']['verification_ref']
        self.assertTrue(all(dumps(ref) not in dumps(context) for context in self.inputs))
        self.assertTrue(all(ref not in step['result_refs'] for step in out['steps']))
        self.assertFalse(any(event['kind'] == 'result' for event in self.f.events()))

    def test_committed_response_loss_replays_same_completion_once(self):
        runner = self.runner(control_mode='lost_once')
        out = self.f.value(runner.run_once(self.expert))
        self.assert_completed(out)
        self.assertEqual(len(self.tasks.requests), 2)
        self.assertEqual(self.tasks.requests[0], self.tasks.requests[1])
        self.assertEqual(self.tasks.releases, [])
        self.assertEqual(len(self.inputs), 1)

    def test_persistent_committed_response_loss_never_reopens_or_reinvokes_completed_work(self):
        runner = self.runner(control_mode='lost_always')
        self.f.error(runner.run_once(self.expert), 'unavailable')
        self.assertEqual(self.f.current()['state'], 'completed')
        self.assertEqual(self.tasks.releases, [])
        self.assertEqual(len(self.tasks.requests), 3)
        self.assertTrue(all(request == self.tasks.requests[0] for request in self.tasks.requests))
        self.assertEqual(self.f.value(runner.run_once(self.expert))['status'], 'empty')
        next_work = self.f.create_next()
        out = self.f.value(runner.run_once(self.expert))
        self.assertEqual(out['work_ref']['goal_id'], next_work['goal_id'])
        self.assertEqual([context['work_ref']['goal_id'] for context in self.inputs],
                         [self.f.work['goal_id'], next_work['goal_id']])
        self.assertEqual(self.f.current()['state'], 'completed')

    def test_uncommitted_ambiguity_retains_and_finalizes_before_more_inference(self):
        runner = self.runner(control_mode='uncommitted')
        self.f.error(runner.run_once(self.expert, max_steps=2), 'unavailable')
        self.assertEqual(self.f.current()['state'], 'running')
        self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_tsk_lease WHERE active=1').fetchone()[0], 1)
        self.assertEqual(self.tasks.releases, [])
        self.tasks.mode = None
        out = self.f.value(runner.run_once(self.expert))
        self.assert_completed(out)
        self.assertEqual((len(self.inputs), self.f.usage()), (1, {'model': 1, 'step': 1}))
        self.assertEqual(self.tasks.requests[0], self.tasks.requests[-1])
        self.assertEqual(len(out['steps']), 1)
        self.assertEqual(len(out['call_ids']), 1)

    def test_persistent_verification_loss_yields_then_verifies_new_epoch_without_inference(self):
        runner = self.runner(verify_mode='lost_always')
        out = self.f.value(runner.run_once(self.expert, max_steps=2))
        self.assertEqual((out['status'], out['state']), ('released', 'queued'))
        self.assertEqual(len(self.verifications.requests), 3)
        self.assertTrue(all(request == self.verifications.requests[0] for request in self.verifications.requests))
        self.assertEqual(self.tasks.requests, [])
        self.verifications.mode = None
        completed = self.f.value(runner.run_once(self.expert))
        self.assert_completed(completed)
        self.assertGreater(completed['work_ref']['epoch'], out['work_ref']['epoch'])
        self.assertEqual((len(self.inputs), self.f.usage()), (1, {'model': 1, 'step': 1}))

    def test_new_control_after_verification_fences_completion_and_further_inference(self):
        for command, state in (('pause', 'paused'), ('cancel', 'cancelled'), ('stop', 'queued')):
            with self.subTest(command=command):
                if command != 'pause':
                    self.setUp()
                def control():
                    _, tasks, memory, _, _ = self.f.connect()
                    if command == 'stop':
                        self.f.value(self.f.stop(memory, self.f.refs[0]))
                    else:
                        work = self.f.current()['work_ref']
                        self.f.value(tasks.control({'key': command, 'work_ref': work, 'command': command}))
                runner = self.runner(after_verify=control)
                out = self.f.value(runner.run_once(self.expert, max_steps=2))
                self.assertEqual(out['state'], state)
                self.assertEqual(len(self.inputs), 1)
                self.assertEqual(len(self.tasks.releases), 1)
                self.assertFalse(any(event['kind'] == 'result' for event in self.f.events()))

    def test_malformed_successful_completion_receipt_is_not_a_completion_claim(self):
        runner = self.runner(control_mode='malformed')
        self.f.error(runner.run_once(self.expert, max_steps=2), 'unavailable')
        self.assertEqual(self.f.current()['state'], 'running')
        self.assertEqual(len(self.inputs), 1)
        self.assertEqual(self.tasks.releases, [])
        self.assertFalse(any(event['kind'] == 'result' for event in self.f.events()))


if __name__ == '__main__':
    unittest.main()
