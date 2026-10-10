"""Frozen RUN completion seam; synthetic public owners are not integration proof."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import sqlite3
import unittest
from pal.contracts_v5 import Result, dumps
from pal.mock_runner_v5 import MockRunner


def value(result):
    if not result.ok:
        raise AssertionError(result.to_json())
    return result.value.to_json()


class SyntheticOwners:
    """Public TSK/MEM/ART/VER fixtures, deliberately no production persistence."""
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None)
        self.work = {'goal_id': 'g', 'revision': 1, 'epoch': 0}
        self.origin = {'kind': 'record', 'id': 'r'}
        self.artifact = {'kind': 'artifact', 'id': 'a'}
        self.verification = {'kind': 'verification', 'id': 'v'}
        self.steps, self.artifact_refs, self.calls = [], [], {}
        self.requests, self.releases, self.verifies, self.completes, self.reserves = [], [], [], [], []
        self.state, self.context_error, self.readiness_error = 'running', None, None
        self.verify_failure = self.complete_failure = self.release_failure = None
        self.check_status, self.lost_verify, self.lost_complete = 'met', False, False
        self.after_verify = None
        self.completed_receipt = None
        self.brief = {'purpose': 'draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
            'constraints': [], 'conditions': [{'id': 'c', 'description': 'saved', 'check': 'artifact_saved'}],
            'context_refs': []}
        self.grant = {'capabilities': [], 'repositories': ['repo'],
                      'limits': {'max_operations': 0, 'max_steps': 8, 'max_model_calls': 8}}

    def claim(self, request):
        self.requests.append(('claim', copy.deepcopy(request)))
        if self.state == 'completed':
            return Result.success({'status': 'empty'})
        return Result.success({'work_ref': self.work, 'lease_id': 'lease', 'steps': self.steps,
            'checkpoint': {}, 'brief': self.brief, 'grant': self.grant})

    def get_call(self, request):
        self.requests.append(('get_call', copy.deepcopy(request)))
        if self.readiness_error:
            return Result.failure(self.readiness_error, 'synthetic readiness failure')
        return Result.success(self.calls[request['call_id']]) if request['call_id'] in self.calls else Result.failure('not_found', 'absent')

    def get_execution_context(self, request):
        self.requests.append(('execution', copy.deepcopy(request)))
        if self.context_error:
            return Result.failure(self.context_error, 'synthetic latest authority')
        return Result.success({'required_refs': [self.origin], 'optional_refs': [], 'session_id': 's',
            'step_sources': [{'step_id': s['step_id'], 'refs': [self.origin, *s['result_refs']]} for s in self.steps],
            'next_step_index': len(self.steps),
            'remaining_budget': {k: {'work': 8, 'host': 8} for k in ('model', 'step')}})

    def get_work(self, request):
        self.requests.append(('work', copy.deepcopy(request)))
        return Result.success({'work_ref': self.work, 'state': self.state, 'control_status': 'none',
                               'current_artifact_refs': self.artifact_refs})

    def register_sources(self, request):
        return Result.success({})

    def reserve_budget(self, request):
        self.reserves.append(copy.deepcopy(request))
        return Result.success({'reservation_id': 'reservation-' + str(len(self.reserves))})

    def admit_call(self, request):
        self.calls[request['call_id']] = {'status': 'admitted', 'may_enter': True}
        return Result.success({})

    def end_call(self, request):
        self.calls[request['call_id']] = {'status': request['outcome'], 'may_enter': False}
        return Result.success({})

    def begin_step(self, request):
        step = {'step_id': 'step-' + str(len(self.steps)), 'work_ref': self.work,
            'index': len(self.steps), 'action': request['action'], 'status': 'started', 'result_refs': []}
        self.steps.append(step)
        return Result.success(step)

    def finish_step(self, request, **metadata):
        step = next(s for s in self.steps if s['step_id'] == request['step_id'])
        step.update(status='finished', result_refs=request['result_refs'])
        if step['action']['kind'] == 'compose':
            self.artifact_refs.extend(request['result_refs'])
        return Result.success(step)

    def release(self, request):
        self.releases.append(copy.deepcopy(request))
        if self.release_failure:
            return Result.failure(self.release_failure, 'synthetic retained occupancy')
        if self.state == 'completed':
            return Result.failure('denied', 'closed lease')
        self.state = self.state if self.state in ('paused', 'cancelled') else 'queued'
        return Result.success({'work_ref': self.work, 'state': self.state, 'control_status': 'none'})

    def read(self, request, *, purpose):
        return Result.success({'ref': request['ref'], 'content': 'draft source'})

    def save(self, request):
        return Result.success({'artifact_ref': self.artifact, 'hash': 'a' * 64, 'bytes': 5})

    def verify(self, request):
        self.requests.append(('verify', copy.deepcopy(request)))
        self.verifies.append(copy.deepcopy(request))
        if self.after_verify:
            callback, self.after_verify = self.after_verify, None
            callback()
        if self.verify_failure or self.lost_verify:
            self.lost_verify = False
            return Result.failure(self.verify_failure or 'unavailable', 'synthetic lost verification')
        return Result.success(self.receipt())

    def receipt(self):
        return {'verification_ref': self.verification, 'checks': [{'condition_id': 'c',
            'status': self.check_status, 'reason': 'synthetic evaluator', 'evidence_refs': [self.artifact]}]}

    def control(self, request):
        self.completes.append(copy.deepcopy(request))
        if self.completed_receipt:
            return Result.success(self.completed_receipt)
        if self.complete_failure:
            return Result.failure(self.complete_failure, 'synthetic completion failure')
        self.state = 'completed'
        self.completed_receipt = {'work_ref': self.work, 'state': 'completed', 'control_status': 'none'}
        if self.lost_complete:
            self.lost_complete = False
            return Result.failure('unavailable', 'synthetic committed response loss')
        return Result.success(self.completed_receipt)


class MockCompletionTests(unittest.TestCase):
    def setUp(self):
        self.owners = SyntheticOwners()
        self.addCleanup(self.owners.conn.close)
        self.model_inputs = []

    def runner(self, *, enabled=True):
        args = {'artifacts': self.owners}
        if enabled:
            args['verifications'] = self.owners
        return MockRunner(self.owners, self.owners, **args)

    def expert(self, context, **diagnostics):
        self.model_inputs.append(copy.deepcopy(context))
        if len(self.model_inputs) > 1:
            return {'kind': 'report', 'summary': 'bounded next step'}
        return {'kind': 'compose', 'content': 'draft', 'media_type': 'text/plain',
                'source_refs': [self.owners.origin]}

    def error(self, result, code='unavailable'):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)

    def retained_tail(self):
        self.owners.steps = [{'step_id': 'old', 'work_ref': self.owners.work, 'index': 0,
            'action': {'kind': 'compose', 'content': 'draft', 'media_type': 'text/plain',
                       'source_refs': [self.owners.origin]}, 'status': 'finished',
            'result_refs': [self.owners.artifact]}]
        self.owners.artifact_refs = [self.owners.artifact]
        self.owners.calls = {dumps(['C15.call', 'lease', 0]): {'status': 'returned', 'may_enter': False}}

    def test_verifications_without_artifacts_is_invalid_host_configuration(self):
        with self.assertRaises(ValueError):
            MockRunner(self.owners, self.owners, verifications=self.owners)

    def test_default_draft_only_behavior_remains_bounded(self):
        out = value(self.runner(enabled=False).run_once(self.expert))
        self.assertEqual(out['status'], 'released')
        self.assertEqual(self.owners.verifies, [])
        self.assertEqual(self.owners.completes, [])
        self.assertEqual(len(self.model_inputs), 1)

    def test_compose_verify_complete_canonical_keys_receipt_and_no_release(self):
        out = value(self.runner().run_once(self.expert))
        self.assertEqual((out['status'], out['state'], out['control_status']), ('completed', 'completed', 'none'))
        self.assertEqual(out['work_ref'], self.owners.work)
        self.assertEqual(out['lease_id'], 'lease')
        self.assertEqual(out['verification'], self.owners.receipt())
        self.assertEqual(len(out['steps']), 1)
        self.assertEqual(len(out['call_ids']), 1)
        self.assertEqual(out['excluded_refs'], [])
        self.assertEqual(out['excluded_step_ids'], [])
        self.assertEqual(self.owners.verifies, [{'key': dumps(['C09.verify', self.owners.work, [self.owners.artifact]]),
            'work_ref': self.owners.work, 'artifact_refs': [self.owners.artifact]}])
        self.assertEqual(self.owners.completes, [{'key': dumps(['C10.complete', self.owners.work, self.owners.verification]),
            'work_ref': self.owners.work, 'command': {'kind': 'complete', 'verification_ref': self.owners.verification}}])
        self.assertEqual((len(self.model_inputs), len(self.owners.reserves), len(self.owners.releases)), (1, 1, 0))

    def test_nonmet_checks_continue_normal_next_step_with_receipt(self):
        for status in ('unknown', 'unmet'):
            self.setUp()
            self.owners.check_status = status
            out = value(self.runner().run_once(self.expert, max_steps=2))
            self.assertEqual(out['status'], 'released')
            self.assertEqual(out['verification'], self.owners.receipt())
            self.assertEqual(len(self.model_inputs), 2)
            self.assertEqual(len(out['steps']), 2)
            self.assertEqual(self.owners.completes, [])
            self.assertEqual(len(self.owners.releases), 1)

    def test_persistent_verify_unavailable_yields_or_retains_without_inference_repair(self):
        self.owners.verify_failure = 'unavailable'
        out = value(self.runner().run_once(self.expert, max_steps=2))
        self.assertEqual(out['status'], 'released')
        self.assertEqual(len(self.owners.verifies), 3)
        self.assertTrue(all(r == self.owners.verifies[0] for r in self.owners.verifies))
        self.assertEqual((len(self.model_inputs), len(self.owners.releases)), (1, 1))
        self.assertEqual(self.owners.releases[0]['outcome'], 'yield')
        self.assertEqual(self.owners.completes, [])

    def test_verify_unavailable_with_release_refused_retains_occupancy(self):
        self.owners.verify_failure = self.owners.release_failure = 'unavailable'
        self.error(self.runner().run_once(self.expert, max_steps=2))
        self.assertEqual(self.owners.state, 'running')
        self.assertEqual(len(self.owners.verifies), 3)
        self.assertEqual(len(self.model_inputs), 1)
        self.assertEqual(self.owners.releases[0]['outcome'], 'yield')

    def test_malformed_verification_receipt_fails_without_new_inference(self):
        self.owners.verify = lambda request: Result.success({'checks': []})
        self.error(self.runner().run_once(self.expert, max_steps=2))
        self.assertEqual(self.owners.completes, [])
        self.assertEqual(len(self.model_inputs), 1)

    def test_persistent_completion_unavailable_retains_and_reenters_before_inference(self):
        runner = self.runner()
        self.owners.complete_failure = 'unavailable'
        self.error(runner.run_once(self.expert, max_steps=2))
        self.assertEqual(len(self.owners.completes), 3)
        self.assertTrue(all(r == self.owners.completes[0] for r in self.owners.completes))
        self.assertEqual(self.owners.releases, [])
        self.owners.complete_failure = None
        self.assertEqual(value(runner.run_once(self.expert))['status'], 'completed')
        self.assertEqual(len(self.model_inputs), 1)
        self.assertEqual(len(self.owners.reserves), 1)

    def test_commit_lost_completion_response_replays_without_release_or_model(self):
        self.owners.lost_complete = True
        runner = self.runner()
        self.assertEqual(value(runner.run_once(self.expert))['status'], 'completed')
        self.assertEqual(len(self.owners.completes), 2)
        self.assertEqual(self.owners.completes[0], self.owners.completes[1])
        self.assertEqual(self.owners.releases, [])
        self.assertEqual(value(runner.run_once(self.expert))['status'], 'empty')
        self.assertEqual(len(self.model_inputs), 1)

    def test_lost_verification_response_retries_same_identity(self):
        self.owners.lost_verify = True
        self.assertEqual(value(self.runner().run_once(self.expert))['status'], 'completed')
        self.assertEqual(len(self.owners.verifies), 2)
        self.assertEqual(self.owners.verifies[0], self.owners.verifies[1])
        self.assertEqual(len(self.model_inputs), 1)

    def test_retained_finished_compose_tail_finalizes_before_new_inference(self):
        self.retained_tail()
        self.assertEqual(value(self.runner().run_once(self.expert))['status'], 'completed')
        self.assertEqual(self.model_inputs, [])
        self.assertEqual(self.owners.reserves, [])
        order = [kind for kind, request in self.owners.requests]
        self.assertLess(order.index('get_call'), order.index('verify'))

    def test_started_step_or_existing_next_call_blocks_entry_finalization(self):
        self.retained_tail()
        self.owners.steps[0]['status'] = 'started'
        value(self.runner().run_once(self.expert))
        self.assertEqual(self.owners.verifies, [])
        self.owners.steps[0]['status'] = 'finished'
        self.owners.calls[dumps(['C15.call', 'lease', 1])] = {'status': 'admitted', 'may_enter': False}
        value(self.runner().run_once(self.expert))
        self.assertEqual(self.owners.verifies, [])
        self.assertEqual(self.model_inputs, [])

    def test_readiness_failure_prevents_finalization(self):
        self.retained_tail()
        self.owners.readiness_error = 'unavailable'
        value(self.runner().run_once(self.expert))
        self.assertEqual(self.owners.verifies, [])
        self.assertEqual(self.model_inputs, [])

    def test_noncompose_or_nontail_history_does_not_finalize_at_entry(self):
        self.retained_tail()
        self.owners.steps[0]['action'] = {'kind': 'report', 'summary': 'historical'}
        self.model_inputs = [{}]
        value(self.runner().run_once(self.expert))
        self.assertEqual(self.owners.verifies, [])
        self.retained_tail()
        self.owners.artifact_refs.append({'kind': 'artifact', 'id': 'newer'})
        value(self.runner().run_once(self.expert))
        self.assertEqual(self.owners.verifies, [])

    def test_latest_pause_cancel_or_source_stop_fences_completion_then_execution(self):
        for state, code in (('paused', 'conflict'), ('cancelled', 'stale'), ('queued', 'denied')):
            self.setUp()
            def latest_control():
                self.owners.state, self.owners.complete_failure, self.owners.context_error = state, code, code
            self.owners.after_verify = latest_control
            out = value(self.runner().run_once(self.expert, max_steps=2))
            self.assertEqual(out['state'], state)
            self.assertEqual(len(self.model_inputs), 1)
            self.assertEqual(len(self.owners.releases), 1)
            self.assertEqual(len(self.owners.completes), 1)

    def test_verification_ref_never_enters_model_context_or_step_results(self):
        self.owners.check_status = 'unknown'
        value(self.runner().run_once(self.expert, max_steps=2))
        for context in self.model_inputs:
            self.assertNotIn(dumps(self.owners.verification), dumps(context))
        self.assertTrue(all(self.owners.verification not in s['result_refs'] for s in self.owners.steps))
        self.assertEqual([s['action']['kind'] for s in self.owners.steps], ['compose', 'report'])


if __name__ == '__main__':
    unittest.main()
