"""Independent source-review regression for linked historical ask Step shape."""
import unittest
import test_mock_ask_v5 as fixture


class MockAskIntegrityTests(unittest.TestCase):
    def test_invalid_linked_question_shape_never_reaches_model_or_reserves_budget(self):
        for field, value in (('error', 1), ('error', 'ask failed'), ('unrecognized', 'hidden')):
            with self.subTest(field=field, value=value):
                f = fixture.MockAskTests()
                f.setUp()
                try:
                    f.historical()
                    f.o.steps[0][field] = value
                    f.o.release_failure = 'conflict'
                    result = f.runner.run_once(f.report)
                    self.assertEqual((f.inputs, f.o.reserves), ([], []))
                    f.unavailable(result)
                    self.assertFalse(any(r['outcome'] == 'failed' for r in f.o.releases))
                finally:
                    f.doCleanups()


if __name__ == '__main__':
    unittest.main()
