"""Frozen ASK01 RUN acceptance using public owner doubles, no real owner DB."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from pal.contracts_v5 import Result, dumps
from pal.mock_runner_v5 import MockRunner
from test_mock_completion_v5 import SyntheticOwners, value


class AskOwners(SyntheticOwners):
    def __init__(self):
        super().__init__()
        self.conn.close()  # Inherited fixture's unused memory connection is not an owner.
        self.pending = []
        self.optional = []
        self.provenance = {}
        self.read_errors = {}
        self.ask_results = []
        self.asks, self.lookups, self.finishes = [], [], []
        self.lookup_result = Result.failure('not_found', 'absent')
        self.receipt_override = None
        self.persisted_action = None

    def claim(self, request):
        result = value(super().claim(request))
        result['pending_inputs'] = copy.deepcopy(self.pending)
        return Result.success(result)

    def get_execution_context(self, request):
        result = super().get_execution_context(request)
        if not result.ok:
            return result
        data = value(result)
        data['optional_refs'] = copy.deepcopy(self.optional)
        data['step_sources'] = [{'step_id': s['step_id'],
                                'refs': self.provenance.get(s['step_id'], [self.origin])}
                               for s in self.steps]
        return Result.success(data)

    def read(self, request, *, purpose):
        error = self.read_errors.get(request['ref']['id'])
        if error:
            return Result.failure(error, 'synthetic source disposition')
        return super().read(request, purpose=purpose)

    def admit_call(self, request):
        self.calls[request['call_id']] = {'call_id': request['call_id'], 'lease_id': 'lease',
            'work_ref': copy.deepcopy(self.work), 'index': len(self.steps),
            'status': 'admitted', 'may_enter': True}
        return Result.success({'call_id': request['call_id'], 'status': 'admitted'})

    def end_call(self, request):
        self.calls[request['call_id']].update(status=request['outcome'], may_enter=False)
        return Result.success({'call_id': request['call_id'], 'status': request['outcome']})

    def begin_step(self, request):
        result = value(super().begin_step(request))
        if self.persisted_action is not None:
            result['action'] = copy.deepcopy(self.persisted_action)
            self.steps[-1]['action'] = copy.deepcopy(self.persisted_action)
        call_id = dumps(['C15.call', 'lease', result['index']])
        self.calls[call_id].update(work_ref=copy.deepcopy(self.work), step_id=result['step_id'])
        return Result.success(result)

    def finish_step(self, request, **metadata):
        self.finishes.append(copy.deepcopy(request))
        return super().finish_step(request, **metadata)

    def ask(self, request):
        if set(request) != {'key', 'work_ref', 'step_id', 'question', 'missing_fact', 'source_refs'}:
            raise AssertionError('C04 request is not closed')
        self.asks.append(copy.deepcopy(request))
        if self.ask_results:
            return self.ask_results.pop(0)
        if self.receipt_override is not None:
            return self.receipt_override
        self.state = 'waiting_input'
        self.steps[-1]['status'] = 'finished'
        return Result.success(self.receipt())

    def receipt(self):
        return {'question_id': 'q', 'state': 'waiting_input', 'work_ref': copy.deepcopy(self.work)}

    def get_question_by_key(self, request):
        self.lookups.append(copy.deepcopy(request))
        return self.lookup_result


class MockAskTests(unittest.TestCase):
    def setUp(self):
        self.o = AskOwners()
        self.inputs = []
        self.runner = MockRunner(self.o, self.o)

    def expert(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        return {'kind': 'ask', 'question': 'Which date?', 'missing_fact': 'date',
                'source_refs': [self.o.origin]}

    def run_ask(self):
        return self.runner.run_once(self.expert, max_steps=1)

    def unavailable(self, result):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, 'unavailable')

    def request(self, step):
        return {'key': dumps(['C04.ask', self.o.work, step['step_id']]),
                'work_ref': self.o.work, 'step_id': step['step_id'],
                **{k: step['action'][k] for k in ('question', 'missing_fact', 'source_refs')}}

    def assert_waiting(self, result):
        data = value(result)
        self.assertEqual({k: data[k] for k in ('status', 'question_id', 'state', 'work_ref', 'lease_id', 'step_id')},
                         {'status': 'waiting', 'question_id': 'q', 'state': 'waiting_input',
                          'work_ref': self.o.work, 'lease_id': 'lease', 'step_id': self.o.steps[-1]['step_id']})
        self.assertEqual(self.o.finishes, [])
        self.assertEqual(self.o.releases, [])
        return data

    def test_atomic_waiting_uses_persisted_step_exact_key_and_no_generic_finish(self):
        self.o.persisted_action = {'kind': 'ask', 'question': 'Persisted wording?',
                                   'missing_fact': 'persisted fact', 'source_refs': [self.o.origin, self.o.origin]}
        data = self.assert_waiting(self.run_ask())
        self.assertEqual(self.o.asks, [self.request(self.o.steps[-1])])
        self.assertEqual((len(self.inputs), len(self.o.reserves), len(data['call_ids'])), (1, 1, 1))
        self.assertEqual(data['excluded_refs'], [])
        self.assertEqual(data['excluded_step_ids'], [])

    def test_three_same_input_attempts_then_one_lookup_recovers_lost_reply(self):
        self.o.ask_results = [Result.failure('unavailable', 'lost response') for _ in range(3)]
        self.o.lookup_result = Result.success(self.o.receipt())
        self.assert_waiting(self.run_ask())
        expected = self.request(self.o.steps[-1])
        self.assertEqual(self.o.asks, [expected] * 3)
        self.assertEqual(self.o.lookups, [{'key': expected['key']}])
        self.assertEqual((len(self.inputs), len(self.o.reserves)), (1, 1))

    def test_retry_stops_on_second_success_without_lookup(self):
        self.o.ask_results = [Result.failure('unavailable', 'transient'), Result.success(self.o.receipt())]
        self.assert_waiting(self.run_ask())
        self.assertEqual(len(self.o.asks), 2)
        self.assertEqual(self.o.lookups, [])

    def test_unknown_commit_retains_started_step_and_never_repairs_by_inference(self):
        self.o.ask_results = [Result.failure('unavailable', 'unknown') for _ in range(3)]
        self.o.lookup_result = Result.failure('unavailable', 'unknown')
        self.o.release_failure = 'conflict'
        self.unavailable(self.run_ask())
        self.assertEqual((len(self.o.asks), len(self.o.lookups)), (3, 1))
        self.assertEqual(self.o.steps[-1]['status'], 'started')
        self.assertEqual(self.o.finishes, [])
        self.assertEqual([r['outcome'] for r in self.o.releases], ['yield'])
        self.assertEqual(len(self.inputs), 1)

    def test_ask_authority_refusals_yield_never_fail_and_never_lookup(self):
        for code in ('conflict', 'stale', 'denied', 'not_found', 'invalid_input'):
            with self.subTest(code=code):
                self.setUp()
                self.o.ask_results = [Result.failure(code, 'newer owner authority')]
                self.run_ask()
                self.assertEqual(len(self.o.asks), 1)
                self.assertEqual([r['outcome'] for r in self.o.releases], ['yield'])
                self.assertEqual(self.o.finishes, [])
                self.assertEqual(self.o.lookups, [])
                self.assertEqual(len(self.inputs), 1)

    def test_malformed_waiting_receipts_fail_closed(self):
        bad = [None, {}, {'question_id': '', 'state': 'waiting_input', 'work_ref': self.o.work},
               {'question_id': 1, 'state': 'waiting_input', 'work_ref': self.o.work},
               {'question_id': 'q', 'state': 'queued', 'work_ref': self.o.work},
               {'question_id': 'q', 'state': 'waiting_input', 'work_ref': {**self.o.work, 'epoch': 1}},
               {**self.o.receipt(), 'extra': True}]
        for receipt in bad:
            with self.subTest(receipt=receipt):
                self.setUp()
                self.o.receipt_override = object() if receipt is None else Result.success(receipt)
                self.o.release_failure = 'conflict'
                self.unavailable(self.run_ask())
                self.assertEqual(self.o.finishes, [])
                self.assertTrue(all(r['outcome'] == 'yield' for r in self.o.releases))
                self.assertEqual(len(self.inputs), 1)

    def test_unrecognized_or_throwing_ask_owner_fails_closed_without_failed_release(self):
        for disposition in ('limit', 'exception'):
            with self.subTest(disposition=disposition):
                self.setUp()
                self.o.release_failure = 'conflict'
                if disposition == 'limit':
                    self.o.ask_results = [Result.failure('limit', 'not a C04 authority disposition')]
                else:
                    def broken(request):
                        raise RuntimeError('synthetic callback failure')
                    self.o.ask = broken
                self.unavailable(self.run_ask())
                self.assertEqual(self.o.finishes, [])
                self.assertTrue(all(r['outcome'] == 'yield' for r in self.o.releases))
                self.assertEqual(self.o.lookups, [])
                self.assertEqual(len(self.inputs), 1)

    def tail(self):
        step = {'step_id': 'tail', 'work_ref': copy.deepcopy(self.o.work), 'index': 0,
                'action': {'kind': 'ask', 'question': 'Saved?', 'missing_fact': 'saved',
                           'source_refs': [self.o.origin]}, 'status': 'started', 'result_refs': []}
        self.o.steps = [step]
        call_id = dumps(['C15.call', 'lease', 0])
        self.o.calls[call_id] = {'call_id': call_id, 'lease_id': 'lease', 'index': 0,
                                'status': 'returned', 'may_enter': False,
                                'work_ref': copy.deepcopy(self.o.work), 'step_id': 'tail'}
        return call_id

    def test_retained_ask_public_call_recheck_without_fresh_inference(self):
        call_id = self.tail()
        data = self.assert_waiting(self.run_ask())
        self.assertIn(('get_call', {'call_id': call_id}), self.o.requests)
        self.assertEqual(self.o.asks, [self.request(self.o.steps[-1])])
        self.assertEqual(self.inputs, [])
        self.assertEqual(self.o.reserves, [])
        self.assertEqual(data['call_ids'], [call_id])

    def test_retained_call_missing_wrong_binding_or_unended_never_asks(self):
        for mutation in ('missing', 'admitted', 'wrong_step', 'wrong_epoch', 'malformed', 'wrong_lease', 'bool_index'):
            with self.subTest(mutation=mutation):
                self.setUp()
                key = self.tail()
                if mutation == 'missing':
                    del self.o.calls[key]
                elif mutation == 'admitted':
                    self.o.calls[key]['status'] = 'admitted'
                elif mutation == 'wrong_step':
                    self.o.calls[key]['step_id'] = 'other'
                elif mutation == 'wrong_epoch':
                    self.o.calls[key]['work_ref']['epoch'] = 1
                elif mutation == 'wrong_lease':
                    self.o.calls[key]['lease_id'] = 'foreign'
                elif mutation == 'bool_index':
                    self.o.calls[key]['index'] = False
                else:
                    self.o.calls[key]['work_ref']['epoch'] = False
                self.o.release_failure = 'conflict'
                self.unavailable(self.run_ask())
                self.assertEqual((self.o.asks, self.inputs, self.o.reserves), ([], [], []))

    def historical(self):
        self.o.work['epoch'] = 3
        refs = [{'kind': 'record', 'id': name} for name in ('answer1', 'answer2', 'question-source', 'unrelated')]
        self.o.optional = refs
        self.o.steps = [{'step_id': 'ask-' + str(i), 'work_ref': {**self.o.work, 'epoch': i}, 'index': i,
                         'action': {'kind': 'ask', 'question': 'Question ' + str(i), 'missing_fact': 'fact',
                                    'source_refs': [self.o.origin]}, 'status': 'finished', 'result_refs': []}
                        for i in range(2)]
        self.o.pending = [{'question_id': 'q' + str(i), 'step_id': s['step_id'], 'answer_record_ref': refs[i]}
                          for i, s in enumerate(self.o.steps)]
        self.o.provenance = {'ask-0': [self.o.origin, refs[2]], 'ask-1': [self.o.origin]}

    def report(self, context, **diagnostics):
        self.inputs.append(copy.deepcopy(context))
        return {'kind': 'report', 'summary': 'bounded'}

    def test_multiple_old_epoch_links_exact_c12_and_complete_local_diagnostics(self):
        self.historical()
        data = value(self.runner.run_once(self.report))
        self.assertEqual(self.inputs[0]['pending_inputs'], self.o.pending)
        self.assertEqual(data['pending_inputs'], self.o.pending)
        self.assertEqual([s['step_id'] for s in self.inputs[0]['steps']], ['ask-0', 'ask-1'])

    def test_selective_answer_or_question_source_exclusion_keeps_all_diagnostics(self):
        for stopped, eligible, excluded_step in [('answer1', [1], []), ('question-source', [1], ['ask-0']),
                                                ('unrelated', [0, 1], [])]:
            with self.subTest(stopped=stopped):
                self.setUp()
                self.historical()
                self.o.read_errors[stopped] = 'denied'
                data = value(self.runner.run_once(self.report))
                self.assertEqual(self.inputs[0]['pending_inputs'], [self.o.pending[i] for i in eligible])
                self.assertEqual(data['pending_inputs'], self.o.pending)
                self.assertEqual(data['excluded_step_ids'], excluded_step)
                self.assertIn({'kind': 'record', 'id': stopped}, data['excluded_refs'])
                if stopped == 'question-source':
                    self.assertIn(self.o.pending[0]['answer_record_ref'], [c['ref'] for c in self.inputs[0]['context']])

    def test_empty_or_all_ineligible_links_omit_optional_c12_field(self):
        for historical in (False, True):
            with self.subTest(historical=historical):
                self.setUp()
                if historical:
                    self.historical()
                    self.o.read_errors.update(answer1='not_found', answer2='denied')
                data = value(self.runner.run_once(self.report))
                self.assertNotIn('pending_inputs', self.inputs[0])
                self.assertEqual(data['pending_inputs'], self.o.pending)

    def test_corrupt_pending_linkage_never_enters_expert(self):
        for mutation in ('unknown_step', 'nonask', 'started', 'duplicate_question', 'wrong_ref_kind', 'extra', 'wrong_revision'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.historical()
                if mutation == 'unknown_step': self.o.pending[0]['step_id'] = 'missing'
                elif mutation == 'nonask': self.o.steps[0]['action'] = {'kind': 'report', 'summary': 'not question'}
                elif mutation == 'started': self.o.steps[0]['status'] = 'started'
                elif mutation == 'duplicate_question': self.o.pending[1]['question_id'] = self.o.pending[0]['question_id']
                elif mutation == 'wrong_ref_kind': self.o.pending[0]['answer_record_ref']['kind'] = 'artifact'
                elif mutation == 'extra': self.o.pending[0]['body'] = 'invented'
                else: self.o.steps[0]['work_ref']['revision'] = 2
                self.runner.run_once(self.report)
                self.assertEqual(self.inputs, [])
                self.assertEqual(self.o.reserves, [])

    def test_optional_answer_unavailable_does_not_become_exclusion_or_inference(self):
        self.historical()
        self.o.read_errors['answer1'] = 'unavailable'
        self.runner.run_once(self.report)
        self.assertEqual(self.inputs, [])
        self.assertEqual(self.o.reserves, [])

    def test_c076_ver_authority_is_nonterminal_and_latest_execution_settles_pause(self):
        for code in ('conflict', 'stale', 'denied'):
            with self.subTest(code=code):
                self.setUp()
                self.o.receipt = SyntheticOwners.receipt.__get__(self.o)
                self.o.verify_failure = code
                def pause():
                    self.o.state = 'paused'
                    self.o.context_error = 'denied'
                self.o.after_verify = pause
                runner = MockRunner(self.o, self.o, artifacts=self.o, verifications=self.o)
                def compose(context, **diagnostics):
                    self.inputs.append(copy.deepcopy(context))
                    return {'kind': 'compose', 'content': 'draft', 'media_type': 'text/plain', 'source_refs': [self.o.origin]}
                runner.run_once(compose, max_steps=2)
                self.assertEqual(len(self.inputs), 1)
                self.assertTrue(self.o.releases)
                self.assertTrue(all(r['outcome'] != 'failed' for r in self.o.releases), self.o.releases)
                self.assertEqual(self.o.completes, [])


if __name__ == '__main__':
    unittest.main()
