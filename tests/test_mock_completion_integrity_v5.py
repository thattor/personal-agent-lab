"""Independent strict boundary regressions beyond the frozen acceptance fixture."""
import copy
import unittest

from pal.contracts_v5 import Result, dumps
import test_mock_completion_v5 as fixture


class MockCompletionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.MockCompletionTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def unavailable(self, result):
        self.f.error(result)
        self.assertEqual(len(self.f.model_inputs), 1)
        self.assertEqual(self.f.owners.releases, [])
        self.assertEqual(self.f.owners.state, 'running')

    def test_malformed_checks_do_not_continue_inference_or_complete(self):
        changes = [lambda r: r['checks'][0].update(status='broken'),
                   lambda r: r['checks'][0].update(condition_id='other'),
                   lambda r: r['checks'].append(copy.deepcopy(r['checks'][0])),
                   lambda r: r['checks'][0].update(reason='x' * 1025),
                   lambda r: r['checks'][0].update(evidence_refs=[{'kind': 'verification', 'id': 'v'}]),
                   lambda r: r['checks'][0].update(evidence_refs=[{'kind': 'artifact', 'id': 'other'}])]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                if index:
                    self.setUp()
                receipt = self.f.owners.receipt()
                change(receipt)
                self.f.owners.verify = lambda request: Result.success(receipt)
                self.unavailable(self.f.runner().run_once(self.f.expert, max_steps=2))
                self.assertEqual(self.f.owners.completes, [])

    def test_unexpected_owner_errors_are_not_work_failure_authority(self):
        for method, codes in [('verify', ['ambiguous', 'invalid_input', 'not_found', 'limit']),
                              ('control', ['invalid_input', 'not_found', 'limit'])]:
            for code in codes:
                with self.subTest(method=method, code=code):
                    self.setUp()
                    setattr(self.f.owners, method, lambda request, code=code: Result.failure(code, 'fixture unknown'))
                    self.unavailable(self.f.runner().run_once(self.f.expert, max_steps=2))

    def test_current_artifact_set_is_typed_and_required(self):
        for index, refs in enumerate((None, 'not a list', [{'kind': 'record', 'id': 'r'}],
                                    [{'kind': 'artifact', 'id': 'a'}] * 2)):
            with self.subTest(refs=refs):
                if index:
                    self.setUp()
                self.f.owners.get_work = lambda request: Result.success({
                    'work_ref': self.f.owners.work, 'state': 'running', 'current_artifact_refs': refs})
                self.unavailable(self.f.runner().run_once(self.f.expert, max_steps=2))
                self.assertEqual(self.f.owners.verifies, [])

    def test_completion_workref_never_accepts_boolean_integer_equivalence(self):
        self.f.owners.control = lambda request: Result.success({
            'work_ref': {**self.f.owners.work, 'revision': True},
            'state': 'completed', 'control_status': 'none'})
        self.unavailable(self.f.runner().run_once(self.f.expert, max_steps=2))

    def test_nonresult_or_raising_completion_callback_retains_occupancy(self):
        def raises(request):
            raise RuntimeError('synthetic response unavailable')
        for callback in (lambda request: {'ok': True}, raises):
            with self.subTest(callback=callback):
                self.setUp()
                self.f.owners.control = callback
                self.unavailable(self.f.runner().run_once(self.f.expert, max_steps=2))

    def test_retained_same_lease_completion_returns_durable_diagnostics(self):
        runner = self.f.runner()
        self.f.owners.complete_failure = 'unavailable'
        self.f.error(runner.run_once(self.f.expert))
        self.f.owners.complete_failure = None
        out = fixture.value(runner.run_once(self.f.expert))
        self.assertEqual(out['status'], 'completed')
        self.assertEqual(out['steps'], self.f.owners.steps)
        self.assertEqual(out['call_ids'], [dumps(['C15.call', 'lease', 0])])
        self.assertEqual(len(self.f.model_inputs), 1)


if __name__ == '__main__':
    unittest.main()
